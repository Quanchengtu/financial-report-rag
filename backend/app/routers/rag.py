from fastapi import APIRouter, HTTPException, Query
from app.services.sec_client import build_filing_urls, normalize_cik, fetch_filing_html
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text
from app.services.retriever import retrieve_relevant_chunks
from app.services.section_parser import extract_sections, get_priority_sections_for_question

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/retrieve")
def retrieve_from_filing(
    cik: str = Query(..., description="Company CIK"),
    accession_number: str = Query(..., description="SEC accession number"),
    primary_document: str = Query(..., description="Primary document file name"),
    question: str = Query(..., description="User question"),
    top_k: int = Query(3, ge=1, le=10, description="How many top chunks to return")
):
    try:
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

        results = retrieve_relevant_chunks(
            question=question,
            chunks=chunk_records,
            top_k=top_k
        )

        return {
            "cik": normalized_cik,
            "accession_number": accession_number,
            "primary_document": primary_document,
            "filing_document_url": urls["filing_document_url"],
            "question": question,
            "text_length": len(text_content),
            "section_count": len(sections),
            "used_priority_sections": priority_sections,
            "chunk_count": len(chunk_records),
            "matched_count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunks: {str(e)}")