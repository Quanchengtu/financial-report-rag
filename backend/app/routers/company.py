from fastapi import APIRouter, HTTPException
from app.schemas.sec import CompanyInfoResponse, CompanyFilingsResponse
from app.services.sec_client import (
    get_company_submissions,
    get_recent_filings,
    normalize_cik
)

router = APIRouter(prefix="/company", tags=["Company"])


@router.get("/{cik}", response_model=CompanyInfoResponse)
def get_company_info(cik: str):
    try:
        data = get_company_submissions(cik)
        return {
            "cik": normalize_cik(cik),
            "name": data.get("name"),
            "tickers": data.get("tickers", []),
            "sic_description": data.get("sicDescription")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch company info: {str(e)}")


@router.get("/{cik}/filings", response_model=CompanyFilingsResponse)
def get_company_filings(cik: str):
    try:
        filings = get_recent_filings(cik, forms=["10-K", "10-Q"], limit=10)
        return {
            "cik": normalize_cik(cik),
            "filings": filings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch company filings: {str(e)}")