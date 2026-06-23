from app.services.sec_client import (
    build_filing_urls,
    normalize_cik,
    fetch_filing_html
)
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text
from app.services.section_parser import extract_sections
from app.services.embedding_service import embed_texts
from app.services.vector_store import count_chunks_for_filing, upsert_chunks

# 把一份財報轉成一筆一筆可以存進 vector DB 的 chunk records
def build_chunk_records(   # 抓 HTML / 清 HTML / 抽 section / 切 chunk / 加 metadata
    cik: str,
    accession_number: str,
    primary_document: str,
    company_ticker: str | None = None,
    form_type: str | None = None,
    filing_date: str | None = None,
    chunk_size: int = 800,
    overlap: int = 100
) -> list[dict]:
    normalized_cik = normalize_cik(cik)

    urls = build_filing_urls(
        cik=normalized_cik,
        accession_number=accession_number,
        primary_document=primary_document
    )

    html_content = fetch_filing_html(urls["filing_document_url"])   # 去 SEC 抓財報 HTML 原始內容
    text_content = extract_text_from_html(html_content)   # 把 HTML 清理成純文字

    sections = extract_sections(text_content)   # 嘗試將財將切成不同章節

    chunk_records = []
    chunk_index = 0

    if sections:   # 若extract_sections() 有成功抓出章節，就用「章節模式」切 chunks
        for section in sections:
            section_name = section["section_name"]
            section_text = section["text"]

            chunks = chunk_text(   # 將每個 section 的文字再切成 chunks 效果比整份直接切chunks更好
                section_text,
                chunk_size=chunk_size,
                overlap=overlap
            )

            # 將每個 chunk 包成 record （type Dict)
            for chunk in chunks:
                chunk_records.append({   # 產生每個 chunk 的唯一 ID，便於存入 vector DB時辨認
                    "id": f"{normalized_cik}_{accession_number}_{chunk_index}",
                    "text": chunk,   # 使用者提問時做 retriever 檢索的 chunk text
                    "metadata": {
                        "cik": normalized_cik,
                        "ticker": company_ticker or "",
                        "form_type": form_type or "",
                        "filing_date": filing_date or "",
                        "accession_number": accession_number,
                        "primary_document": primary_document,
                        "section_name": section_name,
                        "chunk_index": chunk_index,
                        "filing_document_url": urls["filing_document_url"]
                    }
                })
                chunk_index += 1

    # 做此 fallback 設計，否則只要 section parser 失敗，整份財報就完全不能 index         
    else:   # 沒有解析出財報章節 就以整份財報切chunks
        chunks = chunk_text(
            text_content,
            chunk_size=chunk_size,
            overlap=overlap
        )

        for chunk in chunks:
            chunk_records.append({
                "id": f"{normalized_cik}_{accession_number}_{chunk_index}",
                "text": chunk,
                "metadata": {
                    "cik": normalized_cik,
                    "ticker": company_ticker or "",
                    "form_type": form_type or "",
                    "filing_date": filing_date or "",
                    "accession_number": accession_number,
                    "primary_document": primary_document,
                    "section_name": "",   # 差別處 因沒有分析出章節
                    "chunk_index": chunk_index,
                    "filing_document_url": urls["filing_document_url"]
                }
            })
            chunk_index += 1

    return chunk_records

def get_index_status(
    cik: str,
    accession_number: str,
    primary_document: str
) -> dict:
    normalized_cik = normalize_cik(cik)
    chunk_count = count_chunks_for_filing(
        cik=normalized_cik,
        accession_number=accession_number,
        primary_document=primary_document
    )
    return {
        "indexed": chunk_count > 0,
        "chunk_count": chunk_count,
        "cik": normalized_cik,
        "accession_number": accession_number,
        "primary_document": primary_document
    }


def ensure_filing_indexed(
    cik: str,
    accession_number: str,
    primary_document: str,
    company_ticker: str | None = None,
    form_type: str | None = None,
    filing_date: str | None = None,
    auto_index: bool = True
) -> dict:
    status = get_index_status(
        cik=cik,
        accession_number=accession_number,
        primary_document=primary_document
    )

    index_status = {
        "auto_index": auto_index,
        "was_indexed_before": status["indexed"],
        "indexed_now": False,
        "chunk_count": status["chunk_count"],
        "cik": status["cik"],
        "accession_number": accession_number,
        "primary_document": primary_document
    }

    if status["indexed"] or not auto_index:
        return index_status

    result = index_filing(
        cik=cik,
        accession_number=accession_number,
        primary_document=primary_document,
        company_ticker=company_ticker,
        form_type=form_type,
        filing_date=filing_date
    )

    indexed_count = result.get("indexed_count", 0)
    index_status.update({
        "indexed_now": indexed_count > 0,
        "chunk_count": indexed_count,
        "index_message": result.get("message"),
    })
    return index_status


# 負責把 chunks 轉 embedding 並存進 vector DB
def index_filing(
    cik: str,
    accession_number: str,
    primary_document: str,
    company_ticker: str | None = None,
    form_type: str | None = None,
    filing_date: str | None = None
) -> dict:
    chunk_records = build_chunk_records(
        cik=cik,
        accession_number=accession_number,
        primary_document=primary_document,
        company_ticker=company_ticker,
        form_type=form_type,
        filing_date=filing_date
    )

    if not chunk_records:
        return {
            "indexed_count": 0,
            "message": "No chunks generated"
        }

    # 將 records 拆成四個 list 
    ids = [record["id"] for record in chunk_records]
    documents = [record["text"] for record in chunk_records]
    metadatas = [record["metadata"] for record in chunk_records]
    embeddings = embed_texts(documents)

    # 存入vector store
    upsert_chunks(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {
        "indexed_count": len(chunk_records),   # chunk count
        "accession_number": accession_number,
        "primary_document": primary_document
    }