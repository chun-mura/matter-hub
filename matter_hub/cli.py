"""CLI entry point for Matter Hub."""

import sys
import time

import click
import qrcode
from rich.console import Console
from rich.table import Table

from matter_hub.api import MatterClient, parse_feed_entry
from matter_hub.config import load_config, save_config, get_db_path
from matter_hub.db import Database

console = Console()


def get_client_from_config() -> MatterClient:
    config = load_config()
    access_token = config.get("access_token")
    refresh_token = config.get("refresh_token")
    if not access_token:
        console.print("[red]未認証です。先に `matter-hub auth` を実行してください。[/red]")
        sys.exit(1)
    return MatterClient(access_token=access_token, refresh_token=refresh_token)


def get_db() -> Database:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Database(db_path)


@click.group()
def cli():
    """Matter Hub - Matter記事の検索・タグ管理CLI"""
    pass


@cli.command()
def auth():
    """QRコード認証でMatterにログイン"""
    client = MatterClient()
    session_token = client.trigger_qr_login()

    console.print("\n[bold]MatterアプリでこのQRコードをスキャンしてください:[/bold]")
    console.print("[dim]Profile > Settings > Connected Accounts > Obsidian > Scan QR Code[/dim]\n")

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(session_token)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    console.print("\n[yellow]スキャン待機中...[/yellow]")

    for _ in range(600):
        result = client.exchange_token(session_token)
        if result:
            save_config({
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
            })
            console.print("[green]認証成功！トークンを保存しました。[/green]")
            return
        time.sleep(1)

    console.print("[red]タイムアウト: 10分以内にスキャンされませんでした。[/red]")
    sys.exit(1)


@cli.command()
@click.option("--tag", is_flag=True, help="同期後にOllamaで自動タグ付けを実行")
@click.option("--model", default="gemma3:4b", help="Ollamaモデル名（デフォルト: gemma3:4b）")
def sync(tag, model):
    """Matter APIから記事を同期"""
    client = get_client_from_config()

    try:
        entries = client.fetch_all_articles()
    except Exception as e:
        config = load_config()
        if config.get("refresh_token"):
            try:
                client.refresh_token = config["refresh_token"]
                new_tokens = client.refresh_access_token()
                save_config({
                    "access_token": new_tokens["access_token"],
                    "refresh_token": new_tokens["refresh_token"],
                })
                entries = client.fetch_all_articles()
            except Exception:
                console.print("[red]トークンの更新に失敗しました。`matter-hub auth` で再認証してください。[/red]")
                sys.exit(1)
        else:
            raise

    db = get_db()
    count = 0

    for entry in entries:
        parsed = parse_feed_entry(entry)
        article = parsed["article"]

        if article.get("library_state") == 3:
            continue

        db.upsert_article(article)

        db.clear_matter_tags(article["id"])
        for t in parsed["tags"]:
            db.add_tag(article["id"], t["name"], "matter")

        db.clear_highlights(article["id"])
        for h in parsed["highlights"]:
            db.add_highlight(article["id"], h["text"], h.get("note"), h.get("created_date"))

        count += 1

    console.print(f"[green]{count} 件の記事を同期しました[/green]")

    if tag:
        _run_auto_tag(db, ollama_model=model)

    db.close()


def _run_auto_tag(db: Database, ollama_model: str = "gemma3:4b"):
    from matter_hub.tagger import tag_article_ollama

    articles = db.articles_without_ai_tags()
    existing_tags = db.get_all_tag_names()

    if not articles:
        console.print("[green]タグ付け対象の記事はありません[/green]")
        return

    console.print(f"[yellow]{len(articles)} 件の記事にタグ付け中（Ollama: {ollama_model}）...[/yellow]")

    for article in articles:
        highlights = db.get_highlights(article["id"])
        try:
            tags = tag_article_ollama(article, highlights, existing_tags, model=ollama_model)
        except Exception as e:
            console.print(f"  [red]{article['title'][:40]}... → エラー: {e}[/red]")
            continue
        for tag_name in tags:
            db.add_tag(article["id"], tag_name, "ai")
            if tag_name not in existing_tags:
                existing_tags.append(tag_name)
        console.print(f"  {article['title'][:40]}... → {', '.join(tags) or '(タグなし)'}")

    console.print("[green]タグ付け完了[/green]")


@cli.command()
@click.argument("query", default="")
@click.option("--tag", "tag_filter", default=None, help="タグで絞り込み")
@click.option("--author", default=None, help="著者で絞り込み")
@click.option("--after", default=None, help="指定日以降の記事 (YYYY-MM-DD)")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def search(query, tag_filter, author, after, as_json):
    """記事を検索"""
    db = get_db()

    if tag_filter:
        articles = db.search_by_tag(tag_filter)
    elif query:
        articles = db.search(query)
    else:
        articles = db.list_articles()

    if author:
        articles = [a for a in articles if a.get("author") and author.lower() in a["author"].lower()]
    if after:
        articles = [a for a in articles if a.get("published_date") and a["published_date"] >= after]

    if as_json:
        import json
        click.echo(json.dumps(articles, ensure_ascii=False, indent=2))
    else:
        _print_articles_table(articles)

    db.close()


@cli.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="全件表示")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def list_cmd(show_all, as_json):
    """記事一覧を表示"""
    db = get_db()
    limit = None if show_all else 20
    articles = db.list_articles(limit=limit)

    if as_json:
        import json
        click.echo(json.dumps(articles, ensure_ascii=False, indent=2))
    else:
        _print_articles_table(articles)

    db.close()


@cli.command()
def tags():
    """タグ一覧を表示（記事数付き）"""
    db = get_db()
    tag_list = db.list_tags()

    table = Table(title="タグ一覧")
    table.add_column("タグ", style="cyan")
    table.add_column("記事数", justify="right", style="green")

    for name, count in tag_list:
        table.add_row(name, str(count))

    console.print(table)
    db.close()


@cli.group()
def tag():
    """タグの追加・削除"""
    pass


@tag.command(name="add")
@click.argument("article_id")
@click.argument("tag_name")
def tag_add(article_id, tag_name):
    """記事にタグを追加"""
    db = get_db()
    db.add_tag(article_id, tag_name, "manual")
    console.print(f"[green]タグ '{tag_name}' を追加しました[/green]")
    db.close()


@tag.command(name="remove")
@click.argument("article_id")
@click.argument("tag_name")
def tag_remove(article_id, tag_name):
    """記事からタグを削除"""
    db = get_db()
    db.remove_tag(article_id, tag_name)
    console.print(f"[yellow]タグ '{tag_name}' を削除しました[/yellow]")
    db.close()


@cli.command()
def stats():
    """興味の傾向を分析"""
    db = get_db()
    s = db.get_stats()

    console.print(f"\n[bold]記事数:[/bold] {s['total_articles']}")
    console.print(f"[bold]タグ数:[/bold] {s['total_tags']}")

    if s["top_authors"]:
        console.print("\n[bold]著者別（上位10件）:[/bold]")
        table = Table()
        table.add_column("著者", style="cyan")
        table.add_column("記事数", justify="right", style="green")
        for author, count in s["top_authors"]:
            table.add_row(author, str(count))
        console.print(table)

    if s["monthly"]:
        console.print("\n[bold]月別保存数:[/bold]")
        table = Table()
        table.add_column("月", style="cyan")
        table.add_column("記事数", justify="right", style="green")
        for month, count in s["monthly"]:
            table.add_row(month, str(count))
        console.print(table)

    db.close()


def _print_articles_table(articles: list[dict]):
    if not articles:
        console.print("[yellow]記事が見つかりませんでした[/yellow]")
        return

    table = Table()
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("タイトル", style="cyan", max_width=50)
    table.add_column("著者", style="green", max_width=20)
    table.add_column("日付", style="yellow", max_width=12)

    for a in articles:
        table.add_row(
            a["id"][:8],
            a["title"][:50],
            a.get("author") or "-",
            a.get("published_date") or "-",
        )

    console.print(table)
