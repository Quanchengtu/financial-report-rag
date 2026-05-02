# 把使用者問題轉成英文關鍵字，對每個財報 chunk 進行關鍵字與片語比對，排除雜訊段落，根據財報章節加權，最後回傳分數最高的幾個相關段落
import re
from collections import Counter

STOPWORDS = {   # 移除對搜尋幫助不大的字
    "the", "is", "are", "a", "an", "of", "to", "in", "on", "at", "for", "and",
    "or", "but", "if", "then", "than", "with", "by", "as", "from", "that",
    "this", "these", "those", "be", "been", "being", "was", "were", "it",
    "its", "their", "his", "her", "them", "they", "we", "you", "he", "she",
    "do", "does", "did", "have", "has", "had", "not", "no", "yes", "into",
    "about", "over", "under", "after", "before", "during", "through", "such"
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)  # 將「不是英文、數字、空白」的符號換成空白
    text = re.sub(r"\s+", " ", text)          # 多個空格壓縮成一個空格
    return text.strip()


def tokenize(text: str) -> list[str]:           # 切成關鍵字
    normalized = normalize_text(text)
    if not normalized:
        return []

    return [
        token for token in normalized.split()  # 用空白切成字串
        if token not in STOPWORDS and len(token) > 1
    ]


def get_query_phrases(question: str) -> list[str]:   # 將問題中的token（單個字）組成一句片語
    tokens = tokenize(question)
    if len(tokens) < 2:
        return []
    return [" ".join(tokens)]


def count_phrase_occurrences(text: str, phrase: str) -> int:   # 計算某個phrase在text裡完整出現幾次
    if not text or not phrase:
        return 0
    return len(re.findall(rf"\b{re.escape(phrase)}\b", text))  # 只找完整的 phrase，不找嵌在別的字裡面的東西 .escape()跳脫字元 \b單字邊界


def is_noisy_chunk(text: str) -> bool:  # 排除一些不適合拿來回答問題的 chunk（雜訊）
    if not text or not text.strip():
        return True

    stripped = text.strip()
    lower = stripped.lower()

    # 太短通常是目錄、標題碎片
    if len(stripped) < 80:
        return True

    noisy_patterns = [   # 利用一些pattern排除一些目錄格式
        r"table of contents",
        r"item\s+1a\.\s+risk factors\s+\d+",  # \s+ 一或多空白 \.句點 \d+ 一或多數字
        r"item\s+1b\."
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

# （核心部分）針對「一個問題」和「一個 chunk」計算相關性分數
def score_chunk(question: str, chunk_text: str, section_name: str | None = None) -> dict:
    query_tokens = tokenize(question)     # 將問題也切成token
    if not query_tokens:
        return {"score": 0, "matched_terms": []}

    if is_noisy_chunk(chunk_text):
        return {"score": 0, "matched_terms": []}

    chunk_normalized = normalize_text(chunk_text)   # 用作片語搜尋
    chunk_tokens = tokenize(chunk_text)             # 用作單字比對
    if not chunk_tokens:
        return {"score": 0, "matched_terms": []}

    chunk_counter = Counter(chunk_tokens)   # 計算chunk中各個token出現的次數
    matched_terms = []   # 存query_token和chunk_token同時存在的terms
    raw_score = 0

    for token in query_tokens:
        freq = chunk_counter.get(token, 0)
        if freq > 0:
            raw_score += freq  # 計算query_token在chunk_token同時出現的總數 包含重複出現
            matched_terms.append(token)

    query_phrases = get_query_phrases(question)   # 抓完整片語 若出現比單字加分比重更高 因完整出現更能代表關聯性 e.g. risk factors
    for phrase in query_phrases:
        phrase_count = count_phrase_occurrences(chunk_normalized, phrase)
        if phrase_count > 0:
            raw_score += phrase_count * 4   # 每出現一次完整片語+4分
            matched_terms.append(phrase)

    q = question.lower()   # 根據section name 額外加分 （利用section_parser.py成果）
    if section_name:
        if "risk factor" in q and section_name == "item_1a_risk_factors":
            raw_score += 8
        elif "market risk" in q and section_name == "item_7a_market_risk":
            raw_score += 8
        elif "business" in q and section_name == "item_1_business":
            raw_score += 6
        elif "legal proceedings" in q and section_name == "item_3_legal_proceedings":
            raw_score += 6

    # 對 cross-reference (引用）型 chunk “扣分”  
    lower_chunk = chunk_text.lower()
    if "refer to" in lower_chunk:   # e.g. Please refer to Risk Factors section.
        raw_score -= 3
    if "for a discussion of" in lower_chunk:
        raw_score -= 3

    chunk_length = max(1, len(chunk_tokens))
    # 關鍵字密度加分
    density_bonus = min(3, int((raw_score / chunk_length) * 100))  # 最多加3分 避免密度 bonus 過度影響結果

    final_score = raw_score + density_bonus
    if final_score < 0:   # 避免扣到負分
        final_score = 0

    return {
        "score": final_score,
        "matched_terms": sorted(set(matched_terms)) # set()去重
    }

# 提供外部呼叫的主函式 
def retrieve_relevant_chunks(    # 輸入一個問題、一堆 chunks，回傳最相關(分數高）的前 top_k 個 chunks
    question: str,
    chunks: list[dict],
    top_k: int = 3
) -> list[dict]:
    if not question or not chunks or top_k <= 0:
        return []

    scored_chunks = []   # 放所有「有」分數的chunks

    for chunk in chunks: # chunks data type: dict
        text = chunk.get("text", "")   # 從 chunk 裡取 "text" 這個 key，若無就給預設值 ""
        section_name = chunk.get("section_name")
        chunk_index = chunk.get("chunk_index")

        scored = score_chunk(   # line 82
            question=question,
            chunk_text=text,
            section_name=section_name
        )

        if scored["score"] > 0:   # 只留下 score > 0 的 chunks
            scored_chunks.append({
                "chunk_index": chunk_index,
                "section_name": section_name,
                "score": scored["score"],
                "matched_terms": scored["matched_terms"],
                "text": text
            })
    # 主要排序：score由高至低（有reverse) / 次要排序(若score相同）：chunk_index越小越前面（有negative sign) 通常財報裡前面的段落可能更接近主章節開頭
    scored_chunks.sort(   
        key=lambda x: (x["score"], -x["chunk_index"]),
        reverse=True
    )

    return scored_chunks[:top_k]

''' scored_chunk example
{
    "chunk_index": 12,
    "section_name": "item_1a_risk_factors",
    "score": 20,
    "matched_terms": ["risk", "factors", "risk factors"],
    "text": "Our business is subject to risks..."
}
'''

# Rule-based keyword retriever
''' 評分依據：
1. 關鍵字出現次數
2. 完整片語命中
3. 財報 section 加權
4. 雜訊 chunk 過濾
5. cross-reference 扣分
6. 關鍵字密度加分
'''