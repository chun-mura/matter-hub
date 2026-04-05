"""Auto-tagging for articles using Ollama or Claude API."""

import json
import re

import httpx


def build_prompt(article: dict, highlights: list[dict], existing_tags: list[str]) -> str:
    parts = [
        "以下の記事に3〜5個の日本語タグをつけてください。",
        "タグは短く（1〜3語）、カテゴリとして再利用しやすいものにしてください。",
    ]
    if existing_tags:
        parts.append(f"既存タグ一覧: {', '.join(existing_tags)}")
        parts.append("できるだけ既存タグを再利用してください。")
    parts.append("JSON配列で返してください。例: [\"AI\", \"Web開発\"]")
    parts.append("")
    parts.append(f"タイトル: {article['title']}")
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
    base_url: str = "http://localhost:11434",
) -> list[str]:
    prompt = build_prompt(article, highlights, existing_tags)
    resp = httpx.post(
        f"{base_url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return parse_tags_response(resp.json()["response"])


def tag_article_anthropic(
    client,
    article: dict,
    highlights: list[dict],
    existing_tags: list[str],
) -> list[str]:
    prompt = build_prompt(article, highlights, existing_tags)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_tags_response(response.content[0].text)
