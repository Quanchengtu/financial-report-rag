import importlib
import sys
import types


def import_answer_service_with_stubs():
    config = types.ModuleType("app.core.config")
    config.RAG_LLM_MAX_CHARS_PER_CHUNK = 4000
    config.RAG_LLM_MAX_CONTEXT_CHUNKS = 4
    sys.modules["app.core.config"] = config

    llm_service = types.ModuleType("app.services.llm_service")

    class LLMServiceError(Exception):
        pass

    llm_service.LLMServiceError = LLMServiceError
    llm_service.generate_answer = lambda *args, **kwargs: {"answer": ""}
    llm_service.generate_summary_from_answer = lambda *args, **kwargs: {"answer": ""}
    sys.modules["app.services.llm_service"] = llm_service

    embedding_service = types.ModuleType("app.services.embedding_service")
    embedding_service.embed_text = lambda text: [1.0, 0.0]
    sys.modules["app.services.embedding_service"] = embedding_service

    sys.modules.pop("app.services.answer_service", None)
    return importlib.import_module("app.services.answer_service")


def test_financial_metric_question_preserves_digit_heavy_revenue_evidence():
    answer_service = import_answer_service_with_stubs()
    sentence = "Revenue $1,234 5,678 9,012"

    assert answer_service.is_noisy_sentence(sentence, question="What was revenue?") is False


def test_digit_heavy_non_financial_sentence_is_still_filtered():
    answer_service = import_answer_service_with_stubs()
    sentence = "Page 12345 67890 12345 67890 12345 67890"

    assert answer_service.is_noisy_sentence(sentence, question="What are the risk factors?") is True


def test_financial_value_without_metric_is_still_filtered():
    answer_service = import_answer_service_with_stubs()
    sentence = "$1,234 $5,678 $9,012 2023 2024"

    assert answer_service.is_noisy_sentence(sentence, question="What was revenue?") is True