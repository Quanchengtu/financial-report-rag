import re


SECTION_PATTERNS = [
    ("item_1a_risk_factors", r"\bitem\s+1a\.?\s+risk\s+factors\b"),   # \b 單字邊界 \s+ 0個或多個空格
    ("item_1_business", r"\bitem\s+1\.?\s+business\b"),
    ("item_2_properties", r"\bitem\s+2\.?\s+properties\b"),
    ("item_3_legal_proceedings", r"\bitem\s+3\.?\s+legal\s+proceedings\b"),
    ("item_7_mda", r"\bitem\s+7\.?\s+management[’'`s\s]+discussion\s+and\s+analysis\b"),
    ("item_7a_market_risk", r"\bitem\s+7a\.?\s+quantitative\s+and\s+qualitative\s+disclosures\s+about\s+market\s+risk\b"),
    ("item_8_financial_statements", r"\bitem\s+8\.?\s+financial\s+statements\s+and\s+supplementary\s+data\b"),
]

SECTION_QUERY_KEYWORDS = {
    "item_1a_risk_factors": [
        "risk factors", "risk factor", "key risks", "major risks",
        "風險因素", "主要風險", "重大風險", "有哪些風險", "風險",
    ],
    "item_7a_market_risk": [
        "market risk", "interest rate", "foreign exchange", "fx", "commodity",
        "市場風險", "利率", "匯率", "外匯", "商品價格",
    ],
    "item_8_financial_statements": [
        "total revenue", "net income", "earnings", "consolidated statements",
        "statements of income", "financial statements", "總營收", "淨利",
        "淨收入", "盈餘", "財務報表",
    ],
    "item_7_mda": [
        "management discussion", "results of operations", "mda", "md&a",
        "revenue growth", "gross margin", "operating expenses", "cash flow", "liquidity",
        "capital expenditure", "capex", "future financial performance",
        "營收成長", "收入成長", "毛利", "毛利率", "營業費用",
        "營運", "經營結果", "現金流", "流動性", "資本支出", "財務表現",
        "未來財務表現",
    ],
    "item_1_business": [
        "business", "product", "service", "customer", "business model",
        "業務", "商業模式", "產品", "服務", "客戶",
    ],
    "item_3_legal_proceedings": [
        "legal proceedings", "litigation", "lawsuit", "regulatory", "compliance",
        "法律程序", "訴訟", "官司", "監管", "法規", "合規",
    ],
}


def normalize_for_section_search(text: str) -> str:
    """
    給 section 標題搜尋用的簡化版本。

    Keep the returned string the same length as the original text so regex match
    offsets can safely be used to slice the original filing text.  Collapsing
    whitespace here would make every offset after the first newline/tab drift and
    cause chunks to be assigned to the wrong SEC item.
    """
    lowered = text.lower().replace("’", "'").replace("`", "'")
    return re.sub(r"\s", " ", lowered)


def find_section_boundaries(text: str) -> list[dict]:
    """
    找出文件中已知章節標題的大致開始與結束位置
    回傳:
    [
      {"section_name": "...", "start": 1000, "end": 2500},
      ...
    ]
    """
    normalized = normalize_for_section_search(text)   # 將文字轉成較容易搜尋的格式
    matches = []   # 存找到的章節標題位置

    for section_name, pattern in SECTION_PATTERNS:
        for match in re.finditer(pattern, normalized):  # 在 normalized 這段文字裡面，用 pattern 這個 regex 規則去找"所有"符合的地方
            matches.append({
                "section_name": section_name,
                "start": match.start()
            })

    if not matches:
        return []

    # 依start位置重新排序
    matches.sort(key=lambda x: x["start"])

    sections = []   # 可存section首尾位置（章節範圍）
    for i, match in enumerate(matches):   # 決定每個 section 的 start 和 end
        start = match["start"]
        end = matches[i + 1]["start"] if i + 1 < len(matches) else len(text)  # 一個章節的結束位置，就是下一個章節標題出現的位置

        sections.append({
            "section_name": match["section_name"],
            "start": start,
            "end": end
        })

    return sections


def extract_sections(text: str) -> list[dict]:
    """
    從 cleaned text 中切出已知章節
    回傳:
    [
      {
        "section_name": "item_1a_risk_factors",
        "text": "..."
      }
    ]
    """
    boundaries = find_section_boundaries(text)
    if not boundaries:
        return []

    sections = []   # 對比line 50 這裡存真正切出來的章節文字
    for item in boundaries:
        section_text = text[item["start"]:item["end"]].strip()
        if section_text:
            sections.append({
                "section_name": item["section_name"],
                "text": section_text
            })

    return sections


def _contains_any(text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        if keyword == "利率":
            # Avoid treating 毛利率 (gross margin) as 利率 (interest rate).
            if re.search(r"(?<!毛)利率", text):
                return True
            continue
        if keyword in text:
            return True
    return False


def get_priority_sections_for_question(question: str) -> list[str]:
    """
    根據問題內容，回傳優先搜尋的章節名稱。

    Route common filing topics to their most relevant SEC sections. Chinese
    aliases are included for the bilingual UI, but the routing itself applies to
    both English and Chinese questions so broad retrieval does not over-select
    Item 1A for non-risk topics.
    """
    q = question.lower()

    priorities = []
    for section_name, keywords in SECTION_QUERY_KEYWORDS.items():
        if _contains_any(q, keywords):
            priorities.append(section_name)

    # 去重且保序
    return list(dict.fromkeys(priorities))
