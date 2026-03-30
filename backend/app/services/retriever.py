import re
from collections import Counter


def normalize_text(text: str) -> str:
    """
    將文字轉成較適合比對的格式
    1. 轉小寫
    2. 移除多餘符號
    3. 壓縮空白
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    """
    將文字切成 tokens
    """
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split()


def score_chunk(query_tokens: list[str], chunk: str) -> int:
    """
    根據 query tokens 對單一 chunk 做簡單計分
    分數邏輯先保持簡單：
    - token 出現一次加一次分
    """
    chunk_tokens = tokenize(chunk)
    if not chunk_tokens:
        return 0

    chunk_counter = Counter(chunk_tokens)

    score = 0
    for token in query_tokens:
        score += chunk_counter.get(token, 0)

    return score


def retrieve_relevant_chunks(
    question: str,
    chunks: list[str],
    top_k: int = 3
) -> list[dict]:
    """
    從 chunks 中找出和問題最相關的前幾段
    回傳格式包含：
    - chunk_index
    - score
    - text
    """
    if not question:
        return []

    if not chunks:
        return []

    query_tokens = tokenize(question)
    if not query_tokens:
        return []

    scored_chunks = []

    for idx, chunk in enumerate(chunks):
        score = score_chunk(query_tokens, chunk)

        if score > 0:
            scored_chunks.append({
                "chunk_index": idx,
                "score": score,
                "text": chunk
            })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)

    return scored_chunks[:top_k]