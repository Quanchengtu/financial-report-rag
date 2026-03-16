from fastapi import FastAPI
from app.routers.company import router as company_router
# 從 app/routers/company.py 這個檔案裡，使用已經定義好的 router，命名為company_router

app = FastAPI(title="Financial Report RAG Assistant")

app.include_router(company_router) # 將company.py 裡面定義好的所有 API 路由 掛載到主 app 裡面


@app.get("/") # 初始測試API是否正常運作
def read_root(): 
    return {"message": "Financial Report RAG backend is running"}