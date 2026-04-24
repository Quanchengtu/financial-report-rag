from fastapi import APIRouter, HTTPException, Query
from app.services.sec_client import build_filing_urls, normalize_cik, fetch_filing_html
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text

router = APIRouter(prefix="/filing", tags=["Filing"])


@router.get("/html")
def get_filing_html(
    cik: str = Query(..., description="Company CIK"),
    accession_number: str = Query(..., description="SEC accession number"),
    primary_document: str = Query(..., description="Primary document file name")
):
    try:
        normalized_cik = normalize_cik(cik)

        urls = build_filing_urls(
            cik=normalized_cik,
            accession_number=accession_number,
            primary_document=primary_document
        )

        html_content = fetch_filing_html(urls["filing_document_url"]) # url是dict型態
        text_content = extract_text_from_html(html_content)
        chunks = chunk_text(text_content, chunk_size=800, overlap=100)

        return {
            "cik": normalized_cik,
            "accession_number": accession_number,
            "primary_document": primary_document,
            "filing_document_url": urls["filing_document_url"],
            "html_length": len(html_content),
            "text_length": len(text_content),
            "chunk_count": len(chunks),
            "html_preview": html_content[:1000],  # 前1000字HTML預覽
            "text_preview": text_content[:2000],
            "chunk_preview": chunks[:3]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch filing HTML: {str(e)}")