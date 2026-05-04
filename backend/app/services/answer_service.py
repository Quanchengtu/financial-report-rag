# 將 retriever 找到的 chunks，整理成可回答使用者問題的答案
from app.core.config import RAG_LLM_MAX_CHARS_PER_CHUNK, RAG_LLM_MAX_CONTEXT_CHUNKS
from app.services.llm_service import generate_answer, LLMServiceError
import re   # Python 內建的正規表示式工具，用來切句子、過濾雜訊
from app.services.retriever import tokenize, normalize_text   # 將問題和句子轉成較好比對的格式
from app.services.embedding_service import embed_text
import math


NOISY_SENTENCE_PATTERNS = [
    r"^\s*item\s+\d+[a-z]?\b",  # ^表開頭
    r"^\s*risk factors\s+\d+",
    r"table of contents",
    r"unresolved staff comments",
    r"refer to [“\"']?item",
    r"see [“\"']?item",
    r"for a discussion of",
]

# 若句子包含某些 keywords，就自動歸類成某個 topic
TOPIC_RULES = [   #####
    {
        "label": "changing industry demand",
        "keywords": ["evolving", "industry", "markets", "demand", "competition", "market share"]
    },
    {
        "label": "counterparty and financing risk",
        "keywords": ["counterparty", "financial commitments", "financing", "project delays", "insolvency"]
    },
    {
        "label": "supply chain and inventory risk",
        "keywords": ["supply", "purchase obligations", "lead times", "inventory", "design of future products"]
    },
    {
        "label": "talent retention risk",
        "keywords": ["attract", "retain", "motivate", "executives", "key employees", "talent"]
    },
    {
        "label": "regulatory and legal risk",
        "keywords": ["regulations", "compliance", "regulatory", "legal", "antitrust", "data privacy"]
    },
    {
        "label": "cybersecurity and data protection risk",
        "keywords": ["cyber", "cybersecurity", "security", "data protection", "breaches", "attacks"]
    },
    {
        "label": "stock price and operating volatility",
        "keywords": ["stock price", "fluctuate", "operating results", "volatility", "investors"]
    },
    {
        "label": "climate and macroeconomic risk",
        "keywords": ["climate", "economic conditions", "global operating", "international sales"]
    },
]


def split_into_sentences(text: str) -> list[str]:
    """
    將chunk文字粗略切成句子
    """
    if not text or not text.strip():
        return []

    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)   # 根據.!?後的空白切割句子

    cleaned = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:   # 頭尾空白清掉後若不是空字串就放入cleaned[]
            cleaned.append(sentence)

    return cleaned


def is_noisy_sentence(sentence: str) -> bool:
    """
    過濾明顯不像答案內容的句子 判斷雜訊句子 避免 answer_service 把無意義的句子拿去組答案或引用來源
    """
    if not sentence or not sentence.strip():
        return True

    s = sentence.strip()
    s_lower = s.lower()

    if len(s) < 40:
        return True

    digit_count = sum(ch.isdigit() for ch in s)
    if digit_count > 0 and digit_count / max(len(s), 1) > 0.2:   # 數字比例高的句子視為noisy_sentence
        return True

    for pattern in NOISY_SENTENCE_PATTERNS:
        if re.search(pattern, s_lower):
            return True

    return False


def score_sentence(
    question: str,
    sentence: str,
    question_embedding: list[float] | None = None
) -> float:
    """
    從一大段財報文字中，找出最可能回答使用者問題的句子
    使用 hybrid scoring：
    1. embedding semantic similarity（80%)語意相似度
    2. token overlap（20%）關鍵字重疊
    回傳分數越高關聯性越高
    """

    if not question or not question.strip():
        return 0.0
    if not sentence or not sentence.strip():
        return 0.0

    # --- semantic similarity（主體） ---
    try:
        if question_embedding is None:
            question_embedding = embed_text(question)

        s_emb = embed_text(sentence)
        semantic_score = cosine_similarity(question_embedding, s_emb)   # 計算問題 embedding 和句子 embedding 的相似程度
    except Exception:
        semantic_score = 0.0

    # --- token overlap（輔助） ---
    question_tokens = tokenize(question)
    sentence_tokens = tokenize(sentence)

    overlap_score = 0.0
    if question_tokens and sentence_tokens:
        sentence_token_set = set(sentence_tokens)   # 去重/查詢某個詞是否存在比list快
        overlap_count = sum(1 for t in question_tokens if t in sentence_token_set)  # 問題token出現在句子token就+1
        overlap_score = overlap_count / len(question_tokens)   # 計算問題toke有有多少比例出現在句子token

    # --- final score（權重組合） ---
    final_score = (semantic_score * 0.8) + (overlap_score * 0.2)

    return final_score


def select_supporting_sentences(
    question: str,
    retrieved_chunks: list[dict],
    max_sentences: int = 4
) -> list[dict]:
    """
    從 retrieved chunks 裡挑出最相關且比較像(最相關）答案的句子
    """
    candidates = []

    question_embedding = embed_text(question)

    # rank 越前面的 chunk，代表 retriever 原本判斷它越相關
    for chunk_rank, chunk in enumerate(retrieved_chunks, start=1):
        chunk_text = chunk.get("text", "")   # 從chunk取出metadata及text
        section_name = chunk.get("section_name")
        chunk_index = chunk.get("chunk_index")
        retrieval_score = chunk.get("score")   # 整個chunk對問題的相關程度

        sentences = split_into_sentences(chunk_text)

        for sentence_index, sentence in enumerate(sentences):
            if is_noisy_sentence(sentence):
                continue

            sentence_score = score_sentence(   # 單一句子跟問題的相關程度
                question,
                sentence,
                question_embedding=question_embedding
            )
            if sentence_score < 0.35:   # 避免語意相似度太低的句子被選入 此數值可根據回答精準度和召回率調整 並非固定值
                continue

            candidates.append({
                "sentence": sentence,
                "sentence_score": sentence_score,
                "chunk_rank": chunk_rank,
                "chunk_index": chunk_index,
                "section_name": section_name,
                "retrieval_score": retrieval_score,
                "sentence_index": sentence_index
            })

    if not candidates:
        return []

    candidates.sort(
        key=lambda x: (
            x["sentence_score"],
            x["retrieval_score"] if x["retrieval_score"] is not None else 0,  # 沒有值就當作 0
            -x["chunk_rank"]
        ),
        reverse=True
    )

    # 開始從排序後的 candidates 裡挑出最後結果
    selected = []
    seen = set()   # 避免重複句

    for item in candidates:   # 取到所設定的max數量及停止並回傳結果
        normalized_sentence = normalize_text(item["sentence"])   # 句子做標準化方便去重
        if normalized_sentence in seen:
            continue

        seen.add(normalized_sentence)
        selected.append(item)  # 句子＋整包metadata都放入

        if len(selected) >= max_sentences:
            break

    return selected

# 從已經選出來的 supporting sentences 裡面，根據關鍵字規則判斷這些句子提到哪些主題，最後回傳主題列表
def detect_topics_from_sentences(supporting_sentences: list[dict]) -> list[str]:
    """
    從上面選出的supporting_sentences推測主題類別
    """
    detected_topics = []

    for item in supporting_sentences:
        #sentence = item["sentence"].lower()
        sentence = item.get("sentence", "").lower()

        for rule in TOPIC_RULES:
            if rule["label"] in detected_topics:  # 避免重複加入同個主題
                continue

            if any(keyword in sentence for keyword in rule["keywords"]):   # any() 其中一個是 TRUE 整體結果就是 TRUE
                detected_topics.append(rule["label"])

    return detected_topics


def format_topic_list(topics: list[str]) -> str:
    """
    將 topic list 轉成自然英文列舉(A, B and C)
    """
    if not topics:
        return ""

    if len(topics) == 1:
        return topics[0]

    if len(topics) == 2:
        return f"{topics[0]} and {topics[1]}"

    return ", ".join(topics[:-1]) + f", and {topics[-1]}"   # topics[:-1] 除了最後ㄧ個的所有元素


def build_summary_answer(question: str, supporting_sentences: list[dict]) -> str:
    """
    把 supporting sentences 整理成比較像真正回答的 summary (非LLM 生成答案 而是根據規則組合出回答)
    """
    if not supporting_sentences:
        return "I could not find enough relevant evidence in the filing to produce a grounded summary answer."

    question_lower = question.lower()
    topics = detect_topics_from_sentences(supporting_sentences)

    if "risk factor" in question_lower:     #####
        if topics:
            topic_text = format_topic_list(topics[:4])
            return (
                f"The filing highlights several main risk factors, including {topic_text}. "
                f"These risks could negatively affect the company's business, financial condition, and operating results."
            )

        return (   # 沒有抓到具體 topic 採保守回答
            "The filing says the company's main risk factors could harm its business, financial condition, "
            "results of operations, reputation, and stock price."
        )

    # 一般問題 fallback
    first_sentence = supporting_sentences[0]["sentence"]
    return first_sentence


def build_grounded_answer(
    question: str,
    retrieved_chunks: list[dict],
    max_sentences: int = 4
) -> dict:
    """
    根據 retrieved chunks 組出 grounded answer
    """
    if not retrieved_chunks:
        return {
            "answer": "I could not find enough relevant evidence in the filing to answer this question.",
            "summary_answer": "I could not find enough relevant evidence in the filing to produce a grounded summary answer.",
            "supporting_sentences": [],
            "sources": [],
            "detected_topics": []
        }

    supporting_sentences = select_supporting_sentences(
        question=question,
        retrieved_chunks=retrieved_chunks,
        max_sentences=max_sentences
    )
    # 把所有被選中的 supporting sentences 接成一段 answer (extractive answer)
    if supporting_sentences:
        extractive_answer = " ".join(item["sentence"] for item in supporting_sentences)
    else:
        fallback_parts = []
        for chunk in retrieved_chunks[:2]:
            text = chunk.get("text", "").strip()
            if text:
                fallback_parts.append(text[:300])

        extractive_answer = " ".join(fallback_parts) if fallback_parts else (
            "I could not generate a grounded answer from the retrieved filing chunks."
        )

    detected_topics = detect_topics_from_sentences(supporting_sentences)
    summary_answer = build_summary_answer(question, supporting_sentences)

    sources = []
    for rank, chunk in enumerate(retrieved_chunks, start=1):
        sources.append({
            "source_rank": rank,
            "chunk_index": chunk.get("chunk_index"),
            "section_name": chunk.get("section_name"),
            "score": chunk.get("score"),
            "text_excerpt": chunk.get("text", "")[:500]
        })

    return {
        "answer": extractive_answer,
        "summary_answer": summary_answer,
        "supporting_sentences": supporting_sentences,
        "sources": sources,
        "detected_topics": detected_topics
    }


def build_llm_grounded_answer(
    question: str,
    retrieved_chunks: list[dict],
    max_context_chunks: int = RAG_LLM_MAX_CONTEXT_CHUNKS,
    max_chars_per_chunk: int = RAG_LLM_MAX_CHARS_PER_CHUNK, #####
    temperature: float = 0.2,   # 控制 LLM 回答的隨機程度(低/穩定)
) -> dict:
    """Generate a grounded answer from retrieved chunks with LLM."""
    if not retrieved_chunks:
        raise LLMServiceError("No retrieved chunks were provided for LLM answer generation.")

    contexts: list[str] = []   # 建立一個空 list，準備放要給 LLM 的 context
    selected_chunks = retrieved_chunks[:max_context_chunks]

    for chunk in selected_chunks:     # 從 chunk 的 dict 結構中取 "text" 的欄位資料
        text = (chunk.get("text") or "").strip()
        if not text:
            continue

        section_name = chunk.get("section_name") or "unknown_section"
        chunk_index = chunk.get("chunk_index")

        chunk_label = f"{section_name}:{chunk_index}" if chunk_index is not None else section_name   # e.g. "Risk Factors:12"
        contexts.append(f"Source={chunk_label}\n{text[:max_chars_per_chunk]}")

    if not contexts:
        raise LLMServiceError("Retrieved chunks did not include usable text contexts.")

    # 呼叫 LLM 產生答案
    llm_result = generate_answer(
        question=question,
        contexts=contexts,
        temperature=temperature
    )

    # 將提供給 LLM 的來源 chunks 整理成 sources
    sources = []
    for rank, chunk in enumerate(selected_chunks, start=1):   # line 351
        sources.append({
            "source_rank": rank,
            "chunk_index": chunk.get("chunk_index"),
            "section_name": chunk.get("section_name"),
            "score": chunk.get("score"),
            "text_excerpt": (chunk.get("text") or "")[:500]
        })

    return {
        "answer": llm_result["answer"],
        "summary_answer": llm_result["answer"],
        "supporting_sentences": [],
        "sources": sources,
        "detected_topics": [],
        "model": llm_result.get("model"),
        "usage": llm_result.get("usage", {}),
    }

# 計算兩個向量的餘弦相似度 用來判斷兩段文字的語意向量有多接近 最後回傳相似度分數
def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))   # 內積
    norm1 = math.sqrt(sum(a * a for a in vec1))            # 向量長度
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:   # 避免分母可能為0
        return 0.0

    return dot_product / (norm1 * norm2)      # cosine similarity