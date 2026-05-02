"""タイトルが日本語かどうかの判定と表示用ヘルパ。"""


def looks_like_japanese(text: str) -> bool:
    """ひらがな・カタカナ・漢字が一定以上あれば日本語とみなす。

    漢字（CJK）は日中共通のため、仮名ゼロかつ漢字4字以上は中国語と判定する。
    """
    if not text or not text.strip():
        return True
    kana = 0  # ひらがな・カタカナ（日本語固有）
    cjk = 0   # 漢字（日中共通）
    for ch in text:
        o = ord(ch)
        if 0x3040 <= o <= 0x309F or 0x30A0 <= o <= 0x30FF:
            kana += 1
        elif 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            cjk += 1
    jp = kana + cjk
    n = len(text)
    if jp == 0:
        return False
    # 仮名なし・漢字4字以上 → 中国語の可能性が高い
    if kana == 0 and cjk >= 4:
        return False
    if n <= 8 and jp >= 1:
        return True
    return jp >= max(2, int(n * 0.12) + 1)


def display_title(article: dict) -> str:
    """一覧・検索表示用。日本語タイトルがあればそれを使う。"""
    tj = article.get("title_ja")
    if tj is not None and str(tj).strip():
        return str(tj).strip()
    t = article.get("title")
    return str(t).strip() if t else ""
