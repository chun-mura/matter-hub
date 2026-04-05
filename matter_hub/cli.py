"""CLI entry point for Matter Hub."""

import os
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
@click.option("--tag", is_flag=True, help="同期後にAI自動タグ付けを実行")
def sync(tag):
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
        _run_auto_tag(db)

    db.close()


def _run_auto_tag(db: Database):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。[/red]")
        return

    import anthropic
    from matter_hub.tagger import tag_article

    client = anthropic.Anthropic(api_key=api_key)
    articles = db.articles_without_ai_tags()
    existing_tags = db.get_all_tag_names()

    console.print(f"[yellow]{len(articles)} 件の記事にタグ付け中...[/yellow]")

    for article in articles:
        highlights = db.get_highlights(article["id"])
        tags = tag_article(client, article, highlights, existing_tags)
        for tag_name in tags:
            db.add_tag(article["id"], tag_name, "ai")
            if tag_name not in existing_tags:
                existing_tags.append(tag_name)
        console.print(f"  {article['title'][:40]}... → {', '.join(tags)}")

    console.print(f"[green]タグ付け完了[/green]")
