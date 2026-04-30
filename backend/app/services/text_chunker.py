import re   # regular expression 正規表示式套件 


def split_into_paragraphs(text: str) -> list[str]:
    """
    先依雙換行切成段落，並清掉多餘空白
    """
    paragraphs = re.split(r"\n\s*\n", text)
    cleaned_paragraphs = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if paragraph:   # 避免空字串被放入結果
            cleaned_paragraphs.append(paragraph)

    return cleaned_paragraphs


def find_best_split_position(text: str, max_length: int) -> int:
    """
    在 max_length 附近找較自然的切點
    優先順序：
    1. 句號/問號/驚嘆號後
    2. 分號/冒號後
    3. 空白
    4. 實在找不到就硬切
    """
    if len(text) <= max_length:
        return len(text)

    search_start = max(0, max_length - 150)
    candidate = text[:max_length]

    # 1. 優先找句尾符號
    sentence_matches = list(re.finditer(r"[.!?]\s", candidate[search_start:]))
    if sentence_matches:
        match = sentence_matches[-1]   # 取「最後一個」符合的位置, 盡量接近max_length才切
        return search_start + match.end()

    # 2. 再找分號、冒號、逗號
    punctuation_matches = list(re.finditer(r"[;:,]\s", candidate[search_start:]))
    if punctuation_matches:
        match = punctuation_matches[-1]
        return search_start + match.end()

    # 3. 再找空白
    space_pos = candidate.rfind(" ", search_start)
    if space_pos != -1:
        return space_pos

    # 4. 最後才硬切
    return max_length


def split_long_paragraph(paragraph: str, chunk_size: int, overlap: int) -> list[str]:
    """
    如果單一段落太長，再進一步切小塊
    """
    chunks = []   # 儲存切好的小段
    start = 0     # 目前從 paragraph 的哪個位置開始切
    text_length = len(paragraph)

    while start < text_length:
        remaining_text = paragraph[start:]

        if len(remaining_text) <= chunk_size:  # 剩下的小於chunk_size不用再切直接append
            chunk = remaining_text.strip()
            if chunk:
                chunks.append(chunk)
            break

        split_pos = find_best_split_position(remaining_text, chunk_size) 
        chunk = remaining_text[:split_pos].strip()

        if chunk:
            chunks.append(chunk)

        # 將下一次切點往前移，overlap 保留前後文
        start += max(1, split_pos - overlap)  

    return chunks


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """
    改良版 chunking：
    1. 先按段落切
    2. 小段落合併
    3. 太長段落再細切
    """

    if not text:   # 文字是空的回傳空陣列
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    paragraphs = split_into_paragraphs(text)
    chunks = []
    current_chunk = ""  # 組裝中的chunk

    for paragraph in paragraphs:
        # 如果單一 paragraph 太長，先把目前累積的 chunk 存起來
        if len(paragraph) > chunk_size:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = ""

            long_paragraph_chunks = split_long_paragraph(
                paragraph=paragraph,
                chunk_size=chunk_size,
                overlap=overlap
            )
            chunks.extend(long_paragraph_chunks)
            continue

        # 試著把短段落併進 current_chunk
        if not current_chunk:
            current_chunk = paragraph
        elif len(current_chunk) + 2 + len(paragraph) <= chunk_size: # 可以合併入chunk 合併後大小沒有oversize
            current_chunk += "\n\n" + paragraph
        else:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph

    if current_chunk.strip():     # 最後一個current_chunk需要補存入chunk
        chunks.append(current_chunk.strip())

    return chunks