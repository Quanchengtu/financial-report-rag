from app.services import hybrid_retrieval


def test_hybrid_semantic_results_respect_priority_sections(monkeypatch):
    monkeypatch.setattr(
        hybrid_retrieval,
        "build_rule_based_chunk_records",
        lambda **kwargs: (
            [
                {
                    "chunk_index": 1,
                    "section_name": "item_7_mda",
                    "text": "Revenue increased due to stronger demand and improved gross margin performance.",
                }
            ],
            "https://example.com/filing.htm",
            ["item_7_mda"],
            "0000000000",
        ),
    )
    monkeypatch.setattr(hybrid_retrieval, "embed_text", lambda question: [0.1, 0.2])
    monkeypatch.setattr(hybrid_retrieval, "build_filing_where_filter", lambda **kwargs: {"cik": "0000000000"})
    monkeypatch.setattr(
        hybrid_retrieval,
        "query_similar_chunks",
        lambda **kwargs: {
            "documents": [[
                "Risk factors could adversely affect our business and financial results.",
                "Revenue increased due to stronger product demand.",
            ]],
            "metadatas": [[
                {"chunk_index": 2, "section_name": "item_1a_risk_factors"},
                {"chunk_index": 3, "section_name": "item_7_mda"},
            ]],
            "distances": [[0.01, 0.02]],
        },
    )

    result = hybrid_retrieval.hybrid_retrieve(
        cik="0",
        accession_number="0000000000-00-000000",
        primary_document="filing.htm",
        question="What happened to revenue and gross margin?",
        top_k=5,
    )

    assert result["retrieval_diagnostics"]["semantic_filtered_by_priority_count"] == 1
    assert all(item["section_name"] == "item_7_mda" for item in result["results"])
