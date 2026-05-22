import requests   # 呼叫外部LLM API
from requests import RequestException

from app.core.config import (
    LLM_API_KEY,
    LLM_API_TIMEOUT_SECONDS,
    LLM_BASE_URL,
    LLM_MODEL_NAME,
)

# 自定義錯誤
class LLMServiceError(RuntimeError):
    """Raised when the LLM provider request fails or is misconfigured."""

# 將使用者問題＆ RAG 檢索出的 context 整理成可輸入 LLM 的 messages 格式
def _build_messages(question: str, contexts: list[str]) -> list[dict]:
    context_lines = []
    for index, context in enumerate(contexts, start=1):  # 編號
        context_lines.append(f"[{index}] {context.strip()}")

    context_block = "\n\n".join(context_lines)  # 將所有 context 用兩個換行接起來，讓 prompt 比較清楚

    return [   # 傳給 LLM 的系統指令（避免亂回答）
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

# 主要給外部呼叫的程式
def _chat_completion(messages: list[dict], temperature: float = 0.2) -> dict:   # 0.2 為保守回答
    # Call a chat-completions-compatible endpoint and return answer text plus usage metadata.
    if not LLM_API_KEY:
        raise LLMServiceError("LLM_API_KEY is not set.")

    #if not contexts:   # 沒有context直接報錯
    #    raise LLMServiceError("At least one context chunk is required.")

    try:
        response = requests.post(     # API 認證與資料格式設定
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",   # 表示送出的資料是 JSON
            },
            json={   # 送給 LLM 的主要資料（json body)
                "model": LLM_MODEL_NAME,
                "messages": messages,   # prompt messages
                "temperature": temperature,
            },
            timeout=LLM_API_TIMEOUT_SECONDS,
        )
    except RequestException as exc:   # 偵測網路層面錯誤
        raise LLMServiceError(f"LLM transport error: {exc}") from exc

    if response.status_code >= 400:   # 若 API 回傳 400、401、429、500 這類錯誤，就丟出錯誤
        raise LLMServiceError(f"LLM request failed: {response.status_code} {response.text}")

    try:   # 解析回傳的json
        payload = response.json()
    except ValueError as exc:
        raise LLMServiceError("LLM response is not valid JSON.") from exc
    choices = payload.get("choices") or []   # 取出 choices
    if not choices:
        raise LLMServiceError("LLM response did not contain choices.")

    # 取出回答內容，這裡取得第一個回答的文字內容
    message = choices[0].get("message", {})
    answer = message.get("content", "").strip()
    if not answer:
        raise LLMServiceError("LLM response content is empty.")

    return {   # result 
        "answer": answer,
        "model": payload.get("model", LLM_MODEL_NAME),
        "usage": payload.get("usage", {}),   # 可看token消耗
    }

def generate_answer(question: str, contexts: list[str], temperature: float = 0.2) -> dict:   # 0.2 為保守回答
    if not contexts:
        raise LLMServiceError("At least one context chunk is required.")
    return _chat_completion(_build_messages(question=question, contexts=contexts), temperature=temperature)


def generate_summary_from_answer(question: str, answer: str, temperature: float = 0.2) -> dict:
    if not answer or not answer.strip():
        raise LLMServiceError("Answer text is required for summary generation.")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a financial filing assistant. Rewrite the provided answer into a concise, readable, "
                "well-structured Traditional Chinese summary. Do not copy long phrases verbatim. "
                "Do not add facts not present in the provided answer."
            ),
        },
        {
            "role": "user",
            "content": (
                "Question:\n"
                f"{question.strip()}\n\n"
                "Answer to summarize:\n"
                f"{answer.strip()}\n\n"
                "Return 2-4 clear Traditional Chinese sentences."
            ),
        },
    ]

    return _chat_completion(messages=messages, temperature=temperature)
