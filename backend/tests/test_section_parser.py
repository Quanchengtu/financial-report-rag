from app.services.section_parser import (
    extract_sections,
    get_priority_sections_for_question,
    normalize_for_section_search,
)


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


def test_chinese_questions_map_to_financial_priority_sections():
    assert get_priority_sections_for_question("公司的營收和毛利率如何？") == ["item_7_mda"]
    assert get_priority_sections_for_question("公司有哪些主要風險？") == ["item_1a_risk_factors"]
    assert get_priority_sections_for_question("產品和客戶有哪些？") == ["item_1_business"]
