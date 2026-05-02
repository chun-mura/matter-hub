from matter_hub.title_locale import display_title, looks_like_japanese


def test_looks_like_japanese_latin():
    assert looks_like_japanese("Introduction to Rust") is False


def test_looks_like_japanese_mixed_short():
    assert looks_like_japanese("Rust入門") is True


def test_looks_like_japanese_hiragana_only():
    assert looks_like_japanese("あいうえおかきくけこ") is True


def test_looks_like_japanese_chinese_long():
    # 漢字のみ・仮名なし・4字以上 → 中国語とみなす
    assert looks_like_japanese("人工智能的未来展望") is False


def test_looks_like_japanese_chinese_short_kanji():
    # 漢字のみ・3字以下は短すぎて判定困難 → 翻訳対象外にしない（保守的）
    assert looks_like_japanese("人工智") is True


def test_looks_like_japanese_mixed_kanji_kana():
    # 仮名が含まれれば漢字のみでも日本語
    assert looks_like_japanese("人工知能の展望") is True


def test_display_title_prefers_ja():
    assert (
        display_title({"title": "Hello", "title_ja": "こんにちは"})
        == "こんにちは"
    )


def test_display_title_falls_back():
    assert display_title({"title": "Hello"}) == "Hello"


def test_display_title_empty_ja():
    assert display_title({"title": "Hi", "title_ja": ""}) == "Hi"
