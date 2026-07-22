from evaluation.chunking_basic_eval import compare_chunking_settings, evaluate_chunking


def test_evaluate_chunking_returns_basic_metrics():
    text = (
        "Revenue increased because product demand improved. " * 10
        + "Operating cash flow remained positive. " * 10
    )

    result = evaluate_chunking(text, chunk_size=120, overlap=20)

    assert result.chunk_size == 120
    assert result.overlap == 20
    assert result.chunk_count > 1
    assert 0 < result.average_chunk_length <= 120
    assert result.max_chunk_length <= 120
    assert 0 < result.size_utilization <= 1
    assert 0 <= result.repeated_character_ratio <= 1
    assert 0 <= result.sentence_boundary_ratio <= 1


def test_compare_chunking_settings_uses_default_candidates():
    text = "Risk factors may affect revenue. " * 80

    results = compare_chunking_settings(text)

    assert [(result.chunk_size, result.overlap) for result in results] == [
        (500, 50),
        (800, 100),
        (1200, 150),
    ]