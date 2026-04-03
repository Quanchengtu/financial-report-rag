import chromadb
from app.core.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME


def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"description": "Financial filing chunks"}
    )


def upsert_chunks(
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict]
):
    if not ids:
        return

    collection = get_collection()
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )


def query_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    where: dict | None = None
) -> dict:
    collection = get_collection()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where
    )
    return results