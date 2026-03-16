# sec.py 僅定義API 回傳的JSON格式，不負責抓資料、路由、商業邏輯
from pydantic import BaseModel # Pydantic 的核心類別，只要繼承 BaseModel，即可建立一個「有結構、有型別檢查」的資料模型
from typing import List  # 型別提示，表示是一個列表


class CompanyInfoResponse(BaseModel):
    cik: str
    name: str | None = None
    tickers: list[str] = []
    sic_description: str | None = None

'''範例格式：
{
  "cik": "0000320193",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "sic_description": "Electronic Computers"
}
'''

# 定義一筆 filing 紀錄裡面要有哪些欄位
class FilingItem(BaseModel):
    form: str          # 類型 10-K / 10-Q...
    filing_date: str   # 申報日期
    accession_number: str   # SEC filing 編號
    primary_document: str   # 主要文件檔名
    filing_detail_url: str  # 該 filing 的 detail 頁面
    filing_document_url: str   # 直接文件連結

'''範例格式：
{
  "form": "10-K",
  "filing_date": "2025-11-01",
  "accession_number": "0000320193-25-000123",
  "primary_document": "a10-k2025.htm",
  "filing_detail_url": "...",
  "filing_document_url": "..."
}
'''

# 規範 /company/{cik}/filings 這支 API
class CompanyFilingsResponse(BaseModel):
    cik: str
    filings: List[FilingItem]

''' 範例格式：
{
  "cik": "0000320193",
  "filings": [
    {
      "form": "10-K",
      "filing_date": "2025-11-01",
      "accession_number": "...",
      "primary_document": "...",
      "filing_detail_url": "...",
      "filing_document_url": "..."
    }
  ]
}
'''