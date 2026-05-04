# 將處理好的財報文字 chunks、embedding、metadata 存進 ChromaDB 
# 且可用 query embedding 查出相似 chunks
import chromadb
from app.core.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME

# 建立一個會把資料永久儲存在指定資料夾的 ChromaDB client
def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)   # 要存放的資料夾 


def get_collection():   # 資料表
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"description": "Financial filing chunks"}   # 此 metadata 作為 collection 的描述資訊
    )

# 將 chunks 寫入 ChromaDB (若 id 已經存在就更新 不存在就新增)
def upsert_chunks(
    ids: list[str],     # 每個 chunk 的唯一 ID
    documents: list[str],     # 每個 chunk 的原始文字
    embeddings: list[list[float]],     # 每個 chunk 對應的 embedding
    metadatas: list[dict]     # 每個 chunk 的附加資訊(可用於過濾查詢)
):
    if not ids:
        return

    collection = get_collection()
    collection.upsert(   # 把資料正式寫進 ChromaDB
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

# 輸入一個問題的 embedding 回傳最相似的前 top_k 個 chunks
def query_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    where: dict | None = None     # metadata filter
) -> dict:
    collection = get_collection()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where
    )
    return results