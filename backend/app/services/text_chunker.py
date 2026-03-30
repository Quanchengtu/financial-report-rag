def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """
    將長文字切成多個 chunk

    參數:
    - text: 已清洗過的純文字
    - chunk_size: 每個 chunk 的最大字元數
    - overlap: 相鄰 chunk 之間重疊的字元數

    回傳:
    - list[str]: chunk 字串列表
    """

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # 下一段往前推，但保留 overlap
        start += chunk_size - overlap

    return chunks