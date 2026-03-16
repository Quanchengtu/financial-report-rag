import requests
from app.core.config import SEC_USER_AGENT

BASE_SUBMISSIONS_URL = "https://data.sec.gov/submissions"
BASE_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}


def normalize_cik(cik: str) -> str:
    """
    將 CIK 補成 SEC 需要的 10 位數格式
    例如: 320193 -> 0000320193
    """
    return str(cik).zfill(10)


def get_company_submissions(cik: str) -> dict:
    """
    從 SEC 取得公司 submissions 資料
    """
    cik = normalize_cik(cik)
    url = f"{BASE_SUBMISSIONS_URL}/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def build_filing_urls(cik: str, accession_number: str, primary_document: str) -> dict:
    """
    組出 filing detail 頁面 URL 與文件 URL
    """
    cik_no_zero = str(int(cik))
    accession_no_dash = accession_number.replace("-", "")

    filing_detail_url = (
        f"{BASE_ARCHIVES_URL}/{cik_no_zero}/{accession_no_dash}/{accession_number}-index.htm"
    )

    filing_document_url = (
        f"{BASE_ARCHIVES_URL}/{cik_no_zero}/{accession_no_dash}/{primary_document}"
    )

    return {
        "filing_detail_url": filing_detail_url,
        "filing_document_url": filing_document_url
    }


def get_recent_filings(cik: str, forms=None, limit: int = 10) -> list:
    """
    取得最近的指定 filings，預設抓 10-K / 10-Q
    """
    if forms is None:
        forms = ["10-K", "10-Q"]

    normalized_cik = normalize_cik(cik)
    data = get_company_submissions(normalized_cik)
    recent = data.get("filings", {}).get("recent", {})

    form_list = recent.get("form", [])
    filing_date_list = recent.get("filingDate", [])
    accession_number_list = recent.get("accessionNumber", [])
    primary_doc_list = recent.get("primaryDocument", [])

    filings = []

    for i, form in enumerate(form_list):
        if form in forms:
            accession_number = accession_number_list[i]
            primary_document = primary_doc_list[i]

            urls = build_filing_urls(
                cik=normalized_cik,
                accession_number=accession_number,
                primary_document=primary_document
            )

            filings.append({
                "form": form,
                "filing_date": filing_date_list[i],
                "accession_number": accession_number,
                "primary_document": primary_document,
                "filing_detail_url": urls["filing_detail_url"],
                "filing_document_url": urls["filing_document_url"]
            })

        if len(filings) >= limit:
            break

    return filings