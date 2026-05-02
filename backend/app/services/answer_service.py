# 將 retriever 找到的 chunks，整理成可回答使用者問題的答案
from app.core.config import RAG_LLM_MAX_CHARS_PER_CHUNK, RAG_LLM_MAX_CONTEXT_CHUNKS
from app.services.llm_service import generate_answer, LLMServiceError
import re   # Python 內建的正規表示式工具，用來切句子、過濾雜訊
from app.services.retriever import tokenize, normalize_text   # 將問題和句子轉成較好比對的格式


NOISY_SENTENCE_PATTERNS = [
    r"^\s*item\s+\d+[a-z]?\b",  # ^表開頭
    r"^\s*risk factors\s+\d+",
    r"table of contents",
    r"unresolved staff comments",
    r"refer to [“\"']?item",
    r"see [“\"']?item",
    r"for a discussion of",
]

# 若句子包含某些keywords，就自動歸類成某個topic
TOPIC_RULES = [
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
        if sentence:   # 頭尾空白清掉後若不是空字串就放入cleaned
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


def score_sentence(question: str, sentence: str) -> int:
    """
    計算某單一句子和使用者問題的相關程度
    """
    question_tokens = tokenize(question)
    sentence_tokens = tokenize(sentence)

    if not question_tokens or not sentence_tokens:
        return 0

    score = 0
    sentence_token_set = set(sentence_tokens)

    for token in question_tokens:   # 問題中的自若出現在句子中 分數+1
        if token in sentence_token_set:
            score += 1

    normalized_question = normalize_text(question)
    normalized_sentence = normalize_text(sentence)

    if normalized_question and normalized_question in normalized_sentence:
        score += 3

    sentence_lower = sentence.lower()
    bonus_keywords = [
        "may adversely affect",
        "could harm",
        "could adversely affect",
        "may negatively impact",
        "uncertainty",
        "risk",
        "failure to",
        "depend on",
    ]
    for keyword in bonus_keywords:
        if keyword in sentence_lower:
            score += 2

    return score


def select_supporting_sentences(
    question: str,
    retrieved_chunks: list[dict],
    max_sentences: int = 4
) -> list[dict]:
    """
    從 retrieved chunks 裡挑出最相關且比較像(最相關）答案的句子
    """
    candidates = []

    for chunk_rank, chunk in enumerate(retrieved_chunks, start=1):
        chunk_text = chunk.get("text", "")
        section_name = chunk.get("section_name")
        chunk_index = chunk.get("chunk_index")
        retrieval_score = chunk.get("score")

        sentences = split_into_sentences(chunk_text)

        for sentence_index, sentence in enumerate(sentences):
            if is_noisy_sentence(sentence):
                continue

            sentence_score = score_sentence(question, sentence)
            if sentence_score <= 0:
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
            x["retrieval_score"] if x["retrieval_score"] is not None else 0,
            -x["chunk_rank"]
        ),
        reverse=True
    )

    selected = []
    seen = set()

    for item in candidates:
        normalized_sentence = normalize_text(item["sentence"])
        if normalized_sentence in seen:
            continue

        seen.add(normalized_sentence)
        selected.append(item)

        if len(selected) >= max_sentences:
            break

    return selected


def detect_topics_from_sentences(supporting_sentences: list[dict]) -> list[str]:
    """
    從 supporting sentences 推測主要風險主題
    """
    detected_topics = []

    for item in supporting_sentences:
        sentence = item["sentence"].lower()

        for rule in TOPIC_RULES:
            if rule["label"] in detected_topics:
                continue

            if any(keyword in sentence for keyword in rule["keywords"]):
                detected_topics.append(rule["label"])

    return detected_topics


def format_topic_list(topics: list[str]) -> str:
    """
    將 topic list 轉成自然英文列舉
    """
    if not topics:
        return ""

    if len(topics) == 1:
        return topics[0]

    if len(topics) == 2:
        return f"{topics[0]} and {topics[1]}"

    return ", ".join(topics[:-1]) + f", and {topics[-1]}"


def build_summary_answer(question: str, supporting_sentences: list[dict]) -> str:
    """
    把 supporting sentences 整理成比較像真正回答的 summary
    """
    if not supporting_sentences:
        return "I could not find enough relevant evidence in the filing to produce a grounded summary answer."

    question_lower = question.lower()
    topics = detect_topics_from_sentences(supporting_sentences)

    if "risk factor" in question_lower:
        if topics:
            topic_text = format_topic_list(topics[:4])
            return (
                f"The filing highlights several main risk factors, including {topic_text}. "
                f"These risks could negatively affect the company's business, financial condition, and operating results."
            )

        return (
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
    max_chars_per_chunk: int = RAG_LLM_MAX_CHARS_PER_CHUNK,
    temperature: float = 0.2,
) -> dict:
    """Generate a grounded answer from retrieved chunks with LLM."""
    if not retrieved_chunks:
        raise LLMServiceError("No retrieved chunks were provided for LLM answer generation.")

    contexts: list[str] = []
    selected_chunks = retrieved_chunks[:max_context_chunks]

    for chunk in selected_chunks:
        text = (chunk.get("text") or "").strip()
        if not text:
            continue

        section_name = chunk.get("section_name") or "unknown_section"
        chunk_index = chunk.get("chunk_index")
        chunk_label = f"{section_name}:{chunk_index}" if chunk_index is not None else section_name
        contexts.append(f"Source={chunk_label}\n{text[:max_chars_per_chunk]}")

    if not contexts:
        raise LLMServiceError("Retrieved chunks did not include usable text contexts.")

    llm_result = generate_answer(
        question=question,
        contexts=contexts,
        temperature=temperature
    )

    sources = []
    for rank, chunk in enumerate(selected_chunks, start=1):
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
