import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME, RAG_LLM_ENABLED
from app.routers.company import router as company_router
# 從 app/routers/company.py 這個檔案裡，使用已經定義好的 router，命名為company_router
from app.routers.filing import router as filing_router
from app.routers.rag import router as rag_router

# app = FastAPI(title="Financial Report RAG Assistant")
logger = logging.getLogger(__name__)


def _build_llm_health() -> dict:
    """Validate LLM environment without exposing secrets."""
    missing = []
    if not LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if not LLM_BASE_URL:
        missing.append("LLM_BASE_URL")
    if not LLM_MODEL_NAME:
        missing.append("LLM_MODEL_NAME")

    return {
        "enabled": RAG_LLM_ENABLED,
        "ready": RAG_LLM_ENABLED and not missing,
        "missing": missing,
        "config": {
            "llm_api_key_set": bool(LLM_API_KEY),
            "llm_base_url": LLM_BASE_URL or None,
            "llm_model_name": LLM_MODEL_NAME or None,
        },
    }


def log_llm_health() -> None:
    health = _build_llm_health()
    logger.info(
        "LLM health: enabled=%s ready=%s missing=%s base_url=%s model=%s api_key_set=%s",
        health["enabled"],
        health["ready"],
        health["missing"],
        health["config"]["llm_base_url"],
        health["config"]["llm_model_name"],
        health["config"]["llm_api_key_set"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_llm_health()
    yield


app = FastAPI(title="Financial Report RAG Assistant", lifespan=lifespan)


app.include_router(company_router) # 將company.py 裡面定義好的所有 API 路由 掛載到主 app 裡面
app.include_router(filing_router)
app.include_router(rag_router)


@app.get("/") # 初始測試API是否正常運作
def read_root(): 
    return {"message": "Financial Report RAG backend is running"}

@app.get("/health/llm")
def llm_health():
    return _build_llm_health()