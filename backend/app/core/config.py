import os
from dotenv import load_dotenv

load_dotenv()

SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "Quanchengtu; quanchengtu@gmail.com"
)

# EMBEDDING_MODEL_NAME = os.getenv(
#     "EMBEDDING_MODEL_NAME",
#     "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# )

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2"
)

CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_PERSIST_DIR",
    "./chroma_db"
)

CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "financial_filings"
)

LLM_MODEL_NAME = os.getenv(
    "LLM_MODEL_NAME",
    "gpt-4.1-mini"
)

LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.openai.com/v1"
)

LLM_API_KEY = os.getenv("LLM_API_KEY")

LLM_API_TIMEOUT_SECONDS = int(os.getenv("LLM_API_TIMEOUT_SECONDS", "30"))
