from fastapi import APIRouter, HTTPException, Query
from app.services.sec_client import build_filing_urls, normalize_cik, fetch_filing_html
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text
from app.services.retriever import retrieve_relevant_chunks

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/retrieve")
def retrieve_from_filing(
    cik: str = Query(..., description="Company CIK"),
    accession_number: str = Query(..., description="SEC accession number"),
    primary_document: str = Query(..., description="Primary document file name"),
    question: str = Query(..., description="User question"),
    top_k: int = Query(3, description="How many top chunks to return")
):
    try:
        normalized_cik = normalize_cik(cik)

        urls = build_filing_urls(
            cik=normalized_cik,
            accession_number=accession_number,
            primary_document=primary_document
        )

        # 1. 抓原始 HTML
        html_content = fetch_filing_html(urls["filing_document_url"])

        # 2. 清洗成純文字
        text_content = extract_text_from_html(html_content)

        # 3. 切 chunks
        chunks = chunk_text(text_content, chunk_size=800, overlap=100)

        # 4. 做 retrieval
        results = retrieve_relevant_chunks(
            question=question,
            chunks=chunks,
            top_k=top_k
        )

        return {
            "cik": normalized_cik,
            "accession_number": accession_number,
            "primary_document": primary_document,
            "filing_document_url": urls["filing_document_url"],
            "question": question,
            "chunk_count": len(chunks),
            "matched_count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunks: {str(e)}")