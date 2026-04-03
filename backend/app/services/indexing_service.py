from app.services.sec_client import (
    build_filing_urls,
    normalize_cik,
    fetch_filing_html
)
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text
from app.services.section_parser import extract_sections
from app.services.embedding_service import embed_texts
from app.services.vector_store import upsert_chunks


def build_chunk_records(
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

    html_content = fetch_filing_html(urls["filing_document_url"])
    text_content = extract_text_from_html(html_content)

    sections = extract_sections(text_content)

    chunk_records = []
    chunk_index = 0

    if sections:
        for section in sections:
            section_name = section["section_name"]
            section_text = section["text"]

            chunks = chunk_text(
                section_text,
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
                        "section_name": section_name,
                        "chunk_index": chunk_index,
                        "filing_document_url": urls["filing_document_url"]
                    }
                })
                chunk_index += 1
    else:
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
                    "section_name": "",
                    "chunk_index": chunk_index,
                    "filing_document_url": urls["filing_document_url"]
                }
            })
            chunk_index += 1

    return chunk_records


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

    ids = [record["id"] for record in chunk_records]
    documents = [record["text"] for record in chunk_records]
    metadatas = [record["metadata"] for record in chunk_records]
    embeddings = embed_texts(documents)

    upsert_chunks(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {
        "indexed_count": len(chunk_records),
        "accession_number": accession_number,
        "primary_document": primary_document
    }