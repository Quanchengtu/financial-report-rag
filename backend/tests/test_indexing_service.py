import importlib
import sys
import types


def import_indexing_service_with_stubs(existing_count=0):
    sec_client = types.ModuleType("app.services.sec_client")
    sec_client.normalize_cik = lambda cik: cik.zfill(10)
    sec_client.build_filing_urls = lambda **kwargs: {"filing_document_url": "https://example.test/filing.htm"}
    sec_client.fetch_filing_html = lambda url: "<html>Risk factors include competition.</html>"
    sys.modules["app.services.sec_client"] = sec_client

    html_parser = types.ModuleType("app.services.html_parser")
    html_parser.extract_text_from_html = lambda html: "Risk factors include competition and supply constraints. " * 40
    sys.modules["app.services.html_parser"] = html_parser

    text_chunker = types.ModuleType("app.services.text_chunker")
    text_chunker.chunk_text = lambda text, chunk_size=800, overlap=100: [text[:200]]
    sys.modules["app.services.text_chunker"] = text_chunker

    section_parser = types.ModuleType("app.services.section_parser")
    section_parser.extract_sections = lambda text: [{"section_name": "item_1a_risk_factors", "text": text}]
    sys.modules["app.services.section_parser"] = section_parser

    embedding_service = types.ModuleType("app.services.embedding_service")
    embedding_service.embed_texts = lambda texts: [[1.0, 0.0] for _ in texts]
    sys.modules["app.services.embedding_service"] = embedding_service

    vector_store = types.ModuleType("app.services.vector_store")
    vector_store.count_chunks_for_filing = lambda **kwargs: existing_count
    vector_store.upserted = []
    vector_store.upsert_chunks = lambda **kwargs: vector_store.upserted.append(kwargs)
    sys.modules["app.services.vector_store"] = vector_store

    sys.modules.pop("app.services.indexing_service", None)
    return importlib.import_module("app.services.indexing_service"), vector_store


def test_ensure_filing_indexed_skips_existing_chunks():
    indexing_service, vector_store = import_indexing_service_with_stubs(existing_count=7)

    status = indexing_service.ensure_filing_indexed(
        cik="1045810",
        accession_number="0001045810-26-000052",
        primary_document="nvda-20260426.htm",
    )

    assert status["was_indexed_before"] is True
    assert status["indexed_now"] is False
    assert status["chunk_count"] == 7
    assert vector_store.upserted == []


def test_ensure_filing_indexed_indexes_missing_filing():
    indexing_service, vector_store = import_indexing_service_with_stubs(existing_count=0)

    status = indexing_service.ensure_filing_indexed(
        cik="1045810",
        accession_number="0001045810-26-000052",
        primary_document="nvda-20260426.htm",
        company_ticker="NVDA",
        form_type="10-Q",
        filing_date="2026-04-26",
    )

    assert status["was_indexed_before"] is False
    assert status["indexed_now"] is True
    assert status["chunk_count"] == 1
    assert len(vector_store.upserted) == 1
