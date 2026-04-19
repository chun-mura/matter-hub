"""CLI entry point for Matter Hub."""

import sys
import time

import click
import qrcode
from rich.console import Console
from rich.table import Table

from matter_hub.api import MatterClient
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


def _console_log(msg: str, level: str = "info") -> None:
    style = {"success": "green", "warn": "yellow", "error": "red"}.get(level)
    if style:
        console.print(f"[{style}]{msg}[/{style}]")
    else:
        console.print(msg)


@cli.command()
@click.option("--tag", is_flag=True, help="同期後にOllamaで自動タグ付けを実行")
@click.option("--embed", is_flag=True, help="同期後にEmbeddingを生成")
@click.option("--model", default="gemma3:4b", help="Ollamaモデル名（デフォルト: gemma3:4b）")
def sync(tag, embed, model):
    """Matter APIから記事を同期"""
    from matter_hub.sync import fetch_entries_with_refresh, ingest_entries

    client = get_client_from_config()
    try:
        entries = fetch_entries_with_refresh(client)
    except Exception:
        console.print("[red]トークンの更新に失敗しました。`matter-hub auth` で再認証してください。[/red]")
        sys.exit(1)

    db = get_db()
    try:
        ingest_entries(db, entries, log=_console_log)
        if tag:
            _run_auto_tag(db, ollama_model=model)
        if embed:
            _run_embed(db)
    finally:
        db.close()


def _ensure_ollama():
    """Ollamaが起動しているか確認し、停止中なら起動を提案する。"""
    import httpx
    from matter_hub.ollama import get_base_url
    from matter_hub.sync import ensure_ollama_noninteractive

    base_url = get_base_url()
    try:
        httpx.get(f"{base_url}/api/tags", timeout=3)
        return True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    console.print(f"[yellow]Ollamaに接続できません ({base_url})[/yellow]")
    if not click.confirm("Ollamaを起動しますか？"):
        return False
    return ensure_ollama_noninteractive(log=_console_log, auto_start=True)


def _run_auto_tag(db: Database, ollama_model: str = "gemma3:4b"):
    from matter_hub.sync import auto_tag_articles

    auto_tag_articles(db, _ensure_ollama, model=ollama_model, log=_console_log)


def _run_embed(db: Database):
    from matter_hub.sync import embed_articles

    embed_articles(db, _ensure_ollama, log=_console_log)


def _semantic_search(db: Database, query: str, top_n: int = 10) -> list[dict]:
    """ハイブリッド検索: FTSスコアとセマンティック類似度を合算してランキング"""
    import numpy as np
    from matter_hub.ollama import generate_embedding

    # embedding未生成の記事があれば自動生成
    without = db.articles_without_embedding()
    if without:
        console.print(f"[yellow]{len(without)} 件の記事のEmbeddingを生成中...[/yellow]")
        _run_embed(db)

    if not _ensure_ollama():
        return []

    # --- セマンティックスコア ---
    query_emb = np.array(generate_embedding(query), dtype=np.float32)

    all_emb = db.get_all_embeddings()
    if not all_emb:
        console.print("[yellow]Embeddingが生成されていません。`matter-hub sync --embed` を実行してください。[/yellow]")
        return []

    semantic_scores = {}
    for row in all_emb:
        emb = np.frombuffer(row["embedding"], dtype=np.float32)
        similarity = float(np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb)))
        semantic_scores[row["id"]] = similarity

    # --- FTSスコア（0〜1に正規化）---
    fts_scores = {}
    if query.strip():
        # スペース区切りの単語をOR検索に変換
        terms = query.strip().split()
        fts_query = " OR ".join(f'"{t}"' for t in terms)
        fts_rows = db.conn.execute(
            """SELECT a.id, rank FROM articles a
               JOIN articles_fts f ON a.rowid = f.rowid
               WHERE articles_fts MATCH ?""",
            (fts_query,),
        ).fetchall()
        if fts_rows:
            # FTSヒットした記事にはスコア1.0を付与（ヒット有無が重要）
            for r in fts_rows:
                fts_scores[r["id"]] = 1.0

    # --- スコア合算 ---
    # FTSヒット時はボーナス(重み0.5)を加算
    all_ids = set(semantic_scores.keys())
    combined = []
    for aid in all_ids:
        sem = semantic_scores.get(aid, 0.0)
        fts = fts_scores.get(aid, 0.0)
        score = sem + 0.5 * fts
        combined.append((aid, score))

    combined.sort(key=lambda x: x[1], reverse=True)

    min_score = 0.3
    filtered = [(aid, s) for aid, s in combined if s >= min_score][:top_n]

    if not filtered:
        console.print("[yellow]類似度の高い記事が見つかりませんでした[/yellow]")
        return []

    articles = []
    for article_id, score in filtered:
        row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        if row:
            article = dict(row)
            article["_score"] = score
            articles.append(article)

    return articles


@cli.command()
@click.argument("query", default="")
@click.option("--tag", "tag_filter", default=None, help="タグで絞り込み")
@click.option("--author", default=None, help="著者で絞り込み")
@click.option("--after", default=None, help="指定日以降の記事 (YYYY-MM-DD)")
@click.option("--source", default=None, help="ソースで絞り込み（matter/hatena/hackernews/reddit/zenn/qiita/x/web）")
@click.option("--semantic", is_flag=True, help="セマンティック検索（意味的な類似度で検索）")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def search(query, tag_filter, author, after, source, semantic, as_json):
    """記事を検索"""
    db = get_db()

    if semantic:
        articles = _semantic_search(db, query)
    elif tag_filter:
        articles = db.search_by_tag(tag_filter, source=source)
    elif query:
        articles = db.search(query, source=source)
    else:
        articles = db.list_articles(source=source)

    if author:
        articles = [a for a in articles if a.get("author") and author.lower() in a["author"].lower()]
    if after:
        articles = [a for a in articles if a.get("published_date") and a["published_date"] >= after]

    if as_json:
        import json
        click.echo(json.dumps(articles, ensure_ascii=False, indent=2))
    else:
        _print_articles(articles)

    db.close()


@cli.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="全件表示")
@click.option("--source", default=None, help="ソースで絞り込み（matter/hatena/hackernews/reddit/zenn/qiita/x/web）")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def list_cmd(show_all, source, as_json):
    """記事一覧を表示"""
    db = get_db()
    limit = None if show_all else 20
    articles = db.list_articles(limit=limit, source=source)

    if as_json:
        import json
        click.echo(json.dumps(articles, ensure_ascii=False, indent=2))
    else:
        _print_articles(articles)

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


@cli.group(name="import")
def import_cmd():
    """外部URLから記事をインポート"""
    pass


@import_cmd.command(name="url")
@click.argument("urls", nargs=-1, required=True)
@click.option("--source", default=None, help="ソース種別（hatena/hackernews/reddit/zenn/qiita/x/web）")
@click.option("--note", default=None, help="メモを追加")
@click.option("--tag", "tag_names", multiple=True, help="タグを追加（複数指定可）")
def import_url(urls, source, note, tag_names):
    """URLから記事をインポート"""
    from matter_hub.importer import fetch_article

    db = get_db()
    for url in urls:
        try:
            article = fetch_article(url, source=source, note=note)
            db.upsert_article(article)
            for tag_name in tag_names:
                db.add_tag(article["id"], tag_name, "manual")
            console.print(f"  [green]✓[/green] {article['title'][:60]} [dim]({article['source']})[/dim]")
        except Exception as e:
            console.print(f"  [red]✗[/red] {url} → {e}")

    console.print(f"[green]{len(urls)} 件のURLを処理しました[/green]")
    db.close()


@import_cmd.command(name="json")
@click.argument("file", type=click.Path(exists=True))
def import_json(file):
    """JSONファイルから記事を一括インポート

    JSONフォーマット: [{"url": "...", "title": "...", "source": "...", "note": "..."}, ...]
    urlは必須、他はオプション。
    """
    import json as json_mod
    from matter_hub.importer import parse_json_import

    with open(file) as f:
        data = json_mod.load(f)

    if not isinstance(data, list):
        console.print("[red]JSONはarticleオブジェクトの配列である必要があります[/red]")
        sys.exit(1)

    articles = parse_json_import(data)
    db = get_db()
    count = 0
    for article in articles:
        db.upsert_article(article)
        count += 1
        console.print(f"  [green]✓[/green] {article['title'][:60]} [dim]({article['source']})[/dim]")

    console.print(f"[green]{count} 件の記事をインポートしました[/green]")
    db.close()


@cli.group()
def backfill():
    """壊れたメタデータを再取得する"""
    pass


@backfill.command(name="reddit")
@click.option("--dry-run", is_flag=True, help="更新せず対象のみ表示")
def backfill_reddit(dry_run):
    """Reddit記事で 'Please wait for verification' タイトルのものを再取得"""
    from matter_hub.importer import fetch_article

    db = get_db()
    rows = db.conn.execute(
        """SELECT * FROM articles
           WHERE source = 'reddit'
             AND (title LIKE 'Reddit - Please wait%'
                  OR title LIKE '%Please wait for verification%')""",
    ).fetchall()

    if not rows:
        console.print("[green]backfill対象の記事はありません[/green]")
        db.close()
        return

    console.print(f"[yellow]{len(rows)} 件のReddit記事を再取得します[/yellow]")
    updated = 0
    failed = 0
    for row in rows:
        existing = dict(row)
        url = existing["url"]
        article = fetch_article(url, source="reddit", note=existing.get("note"))
        if article["title"] == url or "Please wait" in article["title"]:
            console.print(f"  [red]✗[/red] {url} → 再取得失敗")
            failed += 1
            continue

        article["library_state"] = existing.get("library_state")

        if dry_run:
            console.print(f"  [cyan]→[/cyan] {article['title'][:60]}")
        else:
            db.upsert_article(article)
            console.print(f"  [green]✓[/green] {article['title'][:60]}")
            updated += 1

    if dry_run:
        console.print(f"[yellow]dry-run: {len(rows) - failed} 件が更新対象[/yellow]")
    else:
        console.print(f"[green]{updated} 件更新、{failed} 件失敗[/green]")
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


@cli.command(name="help")
@click.argument("command_name", default=None, required=False)
@click.pass_context
def help_cmd(ctx, command_name):
    """コマンドの使い方を表示"""
    if command_name:
        # 特定コマンドのヘルプ
        cmd = cli.get_command(ctx, command_name)
        if cmd is None:
            console.print(f"[red]不明なコマンド: {command_name}[/red]")
            console.print("利用可能なコマンドは [bold]matter-hub help[/bold] で確認できます。")
            sys.exit(1)
        console.print(f"\n[bold cyan]matter-hub {command_name}[/bold cyan] — {cmd.get_short_help_str()}\n")
        # サブコマンドがあるグループの場合
        if isinstance(cmd, click.Group):
            for sub_name, sub_cmd in cmd.commands.items():
                console.print(f"  [green]matter-hub {command_name} {sub_name}[/green]  {sub_cmd.get_short_help_str()}")
            console.print()
        # パラメータ表示
        params = [p for p in cmd.params if not isinstance(p, click.core.Context)]
        if params:
            param_table = Table(show_header=False, box=None, padding=(0, 2))
            param_table.add_column(style="yellow")
            param_table.add_column(style="dim")
            for p in params:
                if isinstance(p, click.Argument):
                    param_table.add_row(f"<{p.name}>", p.type.name)
                else:
                    names = " / ".join(p.opts)
                    param_table.add_row(names, p.help or "")
            console.print(param_table)
            console.print()
        return

    # 全体ヘルプ
    from matter_hub import __version__

    console.print(f"\n[bold]Matter Hub[/bold] v{__version__} — Matter記事の検索・タグ管理CLI\n")

    commands = [
        ("auth",        "QRコード認証でMatterにログイン"),
        ("sync",        "Matter APIから記事を同期（--tag/--embed）"),
        ("import url",  "URLから記事をインポート"),
        ("import json", "JSONファイルから一括インポート"),
        ("list",        "記事一覧を表示（--source対応）"),
        ("search",      "キーワード・タグ・著者・日付で記事を検索（--semantic/--source対応）"),
        ("tags",        "タグ一覧を表示（記事数付き）"),
        ("tag add",     "記事にタグを手動追加"),
        ("tag remove",  "記事からタグを削除"),
        ("stats",       "興味の傾向を分析"),
        ("help",        "このヘルプを表示"),
    ]

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", min_width=18)
    table.add_column(style="white")
    for name, desc in commands:
        table.add_row(f"matter-hub {name}", desc)
    console.print(table)

    console.print("\n[dim]各コマンドの詳細: matter-hub help <command>[/dim]\n")


def _print_articles(articles: list[dict]):
    if not articles:
        console.print("[yellow]記事が見つかりませんでした[/yellow]")
        return

    for a in articles:
        score = a.get("_score")
        score_str = f"[magenta]\\[{score:.2f}][/magenta] " if score is not None else ""
        source = a.get("source") or "matter"
        console.print(f"{score_str}[cyan]{a['title']}[/cyan] [dim]({source})[/dim]")
        author = a.get("author") or "-"
        date = a.get("published_date") or "-"
        console.print(f"       著者: {author}  日付: {date}")
        console.print(f"       [blue]{a.get('url') or '-'}[/blue]")
        console.print()
