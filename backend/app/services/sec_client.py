import os
import requests
from dotenv import load_dotenv

load_dotenv()

SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "FinancialReportRAG/1.0 (Quanchengtu; quanchengtu@gmail.com)"
)

HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}


def get_company_submissions(cik: str):
    """
    Fetch company submissions JSON from SEC.
    cik should be 10-digit zero-padded string, e.g. 0001045810 for NVDA
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def get_recent_filings(cik: str, forms=None, limit=10):
    """
    Return recent filings filtered by form type.
    forms example: ["10-K", "10-Q"]
    """
    if forms is None:
        forms = ["10-K", "10-Q"]

    data = get_company_submissions(cik)
    recent = data.get("filings", {}).get("recent", {})

    form_list = recent.get("form", [])
    accession_list = recent.get("accessionNumber", [])
    filing_date_list = recent.get("filingDate", [])
    primary_doc_list = recent.get("primaryDocument", [])
    primary_desc_list = recent.get("primaryDocDescription", [])

    results = []

    for form, accession, filing_date, primary_doc, primary_desc in zip(
        form_list,
        accession_list,
        filing_date_list,
        primary_doc_list,
        primary_desc_list
    ):
        if form in forms:
            results.append({
                "form": form,
                "filing_date": filing_date,
                "accession_number": accession,
                "primary_document": primary_doc,
                "primary_doc_description": primary_desc
            })

        if len(results) >= limit:
            break

    return results