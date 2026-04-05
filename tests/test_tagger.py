from unittest.mock import MagicMock, patch

from matter_hub.tagger import build_prompt, parse_tags_response, tag_article_anthropic, tag_article_ollama


def test_build_prompt():
    article = {
        "title": "Introduction to LLMs",
        "url": "https://example.com/llm",
        "author": "Alice",
        "publisher": "AI Blog",
    }
    highlights = [{"text": "transformers are key", "note": None}]
    existing_tags = ["AI", "機械学習"]
    prompt = build_prompt(article, highlights, existing_tags)
    assert "Introduction to LLMs" in prompt
    assert "Alice" in prompt
    assert "transformers are key" in prompt
    assert "AI" in prompt
    assert "機械学習" in prompt


def test_build_prompt_no_highlights():
    article = {
        "title": "Test",
        "url": "https://example.com",
        "author": None,
        "publisher": None,
    }
    prompt = build_prompt(article, [], [])
    assert "Test" in prompt


def test_parse_tags_response_json_array():
    assert parse_tags_response('["AI", "機械学習", "LLM"]') == ["AI", "機械学習", "LLM"]


def test_parse_tags_response_with_markdown():
    assert parse_tags_response('```json\n["AI", "LLM"]\n```') == ["AI", "LLM"]


def test_parse_tags_response_invalid():
    assert parse_tags_response("not json at all") == []


def test_parse_tags_response_with_surrounding_text():
    assert parse_tags_response('Here are the tags: ["AI", "LLM"] done') == ["AI", "LLM"]


def test_tag_article_anthropic():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='["AI", "自然言語処理", "LLM"]')]
    )
    article = {
        "title": "NLP Guide",
        "url": "https://example.com",
        "author": "Bob",
        "publisher": "Tech",
    }
    tags = tag_article_anthropic(mock_client, article, [], ["AI", "Python"])
    assert len(tags) == 3
    assert "AI" in tags
    mock_client.messages.create.assert_called_once()


def test_tag_article_ollama(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:11434/api/generate",
        json={"response": '["AI", "機械学習", "LLM"]'},
    )
    article = {
        "title": "ML Guide",
        "url": "https://example.com",
        "author": "Alice",
        "publisher": "Tech",
    }
    tags = tag_article_ollama(article, [], [])
    assert len(tags) == 3
    assert "AI" in tags
