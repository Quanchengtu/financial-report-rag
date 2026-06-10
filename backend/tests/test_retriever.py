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