import re
from collections import Counter

STOPWORDS = {
    "the", "is", "are", "a", "an", "of", "to", "in", "on", "at", "for", "and",
    "or", "but", "if", "then", "than", "with", "by", "as", "from", "that",
    "this", "these", "those", "be", "been", "being", "was", "were", "it",
    "its", "their", "his", "her", "them", "they", "we", "you", "he", "she",
    "do", "does", "did", "have", "has", "had", "not", "no", "yes", "into",
    "about", "over", "under", "after", "before", "during", "through", "such"
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    return [
        token for token in normalized.split()
        if token not in STOPWORDS and len(token) > 1
    ]


def get_query_phrases(question: str) -> list[str]:
    tokens = tokenize(question)
    if len(tokens) < 2:
        return []
    return [" ".join(tokens)]


def count_phrase_occurrences(text: str, phrase: str) -> int:
    if not text or not phrase:
        return 0
    return len(re.findall(rf"\b{re.escape(phrase)}\b", text))


def is_noisy_chunk(text: str) -> bool:
    if not text or not text.strip():
        return True

    stripped = text.strip()
    lower = stripped.lower()

    # 太短通常是目錄、標題碎片
    if len(stripped) < 80:
        return True

    noisy_patterns = [
        r"table of contents",
        r"item\s+1a\.\s+risk factors\s+\d+",
        r"item\s+1b\.",
        r"unresolved staff comments",
        r"item\s+1c",
        r"cybersecurity",
    ]
    for pattern in noisy_patterns:
        if re.search(pattern, lower):
            return True

    # 數字比例過高，常是頁碼/表格/目錄片段
    digit_count = sum(ch.isdigit() for ch in stripped)
    if digit_count > 0 and digit_count / max(len(stripped), 1) > 0.15:
        return True

    # token 太少通常不是有效內容
    tokens = tokenize(stripped)
    if len(tokens) < 12:
        return True

    return False


def score_chunk(question: str, chunk_text: str, section_name: str | None = None) -> dict:
    query_tokens = tokenize(question)
    if not query_tokens:
        return {"score": 0, "matched_terms": []}

    if is_noisy_chunk(chunk_text):
        return {"score": 0, "matched_terms": []}

    chunk_normalized = normalize_text(chunk_text)
    chunk_tokens = tokenize(chunk_text)
    if not chunk_tokens:
        return {"score": 0, "matched_terms": []}

    chunk_counter = Counter(chunk_tokens)
    matched_terms = []
    raw_score = 0

    for token in query_tokens:
        freq = chunk_counter.get(token, 0)
        if freq > 0:
            raw_score += freq
            matched_terms.append(token)

    query_phrases = get_query_phrases(question)
    for phrase in query_phrases:
        phrase_count = count_phrase_occurrences(chunk_normalized, phrase)
        if phrase_count > 0:
            raw_score += phrase_count * 4
            matched_terms.append(phrase)

    q = question.lower()
    if section_name:
        if "risk factor" in q and section_name == "item_1a_risk_factors":
            raw_score += 8
        elif "market risk" in q and section_name == "item_7a_market_risk":
            raw_score += 8
        elif "business" in q and section_name == "item_1_business":
            raw_score += 6
        elif "legal proceedings" in q and section_name == "item_3_legal_proceedings":
            raw_score += 6

    # 對 cross-reference 型 chunk 扣分
    lower_chunk = chunk_text.lower()
    if "refer to" in lower_chunk:
        raw_score -= 3
    if "for a discussion of" in lower_chunk:
        raw_score -= 3

    chunk_length = max(1, len(chunk_tokens))
    density_bonus = min(3, int((raw_score / chunk_length) * 100))

    final_score = raw_score + density_bonus
    if final_score < 0:
        final_score = 0

    return {
        "score": final_score,
        "matched_terms": sorted(set(matched_terms))
    }


def retrieve_relevant_chunks(
    question: str,
    chunks: list[dict],
    top_k: int = 3
) -> list[dict]:
    if not question or not chunks or top_k <= 0:
        return []

    scored_chunks = []

    for chunk in chunks:
        text = chunk.get("text", "")
        section_name = chunk.get("section_name")
        chunk_index = chunk.get("chunk_index")

        scored = score_chunk(
            question=question,
            chunk_text=text,
            section_name=section_name
        )

        if scored["score"] > 0:
            scored_chunks.append({
                "chunk_index": chunk_index,
                "section_name": section_name,
                "score": scored["score"],
                "matched_terms": scored["matched_terms"],
                "text": text
            })

    scored_chunks.sort(
        key=lambda x: (x["score"], -x["chunk_index"]),
        reverse=True
    )

    return scored_chunks[:top_k]