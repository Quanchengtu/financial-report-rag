import re


SECTION_PATTERNS = [
    ("item_1a_risk_factors", r"\bitem\s+1a\.?\s+risk\s+factors\b"),   # \b 單字邊界 \s+ 0個或多個空格
    ("item_1_business", r"\bitem\s+1\.?\s+business\b"),
    ("item_2_properties", r"\bitem\s+2\.?\s+properties\b"),
    ("item_3_legal_proceedings", r"\bitem\s+3\.?\s+legal\s+proceedings\b"),
    ("item_7_mda", r"\bitem\s+7\.?\s+management[’'`s\s]+discussion\s+and\s+analysis\b"),
    ("item_7a_market_risk", r"\bitem\s+7a\.?\s+quantitative\s+and\s+qualitative\s+disclosures\s+about\s+market\s+risk\b"),
]


def normalize_for_section_search(text: str) -> str:
    """
    給 section 標題搜尋用的簡化版本   
    """
    lowered = text.lower()
    lowered = lowered.replace("’", "'")
    lowered = re.sub(r"\s+", " ", lowered)   # 多空格壓成一個空格
    return lowered


def find_section_boundaries(text: str) -> list[dict]:
    """
    找出文件中已知章節標題的大致開始與結束位置
    回傳:
    [
      {"section_name": "...", "start": 1000, "end": 2500},
      ...
    ]
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


def get_priority_sections_for_question(question: str) -> list[str]:
    """
    根據問題內容，回傳優先搜尋的章節名稱
    """
    q = question.lower()

    priorities = []

    if "risk factors" in q or "risk factor" in q:
        priorities.append("item_1a_risk_factors")

    if "market risk" in q:
        priorities.append("item_7a_market_risk")

    if "management discussion" in q or "results of operations" in q:
        priorities.append("item_7_mda")

    if "business" in q:
        priorities.append("item_1_business")

    if "legal proceedings" in q:
        priorities.append("item_3_legal_proceedings")

    return priorities