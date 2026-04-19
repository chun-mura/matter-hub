"""Shared sync pipeline building blocks."""

from __future__ import annotations

import platform
import subprocess
import time
from typing import Callable, Protocol

import httpx

from matter_hub.api import MatterClient, parse_feed_entry
from matter_hub.config import get_db_path, load_config, save_config
from matter_hub.db import Database


class Logger(Protocol):
    def __call__(self, msg: str, level: str = "info") -> None: ...


def _noop(msg: str, level: str = "info") -> None:
    pass


EnsureFn = Callable[[], bool]


def _is_local_url(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url


def ensure_ollama_noninteractive(
    log: Logger = _noop,
    auto_start: bool = True,
    wait_seconds: int = 60,
) -> bool:
    """Check Ollama availability; optionally launch without prompting."""
    from matter_hub.ollama import get_base_url

    base_url = get_base_url()
    try:
        httpx.get(f"{base_url}/api/tags", timeout=3)
        return True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    if not auto_start or not _is_local_url(base_url):
        log(f"Ollamaに接続できません ({base_url})", level="warn")
        return False

    log("Ollamaが起動していません。起動を試みます...", level="warn")
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", "-a", "Ollama"])
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except FileNotFoundError:
        log("Ollamaを起動できませんでした（コマンド未検出）", level="error")
        return False

    for _ in range(wait_seconds):
        time.sleep(1)
        try:
            httpx.get(f"{base_url}/api/tags", timeout=3)
            log("Ollama起動完了", level="success")
            return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pass

    log("Ollamaの起動がタイムアウトしました", level="error")
    return False


def load_client() -> MatterClient:
    config = load_config()
    access_token = config.get("access_token")
    if not access_token:
        raise RuntimeError("未認証です。`matter-hub auth` を実行してください。")
    return MatterClient(
        access_token=access_token,
        refresh_token=config.get("refresh_token"),
    )


def fetch_entries_with_refresh(client: MatterClient) -> list[dict]:
    try:
        return client.fetch_all_articles()
    except Exception:
        config = load_config()
        if not config.get("refresh_token"):
            raise
        client.refresh_token = config["refresh_token"]
        new_tokens = client.refresh_access_token()
        save_config({
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens["refresh_token"],
        })
        return client.fetch_all_articles()


def ingest_entries(db: Database, entries: list[dict], log: Logger = _noop) -> tuple[int, int]:
    synced = 0
    deleted = 0
    for entry in entries:
        parsed = parse_feed_entry(entry)
        article = parsed["article"]

        if article.get("library_state") == 3:
            if db.delete_article(article["id"]):
                deleted += 1
            continue

        if db.is_deleted(article["id"]):
            continue

        db.upsert_article(article)

        db.clear_matter_tags(article["id"])
        for t in parsed["tags"]:
            db.add_tag(article["id"], t["name"], "matter")

        db.clear_highlights(article["id"])
        for h in parsed["highlights"]:
            db.add_highlight(
                article["id"], h["text"], h.get("note"), h.get("created_date")
            )

        synced += 1

    log(f"{synced} 件の記事を同期しました", level="success")
    if deleted:
        log(f"{deleted} 件の削除済み記事を除去しました", level="warn")
    return synced, deleted


def auto_tag_articles(
    db: Database,
    ensure_ollama: EnsureFn,
    model: str = "gemma3:4b",
    log: Logger = _noop,
) -> int:
    from matter_hub.ollama import tag_article_ollama

    if not ensure_ollama():
        return 0

    articles = db.articles_without_ai_tags()
    existing_tags = db.get_all_tag_names()

    if not articles:
        log("タグ付け対象の記事はありません", level="success")
        return 0

    log(f"{len(articles)} 件の記事にタグ付け中（Ollama: {model}）...", level="warn")

    tagged = 0
    for article in articles:
        highlights = db.get_highlights(article["id"])
        try:
            tags = tag_article_ollama(article, highlights, existing_tags, model=model)
        except Exception as e:
            log(f"  {article['title'][:40]}... → エラー: {e}", level="error")
            continue
        for tag_name in tags:
            db.add_tag(article["id"], tag_name, "ai")
            if tag_name not in existing_tags:
                existing_tags.append(tag_name)
        log(f"  {article['title'][:40]}... → {', '.join(tags) or '(タグなし)'}")
        tagged += 1

    log("タグ付け完了", level="success")
    return tagged


def embed_articles(
    db: Database,
    ensure_ollama: EnsureFn,
    log: Logger = _noop,
) -> int:
    import numpy as np
    from matter_hub.ollama import build_embedding_text, generate_embedding

    if not ensure_ollama():
        return 0

    articles = db.articles_without_embedding()
    if not articles:
        log("Embedding生成対象の記事はありません", level="success")
        return 0

    log(f"{len(articles)} 件の記事のEmbeddingを生成中...", level="warn")

    embedded = 0
    for article in articles:
        tags = [t["name"] for t in db.get_tags(article["id"])]
        highlights = db.get_highlights(article["id"])
        text = build_embedding_text(article, tags, highlights)
        try:
            embedding = generate_embedding(text)
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
            db.save_embedding(article["id"], embedding_bytes)
            log(f"  {article['title'][:50]}... → OK")
            embedded += 1
        except Exception as e:
            log(f"  {article['title'][:50]}... → エラー: {e}", level="error")

    log("Embedding生成完了", level="success")
    return embedded


def run_sync(
    tag: bool = False,
    embed: bool = False,
    model: str = "gemma3:4b",
    log: Logger = _noop,
    auto_start_ollama: bool = True,
) -> dict:
    """Webapp-facing entry point: load config, fetch, ingest, optionally tag/embed."""
    log("Matter APIから記事を取得中...")
    client = load_client()
    entries = fetch_entries_with_refresh(client)

    db = Database(get_db_path())
    tagged = None
    embedded = None
    try:
        synced, deleted = ingest_entries(db, entries, log=log)
        ensure = lambda: ensure_ollama_noninteractive(log=log, auto_start=auto_start_ollama)
        if tag:
            tagged = auto_tag_articles(db, ensure, model=model, log=log)
        if embed:
            embedded = embed_articles(db, ensure, log=log)
    finally:
        db.close()

    return {
        "synced": synced,
        "deleted": deleted,
        "tagged": tagged,
        "embedded": embedded,
    }
