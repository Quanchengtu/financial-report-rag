from sentence_transformers import SentenceTransformer
from app.core.config import EMBEDDING_MODEL_NAME

_model = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_text(text: str) -> list[float]:
    """
    將單段文字轉成 embedding
    """
    if not text or not text.strip():
        raise ValueError("text cannot be empty")

    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    批次將多段文字轉成 embeddings
    """
    if not texts:
        return []

    cleaned_texts = [text.strip() for text in texts if text and text.strip()]
    if not cleaned_texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(cleaned_texts, normalize_embeddings=True)
    return embeddings.tolist()