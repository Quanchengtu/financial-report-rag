# 將文字轉成向量 可用作語意搜尋、cosine similarity、chunk ranking
# from sentence_transformers import SentenceTransformer   # 載入 embedding model的套件
from app.core.config import EMBEDDING_MODEL_NAME

_model = None   # lazy loading 等到真正需要時再載入
# 因 embedding model 載入通常較慢 若程式一啟動就立刻載入 可能會拖慢整個 server 啟動速度
# lazy loading：等到真正需要 embedding 時才載入模型
# 這樣 FastAPI 啟動時不會立刻 import sentence_transformers
# 可以避免 Docker 輕量版環境因為沒裝 sentence-transformers 而啟動失敗

'''
def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:   # 第一次呼叫時 模型才會被真的載入 後面不需重新載入
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)  # all-MiniLM-L6-v2
    return _model
'''
def get_embedding_model():
    """
    第一次呼叫 embedding 功能時，才載入 SentenceTransformer 模型。
    後續會重用同一個 _model，不會每次重新載入。
    """
    global _model

    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Please install full RAG dependencies before using embedding features."
            ) from exc

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _model


def embed_text(text: str) -> list[float]:
    """
    將單段文字轉成 embedding
    """
    if not text or not text.strip():
        raise ValueError("text cannot be empty")

    model = get_embedding_model()  
    embedding = model.encode(text, normalize_embeddings=True)   # 將 embedding 做正規化 讓向量長度變成 1 使cosine similarity 的計算更穩定
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    批次將多段文字轉成 embeddings
    """
    if not texts:
        return []

    cleaned_texts = [text.strip() for text in texts if text and text.strip()]   # 清除空字串
    if not cleaned_texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(cleaned_texts, normalize_embeddings=True)
    return embeddings.tolist()