# sec_client.py 負責主要與SEC溝通的邏輯
import requests   # Python 用來發 HTTP 請求的套件，用於抓SEC API
from app.core.config import SEC_USER_AGENT 

# 定義基底網址
BASE_SUBMISSIONS_URL = "https://data.sec.gov/submissions"   # 抓公司 submissions JSON
BASE_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"   # 組 filing detail 頁面與文件連結

HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",  # 接受壓縮回應
    "Host": "data.sec.gov"   # 指定目標主機
}


def normalize_cik(cik: str) -> str: # 統一cik格式
    """
    將 CIK 補成 SEC 需要的 10 位數格式
    e.g. 320193 -> 0000320193
    """
    return str(cik).zfill(10)


def get_company_submissions(cik: str) -> dict:
    """
    從 SEC 取得公司 submissions 資料
    """
    cik = normalize_cik(cik)
    url = f"{BASE_SUBMISSIONS_URL}/CIK{cik}.json"  # 組出網址

    response = requests.get(url, headers=HEADERS, timeout=30)  # 發送get請求 帶上header資料
    response.raise_for_status()  # 檢查是否有異常（Exception處理）
    return response.json()       # 將SEC 回傳的 JSON 轉成 Python dict


def build_filing_urls(cik: str, accession_number: str, primary_document: str) -> dict:
    """
    自行組合出 (1) filing detail 頁面 URL 與 (2)文件 URL
    """
    cik_no_zero = str(int(cik))  # 去除前導0 (因Archives 路徑通常用的是「沒有前導零的 CIK」)
    accession_no_dash = accession_number.replace("-", "")  # 去掉number中的 "-"

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


def fetch_filing_html(url: str) -> str:
    """
    根據 filing_document_url 抓取 SEC 原始 HTML 內容
    """
    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


# 從 SEC submissions 裡，挑出最近幾筆指定類型的 filings，並整理成想要的特定格式
def get_recent_filings(cik: str, forms=None, limit: int = 10) -> list:
    
    if forms is None:  # 沒特別指定預設抓 10-K / 10-Q
        forms = ["10-K", "10-Q"]

    normalized_cik = normalize_cik(cik)
    data = get_company_submissions(normalized_cik)
    recent = data.get("filings", {}).get("recent", {}) # recent 裡通常是一組“平行”陣列資料
    ''' recent 範例  （同一個 index 代表同一筆 filing -> form[0], filingDate[0], accession_number_list[0]...加起來才是第一組filing)
        {
            "form": ["10-K", "8-K", "10-Q"],
            "filingDate": ["2025-01-01", "2025-02-01", "2025-03-01"],
            ...
        }
    '''

    form_list = recent.get("form", [])
    filing_date_list = recent.get("filingDate", [])
    accession_number_list = recent.get("accessionNumber", [])
    primary_doc_list = recent.get("primaryDocument", [])

    filings = []   # 建立空清單，將篩選後的結果放入

    for i, form in enumerate(form_list):   # 逐一看每一筆 filing 的 form 類型
        if form in forms:     # 如果是想要的類型如 10-K 或 10-Q，就繼續處理
            accession_number = accession_number_list[i]  # index同為i
            primary_document = primary_doc_list[i]

            urls = build_filing_urls(   # 組出URL
                cik=normalized_cik,
                accession_number=accession_number,
                primary_document=primary_document
            )

            # 將SEC 原始資料整理成你 API 想要回傳的格式，key 名稱要對應到 FilingItem schema，此處為schema 跟 service 層配合的地方
            filings.append({   
                "form": form,
                "filing_date": filing_date_list[i],
                "accession_number": accession_number,
                "primary_document": primary_document,
                "filing_detail_url": urls["filing_detail_url"],
                "filing_document_url": urls["filing_document_url"]
            })

        if len(filings) >= limit: # 若以收集到指定筆數如 10 筆，就停止 -> 避免回太多資料。
            break

    return filings   # 回傳的是一個 list，每一項都是整理過的 filing dict

''' sec_client.py 主要邏輯：
1. 呼叫 SEC API
2. 處理請求 header
3. 正規化 CIK
4. 組出 filing 連結
5. 從 submissions 資料中整理出最近的 10-K / 10-Q
'''