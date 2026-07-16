import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests


# ============================================================
# 基本設定
# ============================================================

API_URL = "http://127.0.0.1:8000/rag/retrieve"

# 可更換成目前測試的 NVIDIA 財報資料
CIK = "1045810"
ACCESSION_NUMBER = "0001045810-26-000021" 
PRIMARY_DOCUMENT = "nvda-20260125.htm"

TOP_K = 3
REQUEST_TIMEOUT = 120


SECTION_ALIASES = {
    "item 1": ["item_1_business", "item 1 business", "business"],
    "item 1a": ["item_1a_risk_factors", "item 1a risk factors", "risk factors"],
    "item 7": ["item_7_mda", "item 7 mda", "management discussion", "md&a"],
    "financial statements": [
        "item_8_financial_statements",
        "item 8 financial statements",
        "financial statements",
    ],
}

KEYWORD_ALIASES = {
    "資料中心": ["data center"],
    "遊戲": ["gaming"],
    "運算與網路": ["compute & networking", "compute and networking", "compute networking"],
    "繪圖": ["graphics"],
    "業務部門": ["business segments", "segments"],
    "供應鏈": ["supply chain"],
    "製造": ["manufacturing"],
    "供應商": ["suppliers", "supplier"],
    "競爭": ["competition"],
    "競爭對手": ["competitors", "competitor"],
    "市場占有率": ["market share"],
    "營收成長": ["revenue growth", "revenue increased"],
    "需求": ["demand"],
    "營業費用": ["operating expenses"],
    "研發": ["research and development", "r&d"],
    "薪酬": ["compensation"],
    "營收": ["revenue"],
    "總營收": ["total revenue"],
    "會計年度": ["fiscal year"],
    "淨利": ["net income"],
    "盈餘": ["earnings"],
    "加速運算": ["accelerated computing"],
    "平台": ["platform"],
    "未來財務表現": ["future financial performance"],
    "市場狀況": ["market conditions"],
}

FAILURE_TYPE_DESCRIPTIONS = {
    "section_routing": "Expected section was not present in the Top K chunks.",
    "keyword_mismatch": "Expected section was present, but expected keywords or aliases were not found.",
    "chinese_retrieval_weak": "Chinese question did not retrieve equivalent English filing terminology.",
    "financial_statement_routing": "Financial-statement question was not routed to Item 8 / financial statement content.",
    "chunk_quality": "Retrieved chunk is empty, too short, or likely too noisy to answer reliably.",
}


# questions.json 和 evaluate.py 放在同一個 evaluation 資料夾
CURRENT_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = CURRENT_DIR / "questions.json"
RESULTS_DIR = CURRENT_DIR / "results"

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
# 建立 JSON report 內容
# ============================================================

def find_matched_keywords(chunks: list[dict[str, Any]], expected_keywords: Any) -> list[str]:
    """
    從 Top K chunks 文字中找出命中的 expected keywords。
    """

    if not isinstance(expected_keywords, list):
        return []

    combined_text = "\n".join(
        get_chunk_text(chunk) for chunk in chunks[:TOP_K]
    ).casefold()

    matched_keywords = []

    for keyword in expected_keywords:
        if not isinstance(keyword, str):
            continue

        keyword_variants = [keyword, *KEYWORD_ALIASES.get(keyword, [])]
        if any(variant.casefold() in combined_text for variant in keyword_variants):
            matched_keywords.append(keyword)

    return matched_keywords


def is_expected_section_found(chunks: list[dict[str, Any]], expected_section: Any) -> bool:
    """
    檢查 Top K chunks 是否包含 expected section。
    """

    if expected_section is None:
        return False

    expected_section_text = str(expected_section).casefold()
    accepted_sections = [expected_section_text, *SECTION_ALIASES.get(expected_section_text, [])]

    return any(
        any(accepted in get_chunk_section(chunk).casefold() for accepted in accepted_sections)
        for chunk in chunks[:TOP_K]
    )


def build_top_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    將 API chunks 轉成 JSON report 使用的穩定格式。
    """

    top_chunks = []

    for rank, chunk in enumerate(chunks[:TOP_K], start=1):
        top_chunks.append(
            {
                "rank": rank,
                "section": get_chunk_section(chunk),
                "score": get_chunk_score(chunk),
                "text": get_chunk_text(chunk),
            }
        )

    return top_chunks


def classify_failure_types(
    question_data: dict[str, Any],
    chunks: list[dict[str, Any]],
    matched_keywords: list[str],
    section_found: bool,
) -> list[str]:
    """Classify failed retrieval cases into actionable error categories."""

    failure_types = []
    if section_found and matched_keywords:
        return failure_types

    category = str(question_data.get("category", "")).casefold()
    language = str(question_data.get("language", "")).casefold()
    expected_section = str(question_data.get("expected_section", "")).casefold()

    if not section_found:
        failure_types.append("section_routing")

    if section_found and not matched_keywords:
        failure_types.append("keyword_mismatch")

    if language == "zh" and not matched_keywords:
        failure_types.append("chinese_retrieval_weak")

    if (
        category == "financial statements"
        or expected_section == "financial statements"
    ) and not any(
        "financial" in get_chunk_section(chunk).casefold()
        or "item_8" in get_chunk_section(chunk).casefold()
        for chunk in chunks[:TOP_K]
    ):
        failure_types.append("financial_statement_routing")

    if not chunks or any(len(get_chunk_text(chunk).strip()) < 80 for chunk in chunks[:TOP_K]):
        failure_types.append("chunk_quality")

    return list(dict.fromkeys(failure_types))

'''
def build_result_record(
    question_data: dict[str, Any],
    chunks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    建立單題 retrieval evaluation result。

    retrieval_success 代表 Top K chunks 至少命中 expected section
    或任一 expected keyword。
    """

    if chunks is None:
        chunks = []

    expected_keywords = question_data.get("expected_keywords", [])
    matched_keywords = find_matched_keywords(chunks, expected_keywords)
    section_found = is_expected_section_found(
        chunks,
        question_data.get("expected_section"),
    )

    return {
        "id": question_data.get("id"),
        "language": question_data.get("language"),
        "category": question_data.get("category"),
        "question": question_data.get("question"),
        "expected_section": question_data.get("expected_section"),
        "expected_keywords": expected_keywords,
        "retrieval_success": section_found and bool(matched_keywords),
        "matched_keywords": matched_keywords,
        "section_found": section_found,
        "failure_types": classify_failure_types(
            question_data,
            chunks,
            matched_keywords,
            section_found,
        ),
        "failure_type_descriptions": FAILURE_TYPE_DESCRIPTIONS,
        "top_chunks": build_top_chunks(chunks),
    }
'''

def build_result_record(
    question_data: dict[str, Any],
    chunks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    建立單題 retrieval evaluation result。

    retrieval_success 的判定規則：
    Top K 中至少有一個 chunk 同時符合：
    1. expected section
    2. 至少一個 expected keyword 或 alias
    """

    if chunks is None:
        chunks = []

    expected_keywords = question_data.get("expected_keywords", [])

    matched_keywords = find_matched_keywords(
        chunks,
        expected_keywords,
    )

    section_found = is_expected_section_found(
        chunks,
        question_data.get("expected_section"),
    )

    # 統一使用同一套嚴格判定邏輯
    retrieval_success = evaluate_retrieval_success(
        question_data,
        chunks,
    )

    return {
        "id": question_data.get("id"),
        "language": question_data.get("language"),
        "category": question_data.get("category"),
        "question": question_data.get("question"),
        "expected_section": question_data.get("expected_section"),
        "expected_keywords": expected_keywords,
        "retrieval_success": retrieval_success,
        "matched_keywords": matched_keywords,
        "section_found": section_found,
        "failure_types": classify_failure_types(
            question_data,
            chunks,
            matched_keywords,
            section_found,
        ),
        "failure_type_descriptions": FAILURE_TYPE_DESCRIPTIONS,
        "top_chunks": build_top_chunks(chunks),
    }


def write_results_report(results: list[dict[str, Any]]) -> Path:
    """
    將 evaluation results 寫入 timestamped JSON report。
    """

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = RESULTS_DIR / f"retrieval_eval_{timestamp}.json"

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return report_path



# ============================================================
# Retrieval scoring
# ============================================================

def normalize_text(value: Any) -> str:
    """
    將文字正規化，方便做不分大小寫與空白差異的比對。
    """

    return re.sub(r"\s+", " ", str(value).strip().lower())


def section_matches(actual_section: str, expected_section: str) -> bool:
    """
    判斷 chunk section 是否包含或近似符合 expected section。
    """

    actual = normalize_text(actual_section)
    expected = normalize_text(expected_section)

    if not actual or not expected:
        return False

    accepted_sections = [expected, *SECTION_ALIASES.get(expected, [])]

    if any(accepted in actual or actual in accepted for accepted in accepted_sections):
        return True

    return any(
        SequenceMatcher(None, actual, accepted).ratio() >= 0.8
        for accepted in accepted_sections
    )


def keyword_matches(text: str, expected_keywords: list[Any]) -> bool:
    """
    判斷 chunk text 是否包含任一 expected keyword。
    """

    normalized_text = normalize_text(text)

    for keyword in expected_keywords:
        variants = [keyword, *KEYWORD_ALIASES.get(str(keyword), [])]
        if any(normalize_text(variant) in normalized_text for variant in variants):
            return True

    return False


def evaluate_retrieval_success(
    question_data: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> bool:
    """
    評估 Top K chunks 是否命中預期 section，且包含任一預期 keyword。

    PASS 條件：
    Top K 中至少有一個 chunk 同時符合 expected section，
    並包含至少一個 expected keyword 或 alias。
    """

    expected_section = question_data.get("expected_section")
    expected_keywords = question_data.get("expected_keywords", [])

    if isinstance(expected_keywords, str):
        expected_keywords = [expected_keywords]

    if not isinstance(expected_section, str) or not isinstance(expected_keywords, list):
        return False

    for chunk in chunks[:TOP_K]:
        chunk_section = get_chunk_section(chunk)
        chunk_text = get_chunk_text(chunk)

        section_matched = section_matches(
            chunk_section,
            expected_section,
        )

        keyword_matched = keyword_matches(
            chunk_text,
            expected_keywords,
        )

        if section_matched and keyword_matched:
            return True
        
    return False


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


def print_retrieval_success(success: bool, failure_types: list[str] | None = None) -> None:
    """
    印出單題 retrieval scoring 結果。
    """

    status = "PASS" if success else "FAIL"
    print(f"\nRetrieval Success: {status}")

    if not success and failure_types:
        print(f"Failure Types    : {', '.join(failure_types)}")


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
    Retrieval evaluation：

    1. 讀取 questions.json
    2. 逐題呼叫 Retrieval API
    3. 印出 Top 3 retrieval chunks
    4. 根據 expected section 與 expected keywords 印出 retrieval success
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
    results = []

    for question_data in questions:
        question = question_data.get("question")

        print_question_header(question_data)

        if not isinstance(question, str) or not question.strip():
            print("Skipped: question 欄位不存在或內容為空。")
            results.append(build_result_record(question_data))
            failed_requests += 1
            continue

        try:
            result = call_retrieval_api(question)
            chunks = extract_chunks(result)

            print_chunks(chunks)
            
            result_record = build_result_record(question_data, chunks)
            results.append(result_record)
            success = result_record["retrieval_success"]

            print_retrieval_success(
                success,
                result_record["failure_types"],
            )

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
            results.append(build_result_record(question_data))
            failed_requests += 1

        except requests.exceptions.Timeout:
            print(
                f"\nRequest failed: API 超過 {REQUEST_TIMEOUT} 秒沒有回應。"
            )
            results.append(build_result_record(question_data))
            failed_requests += 1

        except requests.exceptions.HTTPError as error:
            print(f"\nRequest failed: HTTP error: {error}")

            if error.response is not None:
                print("API response:")
                print(error.response.text)

            results.append(build_result_record(question_data))
            failed_requests += 1

        except requests.exceptions.RequestException as error:
            print(f"\nRequest failed: {error}")
            results.append(build_result_record(question_data))
            failed_requests += 1

        except (ValueError, TypeError, KeyError) as error:
            print(f"\nFailed to process API response: {error}")
            results.append(build_result_record(question_data))
            failed_requests += 1

    report_path = write_results_report(results)

    print("\n")
    print("=" * 90)
    print("Retrieval Evaluation Finished")
    print(f"Total questions     : {len(questions)}")
    print(f"Successful requests : {successful_requests}")
    print(f"Failed requests     : {failed_requests}")
    print(f"JSON report         : {report_path}")
    print("=" * 90)


if __name__ == "__main__":
    main()