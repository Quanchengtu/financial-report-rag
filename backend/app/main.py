from fastapi import FastAPI
from app.services.sec_client import get_company_submissions, get_recent_filings
# 將寫好的 sec_client.py 功能，包成可以被瀏覽器或前端呼叫的 API

app = FastAPI(title="Financial Report RAG Assistant")


@app.get("/")
def read_root():
    return {"message": "Financial Report RAG backend is running"} # 開頭確認 API 是否正常運作


@app.get("/company/{cik}") # 查公司基本資訊 傳入cik
def get_company_info(cik: str):
    data = get_company_submissions(cik) # 呼叫 sec_client.py 中的函式，去 SEC 抓取該公司完整 submissions JSON
    return {
        "name": data.get("name"), # 公司名
        "tickers": data.get("tickers"), # 股票代號
        "sicDescription": data.get("sicDescription")  # 產業描述
    }


@app.get("/company/{cik}/filings") # 查最近filings，給某家公司 CIK，回傳最近的 10-K / 10-Q 清單
def get_company_filings(cik: str):
    filings = get_recent_filings(cik, forms=["10-K", "10-Q"], limit=10)
    return {
        "cik": cik,
        "filings": filings
    }