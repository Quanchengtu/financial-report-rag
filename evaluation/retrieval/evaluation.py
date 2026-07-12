import json
from pathlib import Path
from typing import Any

import requests


# ============================================================
# 基本設定
# ============================================================

API_URL = "http://127.0.0.1:8000/rag/retrieve"

# 請換成你目前測試的 NVIDIA 財報資料
CIK = "1045810"
ACCESSION_NUMBER = "請填入 accession number"
PRIMARY_DOCUMENT = "請填入 primary document"

TOP_K = 3
REQUEST_TIMEOUT = 120


# questions.json 和 evaluate.py 放在同一個 evaluation 資料夾
CURRENT_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = CURRENT_DIR / "questions.json"


# ============================================================
# 讀取測試問題
# ============================================================

def load_questions(file_path: Path) -> list[dict[str, Any]]:
    """
    從 questions.json 讀取 retrieval evaluation 測試問題。
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"找不到 questions.json：{file_path}\n"
            "請確認 evaluate.py 和 questions.json 位於同一個資料夾。"
        )

    with file_path.open("r", encoding="utf-8") as file:
        questions = json.load(file)

    if not isinstance(questions, list):
        raise ValueError("questions.json 最外層必須是一個 JSON array。")

    return questions


# ============================================================
# 呼叫 Retrieval API
# ============================================================

def call_retrieval_api(question: str) -> dict[str, Any]:
    """
    呼叫專案目前的 GET /rag/retrieve API。
    """

    params = {
        "cik": CIK,
        "accession_number": ACCESSION_NUMBER,
        "primary_document": PRIMARY_DOCUMENT,
        "question": question,
        "top_k": TOP_K,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    # 如果 API 回傳 4xx 或 5xx，會在這裡拋出錯誤
    response.raise_for_status()

    return response.json()


# ============================================================
# 從 API response 找出 retrieval chunks
# ============================================================

def extract_chunks(result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    從 API response 中取得 retrieval chunks。

    因為不同版本的 API 可能使用不同欄位名稱，
    這裡依序嘗試幾種常見名稱。
    """

    possible_keys = [
        "retrieved_chunks",
        "chunks",
        "results",
        "evidence",
        "retrieval_results",
        "documents",
    ]

    for key in possible_keys:
        value = result.get(key)

        if isinstance(value, list):
            return value

    # 有些 API 可能把結果包在 data 裡
    data = result.get("data")

    if isinstance(data, dict):
        for key in possible_keys:
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


# ============================================================
# 取得 chunk 欄位
# ============================================================

def get_chunk_text(chunk: dict[str, Any]) -> str:
    """
    嘗試從 chunk 中取得文字內容。
    """

    possible_keys = [
        "text",
        "content",
        "chunk_text",
        "document",
        "page_content",
    ]

    for key in possible_keys:
        value = chunk.get(key)

        if isinstance(value, str):
            return value

    return "找不到 chunk 文字欄位"


def get_chunk_section(chunk: dict[str, Any]) -> str:
    """
    嘗試從 chunk 中取得 section 名稱。
    """

    possible_keys = [
        "section",
        "section_name",
        "item",
        "source_section",
    ]

    for key in possible_keys:
        value = chunk.get(key)

        if value is not None:
            return str(value)

    metadata = chunk.get("metadata")

    if isinstance(metadata, dict):
        for key in possible_keys:
            value = metadata.get(key)

            if value is not None:
                return str(value)

    return "Unknown"


def get_chunk_score(chunk: dict[str, Any]) -> str:
    """
    嘗試從 chunk 中取得 retrieval score。
    第一版只顯示，不使用它計算評估分數。
    """

    possible_keys = [
        "score",
        "similarity_score",
        "relevance_score",
        "bm25_score",
        "distance",
    ]

    for key in possible_keys:
        value = chunk.get(key)

        if value is not None:
            if isinstance(value, float):
                return f"{value:.4f}"

            return str(value)

    return "N/A"


# ============================================================
# 印出單一問題的結果
# ============================================================

def print_question_header(question_data: dict[str, Any]) -> None:
    """
    印出問題基本資訊。
    """

    print("\n")
    print("=" * 90)
    print(f"Question ID       : {question_data.get('id', 'N/A')}")
    print(f"Language          : {question_data.get('language', 'N/A')}")
    print(f"Category          : {question_data.get('category', 'N/A')}")
    print(f"Expected Section  : {question_data.get('expected_section', 'N/A')}")
    print(f"Expected Keywords : {question_data.get('expected_keywords', [])}")
    print(f"Question          : {question_data.get('question', '')}")
    print("=" * 90)


def print_chunks(chunks: list[dict[str, Any]]) -> None:
    """
    印出 Top K retrieval chunks。
    """

    if not chunks:
        print("\nNo retrieval chunks found.")
        return

    for rank, chunk in enumerate(chunks[:TOP_K], start=1):
        section = get_chunk_section(chunk)
        score = get_chunk_score(chunk)
        text = get_chunk_text(chunk)

        print(f"\nTop {rank}")
        print("-" * 90)
        print(f"Section : {section}")
        print(f"Score   : {score}")
        print("Text:")
        print(text)
        print("-" * 90)


# ============================================================
# 執行 Evaluation
# ============================================================

def main() -> None:
    """
    第一版 retrieval evaluation：

    1. 讀取 questions.json
    2. 逐題呼叫 Retrieval API
    3. 印出 Top 3 retrieval chunks
    4. 不進行自動評分
    """

    print("Loading evaluation questions...")

    try:
        questions = load_questions(QUESTIONS_FILE)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
        print(f"Failed to load questions: {error}")
        return

    print(f"Loaded {len(questions)} questions.")
    print(f"Retrieval API: {API_URL}")
    print(f"Top K: {TOP_K}")

    successful_requests = 0
    failed_requests = 0

    for question_data in questions:
        question = question_data.get("question")

        print_question_header(question_data)

        if not isinstance(question, str) or not question.strip():
            print("Skipped: question 欄位不存在或內容為空。")
            failed_requests += 1
            continue

        try:
            result = call_retrieval_api(question)
            chunks = extract_chunks(result)

            print_chunks(chunks)

            # 暫時保留 raw response 檢查功能。
            # 如果 chunks 一直抓不到，可以把下面這幾行取消註解。
            #
            # print("\nRaw API response:")
            # print(json.dumps(result, ensure_ascii=False, indent=2))

            successful_requests += 1

        except requests.exceptions.ConnectionError:
            print(
                "\nRequest failed: 無法連線到 Retrieval API。\n"
                "請確認 FastAPI 已經在 http://127.0.0.1:8000 執行。"
            )
            failed_requests += 1

        except requests.exceptions.Timeout:
            print(
                f"\nRequest failed: API 超過 {REQUEST_TIMEOUT} 秒沒有回應。"
            )
            failed_requests += 1

        except requests.exceptions.HTTPError as error:
            print(f"\nRequest failed: HTTP error: {error}")

            if error.response is not None:
                print("API response:")
                print(error.response.text)

            failed_requests += 1

        except requests.exceptions.RequestException as error:
            print(f"\nRequest failed: {error}")
            failed_requests += 1

        except (ValueError, TypeError, KeyError) as error:
            print(f"\nFailed to process API response: {error}")
            failed_requests += 1

    print("\n")
    print("=" * 90)
    print("Retrieval Evaluation Finished")
    print(f"Total questions     : {len(questions)}")
    print(f"Successful requests : {successful_requests}")
    print(f"Failed requests     : {failed_requests}")
    print("=" * 90)


if __name__ == "__main__":
    main()