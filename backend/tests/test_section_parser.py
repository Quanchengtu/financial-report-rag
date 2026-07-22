from app.services.section_parser import (
    extract_sections,
    get_priority_sections_for_question,
    normalize_for_section_search,
)

# test 1 : 正規化後，文字位置不能改變 (將換行、空白等字元正規化之後，字串長度仍然要與原始文字相同，避免章節切割位置跑掉)
def test_normalized_section_search_preserves_offsets_with_whitespace():
    text = "Intro\n\nItem 1. Business\nBusiness content\n\nItem 1A. Risk Factors\nRisk content"

    normalized = normalize_for_section_search(text)
    assert len(normalized) == len(text)

    sections = extract_sections(text)
    business = next(section for section in sections if section["section_name"] == "item_1_business")
    risk = next(section for section in sections if section["section_name"] == "item_1a_risk_factors")

    assert business["text"].startswith("Item 1. Business")
    assert "Business content" in business["text"]
    assert risk["text"].startswith("Item 1A. Risk Factors")
    assert "Risk content" in risk["text"]

# test 2 : 測試 "中文" 問題是否能被分配到正確章節
def test_chinese_questions_map_to_financial_priority_sections():
    assert get_priority_sections_for_question("公司的營收和毛利率如何？") == ["item_7_mda"]
    assert get_priority_sections_for_question("公司有哪些主要風險？") == ["item_1a_risk_factors"]
    assert get_priority_sections_for_question("產品和客戶有哪些？") == ["item_1_business"]

# test 3 : 財務報表數字問題是否正確導到 item 8
def test_financial_statement_questions_map_to_item_8():
    assert get_priority_sections_for_question("What was NVIDIA's total revenue?") == [
        "item_8_financial_statements"
    ]
    assert get_priority_sections_for_question("NVIDIA 的淨利是多少？") == [
        "item_8_financial_statements"
    ]
