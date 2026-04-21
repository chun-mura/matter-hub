"""タイトルが日本語かどうかの判定と表示用ヘルパ。"""


def looks_like_japanese(text: str) -> bool:
    """ひらがな・カタカナ・漢字が一定以上あれば日本語とみなす。"""
    if not text or not text.strip():
        return True
    jp = 0
    for ch in text:
        o = ord(ch)
        if (
            0x3040 <= o <= 0x309F
            or 0x30A0 <= o <= 0x30FF
            or 0x4E00 <= o <= 0x9FFF
            or 0x3400 <= o <= 0x4DBF
        ):
            jp += 1
    n = len(text)
    if jp == 0:
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
