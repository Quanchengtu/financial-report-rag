# 結合 rule-based & semantic retrieval，最後回傳最相關的財報chunk
from app.services.retriever import retrieve_relevant_chunks
from app.services.embedding_service import embed_text
from app.services.vector_store import query_similar_chunks
from app.services.sec_client import build_filing_urls, normalize_cik, fetch_filing_html
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text
from app.services.section_parser import extract_sections, get_priority_sections_for_question


def build_rule_based_chunk_records(
    cik: str,
    accession_number: str,
    primary_document: str,
    question: str,
) -> tuple[list[dict], str, list[str], str]:
    normalized_cik = normalize_cik(cik)

    urls = build_filing_urls(
        cik=normalized_cik,
        accession_number=accession_number,
        primary_document=primary_document
    )

    html_content = fetch_filing_html(urls["filing_document_url"])
    text_content = extract_text_from_html(html_content)

    sections = extract_sections(text_content)   # 從完整財報文字中抓出章節
    priority_sections = get_priority_sections_for_question(question)   # 根據使用者問題判斷應該優先看哪些財報章節

    selected_sections = []   
    if priority_sections and sections:   # 挑出優先section
        selected_sections = [
            section for section in sections
            if section["section_name"] in priority_sections
        ]

    chunk_records = []
    chunk_index = 0

    # 若有成功找到優先章節，就只針對那些章節切 chunk
    if selected_sections:
        for section in selected_sections:
            section_chunks = chunk_text(
                section["text"],
                chunk_size=800,
                overlap=100
            )

            # 將 section chunk 加進 chunk_records
            for chunk in section_chunks:
                chunk_records.append({
                    "chunk_index": chunk_index,
                    "section_name": section["section_name"],
                    "text": chunk
                })
                chunk_index += 1
    else:   # (fallback) 沒有選到section 就切整份財報
        full_chunks = chunk_text(text_content, chunk_size=800, overlap=100)
        for chunk in full_chunks:
            chunk_records.append({
                "chunk_index": chunk_index,
                "section_name": None,
                "text": chunk
            })
            chunk_index += 1

    return chunk_records, urls["filing_document_url"], priority_sections, normalized_cik

# (核心程式碼)用 rule-based retrieval 和 semantic retrieval 各找一批相關 chunk，then合併、去重、排序，最後回傳 top_k 筆
def hybrid_retrieve(
    cik: str,
    accession_number: str,
    primary_document: str,
    question: str,
    top_k: int = 5
) -> dict:     # 先建立 rule-based chunks
    chunk_records, filing_document_url, priority_sections, normalized_cik = build_rule_based_chunk_records(
        cik=cik,
        accession_number=accession_number,
        primary_document=primary_document,
        question=question
    )

    rule_results = retrieve_relevant_chunks(   # 根據問題，在 chunk_records 裡面找最相關的 chunks
        question=question,
        chunks=chunk_records,
        top_k=top_k
    )

    semantic_results = []
    try:
        query_embedding = embed_text(question)

        vector_results = query_similar_chunks(   # 去 vector DB 查相似 chunks
            query_embedding=query_embedding,
            top_k=top_k,
            where={   # 限定在同一份財報裡面找
                "cik": normalized_cik,
                "accession_number": accession_number,
                "primary_document": primary_document
            }
        )
        # 取出 vector DB 回傳內容
        docs = vector_results.get("documents", [[]])[0]
        metadatas = vector_results.get("metadatas", [[]])[0]
        distances = vector_results.get("distances", [[]])[0]   # 距離越小代表越相似

        for doc, metadata, distance in zip(docs, metadatas, distances):
            semantic_results.append({
                "chunk_index": metadata.get("chunk_index"),
                "section_name": metadata.get("section_name"),
                "score": 100 - int(distance * 100) if distance is not None else 0,   # 把 distance 轉成分數，距離越小分數會越高
                "matched_terms": ["semantic_match"],
                "text": doc
            })
    except Exception as e:   # 若 semantic retrieval 出錯，就略過，僅使用rule-baed retrieval
        print(f"Semantic retrieval failed: {e}")
        semantic_results = []

    merged = []   # 將兩種檢索結果合在一起，並且去除重複文字
    seen_texts = set()

    # 合併並去重
    for item in rule_results + semantic_results:   # 兩個 list 直接相加合併，逐一迭代每個 item（每個 item 是一個 dict）
        text_key = item.get("text", "").strip().lower()
        if not text_key or text_key in seen_texts:
            continue
        seen_texts.add(text_key)  # seen_text作為一個 set，用來追蹤已看過的文字
        merged.append(item)

    merged.sort(key=lambda x: x.get("score", 0), reverse=True)   # 把所有結果按照 score 從高到低排序

    return {
        "cik": normalized_cik,
        "filing_document_url": filing_document_url,
        "used_priority_sections": priority_sections,
        "results": merged[:top_k]
    }