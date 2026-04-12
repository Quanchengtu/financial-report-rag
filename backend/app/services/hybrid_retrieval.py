from app.services.retriever import retrieve_relevant_chunks
from app.services.embedding_service import embed_text
from app.services.vector_store import query_similar_chunks
from app.services.sec_client import build_filing_urls, normalize_cik, fetch_filing_html
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text
from app.services.section_parser import extract_sections, get_priority_sections_for_question


def build_rule_based_chunk_records(
    cik: str,
    accession_number: str,
    primary_document: str,
    question: str,
) -> tuple[list[dict], str, list[str], str]:
    normalized_cik = normalize_cik(cik)

    urls = build_filing_urls(
        cik=normalized_cik,
        accession_number=accession_number,
        primary_document=primary_document
    )

    html_content = fetch_filing_html(urls["filing_document_url"])
    text_content = extract_text_from_html(html_content)

    sections = extract_sections(text_content)
    priority_sections = get_priority_sections_for_question(question)

    selected_sections = []
    if priority_sections and sections:
        selected_sections = [
            section for section in sections
            if section["section_name"] in priority_sections
        ]

    chunk_records = []
    chunk_index = 0

    if selected_sections:
        for section in selected_sections:
            section_chunks = chunk_text(
                section["text"],
                chunk_size=800,
                overlap=100
            )

            for chunk in section_chunks:
                chunk_records.append({
                    "chunk_index": chunk_index,
                    "section_name": section["section_name"],
                    "text": chunk
                })
                chunk_index += 1
    else:
        full_chunks = chunk_text(text_content, chunk_size=800, overlap=100)
        for chunk in full_chunks:
            chunk_records.append({
                "chunk_index": chunk_index,
                "section_name": None,
                "text": chunk
            })
            chunk_index += 1

    return chunk_records, urls["filing_document_url"], priority_sections, normalized_cik


def hybrid_retrieve(
    cik: str,
    accession_number: str,
    primary_document: str,
    question: str,
    top_k: int = 5
) -> dict:
    chunk_records, filing_document_url, priority_sections, normalized_cik = build_rule_based_chunk_records(
        cik=cik,
        accession_number=accession_number,
        primary_document=primary_document,
        question=question
    )

    rule_results = retrieve_relevant_chunks(
        question=question,
        chunks=chunk_records,
        top_k=top_k
    )

    semantic_results = []
    try:
        query_embedding = embed_text(question)

        vector_results = query_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            where={
                "cik": normalized_cik,
                "accession_number": accession_number,
                "primary_document": primary_document
            }
        )

        docs = vector_results.get("documents", [[]])[0]
        metadatas = vector_results.get("metadatas", [[]])[0]
        distances = vector_results.get("distances", [[]])[0]

        for doc, metadata, distance in zip(docs, metadatas, distances):
            semantic_results.append({
                "chunk_index": metadata.get("chunk_index"),
                "section_name": metadata.get("section_name"),
                "score": 100 - int(distance * 100) if distance is not None else 0,
                "matched_terms": ["semantic_match"],
                "text": doc
            })
    except Exception:
        semantic_results = []

    merged = []
    seen_texts = set()

    for item in rule_results + semantic_results:
        text_key = item.get("text", "").strip().lower()
        if not text_key or text_key in seen_texts:
            continue
        seen_texts.add(text_key)
        merged.append(item)

    merged.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "cik": normalized_cik,
        "filing_document_url": filing_document_url,
        "used_priority_sections": priority_sections,
        "results": merged[:top_k]
    }