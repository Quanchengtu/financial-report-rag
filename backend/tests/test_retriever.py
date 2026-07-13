from app.services.retriever import is_noisy_chunk, retrieve_relevant_chunks


def test_noisy_chunk_filters_unresolved_staff_comments_heading():
    text = "Unresolved Staff Comments " + "placeholder disclosure text " * 20

    assert is_noisy_chunk(text) is True


def test_retrieve_relevant_chunks_ignores_unresolved_staff_comments_heading():
    noisy_chunk = {
        "chunk_index": 0,
        "section_name": "item_1b_unresolved_staff_comments",
        "text": "Unresolved Staff Comments " + "risk factors market competition disclosure " * 20,
    }
    relevant_chunk = {
        "chunk_index": 1,
        "section_name": "item_1a_risk_factors",
        "text": "Risk factors include intense market competition and possible supply chain disruption. " * 3,
    }

    results = retrieve_relevant_chunks(
        question="What are the risk factors from market competition?",
        chunks=[noisy_chunk, relevant_chunk],
        top_k=2,
    )

    assert [result["chunk_index"] for result in results] == [1]


def test_chinese_financial_terms_expand_to_english_tokens():
    results = retrieve_relevant_chunks(
        question="公司的營收和毛利率如何？",
        chunks=[
            {
                "chunk_index": 0,
                "section_name": "item_1a_risk_factors",
                "text": "Risk factors may affect our suppliers, competition, and business results in many ways.",
            },
            {
                "chunk_index": 1,
                "section_name": "item_7_mda",
                "text": "Revenue increased due to product demand, while gross margin changed because of costs and mix.",
            },
        ],
        top_k=1,
    )

    assert results
    assert results[0]["section_name"] == "item_7_mda"
    assert "revenue" in results[0]["matched_terms"]


def test_chinese_expected_terms_expand_for_financial_statement_questions():
    results = retrieve_relevant_chunks(
        question="NVIDIA 的淨利是多少？",
        chunks=[
            {
                "chunk_index": 0,
                "section_name": "item_8_financial_statements",
                "text": "Consolidated Statements of Income show net income and earnings for the fiscal year. " * 3,
            }
        ],
        top_k=1,
    )

    assert results
    assert results[0]["section_name"] == "item_8_financial_statements"
    assert "income" in results[0]["matched_terms"]
