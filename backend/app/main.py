from fastapi import FastAPI
from app.routers.company import router as company_router

app = FastAPI(title="Financial Report RAG Assistant")

app.include_router(company_router)


@app.get("/")
def read_root():
    return {"message": "Financial Report RAG backend is running"}