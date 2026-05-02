import requests

from app.core.config import (
    LLM_API_KEY,
    LLM_API_TIMEOUT_SECONDS,
    LLM_BASE_URL,
    LLM_MODEL_NAME,
)


class LLMServiceError(RuntimeError):
    """Raised when the LLM provider request fails or is misconfigured."""


def _build_messages(question: str, contexts: list[str]) -> list[dict]:
    context_lines = []
    for index, context in enumerate(contexts, start=1):
        context_lines.append(f"[{index}] {context.strip()}")

    context_block = "\n\n".join(context_lines)

    return [
        {
            "role": "system",
            "content": (
                "You are a financial filing assistant. Answer only using the provided context. "
                "If the context is insufficient, say you do not have enough information."
            ),
        },
        {
            "role": "user",
            "content": (
                "Question:\n"
                f"{question.strip()}\n\n"
                "Context:\n"
                f"{context_block}\n\n"
                "Return a concise grounded answer in Traditional Chinese."
            ),
        },
    ]


def generate_answer(question: str, contexts: list[str], temperature: float = 0.2) -> dict:
    """Call a chat-completions-compatible endpoint and return answer text plus usage metadata."""
    if not LLM_API_KEY:
        raise LLMServiceError("LLM_API_KEY is not set.")

    if not contexts:
        raise LLMServiceError("At least one context chunk is required.")

    response = requests.post(
        f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL_NAME,
            "messages": _build_messages(question=question, contexts=contexts),
            "temperature": temperature,
        },
        timeout=LLM_API_TIMEOUT_SECONDS,
    )

    if response.status_code >= 400:
        raise LLMServiceError(f"LLM request failed: {response.status_code} {response.text}")

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise LLMServiceError("LLM response did not contain choices.")

    message = choices[0].get("message", {})
    answer = message.get("content", "").strip()
    if not answer:
        raise LLMServiceError("LLM response content is empty.")

    return {
        "answer": answer,
        "model": payload.get("model", LLM_MODEL_NAME),
        "usage": payload.get("usage", {}),
    }
