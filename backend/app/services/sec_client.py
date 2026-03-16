# sec_client.py 專門負責從 SEC EDGAR 抓公司申報資料回來（10-K、10-Q...）
import os
import requests
from dotenv import load_dotenv
 
load_dotenv()  # 讀 .env 檔案裡的設定

SEC_USER_AGENT = os.getenv(  # 把 SEC 的 User-Agent 設計成可配置的環境變數 有就用env的值 沒有就用後面預設字串
    "SEC_USER_AGENT",
    "FinancialReportRAG/1.0 (Quanchengtu; quanchengtu@gmail.com)"
)

HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate", # SEC回傳壓縮過的內容 可以解壓
    "Host": "data.sec.gov"
}


def get_company_submissions(cik: str): # 根據公司 CIK，去 SEC 抓這家公司的 submissions JSON
    """
    Fetch company submissions JSON from SEC.
    cik should be 10-digit zero-padded string, e.g. 0001045810 for NVDA 
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"   # 此網址回傳該公司的申報資料 JSON
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()  # 確認request回應狀態 有誤會跳出例外
    return response.json()


def get_recent_filings(cik: str, forms=None, limit=10): # 從某家公司所有 recent filings 裡面，挑出想要的 form type，如 10-K、10-Q
    """
    Return recent filings filtered by form type.
    forms example: ["10-K", "10-Q"]
    """
    if forms is None:
        forms = ["10-K", "10-Q"]

    data = get_company_submissions(cik)
    recent = data.get("filings", {}).get("recent", {})

    # 取出各欄位陣列 每個欄位各自是一個 list
    form_list = recent.get("form", [])
    accession_list = recent.get("accessionNumber", [])
    filing_date_list = recent.get("filingDate", [])
    primary_doc_list = recent.get("primaryDocument", [])
    primary_desc_list = recent.get("primaryDocDescription", [])

    results = []
    # zip(..) 把多個 list 橫向對齊一起跑，第 1 個 form 對第 1 個 accession 對第 1 個 filing date..類推
    for form, accession, filing_date, primary_doc, primary_desc in zip(
        form_list,
        accession_list,
        filing_date_list,
        primary_doc_list,
        primary_desc_list
    ):
        if form in forms: # 只保留所指定的 filing 類型
            results.append({  # 把符合條件的 filing，整理成自己定義的乾淨格式
                "form": form,
                "filing_date": filing_date,
                "accession_number": accession, # filing 的唯一識別碼之一，之後常用來組 URL
                "primary_document": primary_doc, # 主文件檔名
                "primary_doc_description": primary_desc # 描述
            })

        if len(results) >= limit: # 若已經收集到夠多筆，就提早停止，不繼續掃描，較有效率
            break

    return results