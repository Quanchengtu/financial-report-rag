import pytest

from app.services.langchain_query_service import parse_query_rewrite_json
from app.services.llm_service import LLMServiceError


def test_parse_query_rewrite_json_normalizes_valid_payload():
    result = parse_query_rewrite_json(
        '{"original_question":"公司的營收如何？","rewritten_query":"revenue net sales fiscal year","intent":"financial_metric"}',
        original_question="公司的營收如何？",
    )

    assert result == {
        "mode": "langchain_query_rewrite_v1",
        "original_question": "公司的營收如何？",
        "rewritten_query": "revenue net sales fiscal year",
        "intent": "financial_metric",
    }


def test_parse_query_rewrite_json_requires_valid_json():
    with pytest.raises(LLMServiceError, match="not valid JSON"):
        parse_query_rewrite_json("not json", original_question="What changed revenue?")


def test_parse_query_rewrite_json_requires_rewritten_query():
    with pytest.raises(LLMServiceError, match="rewritten_query"):
        parse_query_rewrite_json(
            '{"original_question":"What changed revenue?","intent":"financial_metric"}',
            original_question="What changed revenue?",
        )
