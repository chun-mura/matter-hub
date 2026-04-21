"""Ollama integration for auto-tagging and embedding generation."""

import json
import os
import re

import httpx


def get_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def build_prompt(article: dict, highlights: list[dict], existing_tags: list[str]) -> str:
    from matter_hub.title_locale import display_title

    parts = [
        "以下の記事に3〜5個の日本語タグをつけてください。",
        "タグは短く（1〜3語）、カテゴリとして再利用しやすいものにしてください。",
    ]
    if existing_tags:
        parts.append(f"既存タグ一覧: {', '.join(existing_tags)}")
        parts.append("できるだけ既存タグを再利用してください。")
    parts.append("JSON配列で返してください。例: [\"AI\", \"Web開発\"]")
    parts.append("")
    parts.append(f"タイトル: {display_title(article)}")
    parts.append(f"URL: {article['url']}")
    if article.get("author"):
        parts.append(f"著者: {article['author']}")
    if article.get("publisher"):
        parts.append(f"出版社: {article['publisher']}")
    if highlights:
        hl_texts = [h["text"] for h in highlights]
        parts.append(f"ハイライト: {' / '.join(hl_texts)}")
    return "\n".join(parts)


def parse_tags_response(text: str) -> list[str]:
    cleaned = re.sub(r"```json\s*", "", text)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    # Try to find a JSON array in the text
    match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list) and all(isinstance(t, str) for t in result):
                return result
        except (json.JSONDecodeError, TypeError):
            pass
    try:
        result = json.loads(cleaned)
        if isinstance(result, list) and all(isinstance(t, str) for t in result):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def tag_article_ollama(
    article: dict,
    highlights: list[dict],
    existing_tags: list[str],
    model: str = "gemma3:4b",
    base_url: str | None = None,
) -> list[str]:
    prompt = build_prompt(article, highlights, existing_tags)
    resp = httpx.post(
        f"{base_url or get_base_url()}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return parse_tags_response(resp.json()["response"])


def build_embedding_text(article: dict, tags: list[str], highlights: list[dict]) -> str:
    from matter_hub.title_locale import display_title

    parts = [f"タイトル: {display_title(article)}"]
    if article.get("author"):
        parts.append(f"著者: {article['author']}")
    if tags:
        parts.append(f"タグ: {', '.join(tags)}")
    if highlights:
        hl_texts = [h["text"] for h in highlights]
        parts.append(f"ハイライト: {' / '.join(hl_texts)}")
    return "\n".join(parts)


def translate_title_ollama(
    title: str,
    model: str = "gemma3:4b",
    base_url: str | None = None,
) -> str:
    """英語等のタイトルを自然な日本語の記事タイトルに翻訳。1行のみ返す。"""
    prompt = (
        "次の文字列はウェブ記事のタイトルです。自然な日本語のタイトルに翻訳してください。\n"
        "説明・引用符・マークダウンは付けず、翻訳したタイトルのみを1行で出力してください。\n\n"
        f"{title.strip()}"
    )
    resp = httpx.post(
        f"{base_url or get_base_url()}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=90,
    )
    resp.raise_for_status()
    out = (resp.json().get("response") or "").strip()
    out = re.sub(r"^[`「『\"]+|[`」』\"]+$", "", out)
    out = out.splitlines()[0].strip() if out else ""
    return out or title.strip()


def generate_embedding(
    text: str,
    model: str = "nomic-embed-text",
    base_url: str | None = None,
) -> list[float]:
    resp = httpx.post(
        f"{base_url or get_base_url()}/api/embed",
        json={"model": model, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]
