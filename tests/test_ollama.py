from matter_hub.ollama import (
    build_prompt,
    parse_tags_response,
    tag_article_ollama,
    build_embedding_text,
    generate_embedding,
)


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


def test_build_embedding_text():
    article = {"title": "LLM入門", "author": "Alice", "url": "https://example.com"}
    tags = ["AI", "機械学習"]
    highlights = [{"text": "transformers are key"}]
    text = build_embedding_text(article, tags, highlights)
    assert "LLM入門" in text
    assert "Alice" in text
    assert "AI" in text
    assert "transformers are key" in text


def test_build_embedding_text_minimal():
    article = {"title": "Test", "author": None, "url": "https://example.com"}
    text = build_embedding_text(article, [], [])
    assert "Test" in text
    assert "著者" not in text


def test_build_prompt_uses_title_ja_when_present():
    article = {
        "title": "Rust ownership basics",
        "title_ja": "Rustの所有権入門",
        "url": "https://example.com",
        "author": None,
        "publisher": None,
    }
    prompt = build_prompt(article, [], [])
    assert "Rustの所有権入門" in prompt
    assert "Rust ownership basics" not in prompt


def test_build_embedding_text_uses_title_ja_when_present():
    article = {
        "title": "ML Guide",
        "title_ja": "機械学習ガイド",
        "author": None,
        "url": "https://example.com",
    }
    text = build_embedding_text(article, [], [])
    assert "機械学習ガイド" in text
    assert "ML Guide" not in text


def test_translate_title_ollama(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:11434/api/generate",
        json={"response": "機械学習の基礎"},
    )
    from matter_hub.ollama import translate_title_ollama

    out = translate_title_ollama("Basics of Machine Learning")
    assert "機械学習" in out


def test_generate_embedding(httpx_mock):
    fake_embedding = [0.1] * 768
    httpx_mock.add_response(
        url="http://localhost:11434/api/embed",
        json={"embeddings": [fake_embedding]},
    )
    result = generate_embedding("test text")
    assert len(result) == 768
    assert result[0] == 0.1
