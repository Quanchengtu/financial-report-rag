from fastapi import APIRouter, HTTPException, Query
from app.services.sec_client import build_filing_urls, normalize_cik, fetch_filing_html

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

        html_content = fetch_filing_html(urls["filing_document_url"])

        return {
            "cik": normalized_cik,
            "accession_number": accession_number,
            "primary_document": primary_document,
            "filing_document_url": urls["filing_document_url"],
            "html_length": len(html_content),
            "html_preview": html_content[:2000]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch filing HTML: {str(e)}")