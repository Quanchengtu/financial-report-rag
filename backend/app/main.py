from fastapi import FastAPI
from app.services.sec_client import get_company_submissions, get_recent_filings

app = FastAPI(title="Financial Report RAG Assistant")


@app.get("/")
def read_root():
    return {"message": "Financial Report RAG backend is running"}


@app.get("/company/{cik}")
def get_company_info(cik: str):
    data = get_company_submissions(cik)
    return {
        "name": data.get("name"),
        "tickers": data.get("tickers"),
        "sicDescription": data.get("sicDescription")
    }


@app.get("/company/{cik}/filings")
def get_company_filings(cik: str):
    filings = get_recent_filings(cik, forms=["10-K", "10-Q"], limit=10)
    return {
        "cik": cik,
        "filings": filings
    }