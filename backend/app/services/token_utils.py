def estimate_tokens(text: str) -> int:
    """Rough token estimate for mixed Chinese/English text."""
    if not text:
        return 0
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other = len(text) - cjk
    return max(1, round(cjk * 1.2 + other / 4))
