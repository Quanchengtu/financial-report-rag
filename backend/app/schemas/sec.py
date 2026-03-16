from pydantic import BaseModel
from typing import List


class CompanyInfoResponse(BaseModel):
    cik: str
    name: str | None = None
    tickers: list[str] = []
    sic_description: str | None = None


class FilingItem(BaseModel):
    form: str
    filing_date: str
    accession_number: str
    primary_document: str
    filing_detail_url: str
    filing_document_url: str


class CompanyFilingsResponse(BaseModel):
    cik: str
    filings: List[FilingItem]