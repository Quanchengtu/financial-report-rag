"""Small LangChain-powered helpers that do not replace the existing RAG flow."""

import json

from app.core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME, RAG_LLM_TEMPERATURE
from app.services.llm_service import LLMServiceError

QUERY_REWRITE_SYSTEM_PROMPT = """
You help prepare user questions for retrieval over SEC financial filings.
Rewrite the question into a concise English search query that keeps important financial terms,
company references, years, filing sections, and metric names. Classify the user's intent.
Return only valid JSON with these keys: original_question, rewritten_query, intent.
Allowed intent values: financial_metric, risk_factor, business_overview, legal_or_regulatory,
management_discussion, other.
""".strip()


def parse_query_rewrite_json(raw_text: str, original_question: str) -> dict:
    """Parse and normalize a LangChain JSON response for stable API output."""
    if not raw_text or not raw_text.strip():
        raise LLMServiceError("LangChain query rewrite response is empty.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMServiceError("LangChain query rewrite response was not valid JSON.") from exc

    rewritten_query = str(payload.get("rewritten_query", "")).strip()
    intent = str(payload.get("intent", "other")).strip() or "other"
    if not rewritten_query:
        raise LLMServiceError("LangChain query rewrite response did not include rewritten_query.")

    return {
        "mode": "langchain_query_rewrite_v1",
        "original_question": str(payload.get("original_question") or original_question).strip(),
        "rewritten_query": rewritten_query,
        "intent": intent,
    }


def rewrite_question_for_retrieval(question: str, temperature: float = RAG_LLM_TEMPERATURE) -> dict:
    """
    Rewrite a user question into a retrieval-friendly query using LangChain.

    This is intentionally a sidecar feature: callers can inspect the rewritten query without changing
    the existing rule-based, semantic, or hybrid RAG answer flows.
    """
    if not question or not question.strip():
        raise LLMServiceError("Question is required.")
    if not LLM_API_KEY:
        raise LLMServiceError("LLM_API_KEY is not set.")

    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", QUERY_REWRITE_SYSTEM_PROMPT),
            ("user", "Question:\n{question}"),
        ]
    )
    model = ChatOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        model=LLM_MODEL_NAME,
        temperature=temperature,
    )
    chain = prompt | model | StrOutputParser()
    raw_text = chain.invoke({"question": question.strip()})
    result = parse_query_rewrite_json(raw_text, original_question=question)
    result["model"] = LLM_MODEL_NAME
    return result
