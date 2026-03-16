# company.py  處理公司相關API的路由檔
# 接收 API 請求，呼叫 service 層處理資料，再把結果整理後回傳，抓資料邏輯位於sec_client.py
from fastapi import APIRouter, HTTPException  # 路由整理器 可將一組 API 路由整理在同一個檔案裡 / 錯誤回傳
from app.schemas.sec import CompanyInfoResponse, CompanyFilingsResponse # sec.py 已定義好的回傳資料格式
from app.services.sec_client import (  # sec_client.py中定義好的資料處理邏輯
    get_company_submissions,
    get_recent_filings,
    normalize_cik
)
# 建立router，該檔案所有API前綴都會自動加上 /company
router = APIRouter(prefix="/company", tags=["Company"])  # 歸類於API文件頁面的Company標籤

# API 1. 查公司基本資訊
# 此API 回傳的資料，應該符合 CompanyInfoResponse 這個 schema 格式
@router.get("/{cik}", response_model=CompanyInfoResponse)  # e.g. /company/320193
def get_company_info(cik: str):
    try:
        data = get_company_submissions(cik)  # 呼叫 sec_client.py 的函式 去SEC API 抓取公司資料
        return {                             # 整理回傳格式，只挑想要的欄位回傳
            "cik": normalize_cik(cik),       # 使用者輸入的cik可能不一致，統一正規化成10碼
            "name": data.get("name"),
            "tickers": data.get("tickers", []), # 有ticker就拿 沒有則回傳空陣列
            "sic_description": data.get("sicDescription")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch company info: {str(e)}")

# API 2. 查公司近期 filings
@router.get("/{cik}/filings", response_model=CompanyFilingsResponse)
def get_company_filings(cik: str):
    try:
        filings = get_recent_filings(cik, forms=["10-K", "10-Q"], limit=10) # 只抓10K, 10Q, 最多10筆
        return {
            "cik": normalize_cik(cik),
            "filings": filings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch company filings: {str(e)}")