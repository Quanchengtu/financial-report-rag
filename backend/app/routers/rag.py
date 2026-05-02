from fastapi import APIRouter, HTTPException, Query
from app.services.sec_client import build_filing_urls, normalize_cik, fetch_filing_html
from app.services.html_parser import extract_text_from_html
from app.services.text_chunker import chunk_text
from app.services.retriever import retrieve_relevant_chunks
from app.services.section_parser import extract_sections, get_priority_sections_for_question

from app.services.embedding_service import embed_text
from app.services.vector_store import query_similar_chunks
from app.services.indexing_service import index_filing

from app.services.answer_service import build_grounded_answer, build_llm_grounded_answer
from app.services.hybrid_retrieval import hybrid_retrieve
from app.services.llm_service import LLMServiceError
from app.core.config import RAG_LLM_ENABLED, RAG_LLM_TEMPERATURE

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/retrieve")
def retrieve_from_filing(
    cik: str = Query(..., description="Company CIK"),
    accession_number: str = Query(..., description="SEC accession number"),
    primary_document: str = Query(..., description="Primary document file name"),
    question: str = Query(..., description="User question"),
    top_k: int = Query(3, ge=1, le=10, description="How many top chunks to return")
):
    try:
        normalized_cik = normalize_cik(cik)

        urls = build_filing_urls(
            cik=normalized_cik,
            accession_number=accession_number,
            primary_document=primary_document
        )

        html_content = fetch_filing_html(urls["filing_document_url"])
        text_content = extract_text_from_html(html_content)

        sections = extract_sections(text_content)
        priority_sections = get_priority_sections_for_question(question)

        selected_sections = []
        if priority_sections and sections:
            selected_sections = [
                section for section in sections
                if section["section_name"] in priority_sections
            ]

        chunk_records = []
        chunk_index = 0

        if selected_sections:
            for section in selected_sections:
                section_chunks = chunk_text(
                    section["text"],
                    chunk_size=800,
                    overlap=100
                )

                for chunk in section_chunks:
                    chunk_records.append({
                        "chunk_index": chunk_index,
                        "section_name": section["section_name"],
                        "text": chunk
                    })
                    chunk_index += 1
        else:
            full_chunks = chunk_text(text_content, chunk_size=800, overlap=100)
            for chunk in full_chunks:
                chunk_records.append({
                    "chunk_index": chunk_index,
                    "section_name": None,
                    "text": chunk
                })
                chunk_index += 1

        results = retrieve_relevant_chunks(
            question=question,
            chunks=chunk_records,
            top_k=top_k
        )

        return {
            "mode": "rule_based",
            "cik": normalized_cik,
            "accession_number": accession_number,
            "primary_document": primary_document,
            "filing_document_url": urls["filing_document_url"],
            "question": question,
            "text_length": len(text_content),
            "section_count": len(sections),
            "used_priority_sections": priority_sections,
            "chunk_count": len(chunk_records),
            "matched_count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunks: {str(e)}")
    

@router.post("/index")
def index_filing_to_vector_db(
    cik: str = Query(..., description="Company CIK"),
    accession_number: str = Query(..., description="SEC accession number"),
    primary_document: str = Query(..., description="Primary document file name"),
    ticker: str | None = Query(None, description="Company ticker, e.g. NVDA"),
    form_type: str | None = Query(None, description="Filing type, e.g. 10-K"),
    filing_date: str | None = Query(None, description="Filing date, e.g. 2024-02-21")
):
    try:
        result = index_filing(
            cik=cik,
            accession_number=accession_number,
            primary_document=primary_document,
            company_ticker=ticker,
            form_type=form_type,
            filing_date=filing_date
        )

        return {
            "message": "Filing indexed successfully",
            **result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index filing: {str(e)}")


@router.get("/semantic-retrieve")
def semantic_retrieve(
    question: str = Query(..., description="User question"),
    top_k: int = Query(5, ge=1, le=10, description="How many top chunks to return"),
    cik: str | None = Query(None, description="Optional company CIK filter"),
    ticker: str | None = Query(None, description="Optional ticker filter"),
    form_type: str | None = Query(None, description="Optional form type filter")
):
    try:
        query_embedding = embed_text(question)

        where = {}

        if cik:
            where["cik"] = normalize_cik(cik)
        if ticker:
            where["ticker"] = ticker
        if form_type:
            where["form_type"] = form_type

        if not where:
            where = None

        results = query_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            where=where
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        formatted_results = []
        for doc_id, doc, metadata, distance in zip(ids, documents, metadatas, distances):
            formatted_results.append({
                "id": doc_id,
                "score": 1 - distance if distance is not None else None,
                "text": doc,
                "metadata": metadata
            })

        return {
            "mode": "semantic",
            "question": question,
            "top_k": top_k,
            "filters": {
                "cik": cik,
                "ticker": ticker,
                "form_type": form_type
            },
            "matched_count": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run semantic retrieval: {str(e)}")

@router.get("/answer")
def answer_question_from_filing(
    cik: str = Query(..., description="Company CIK"),
    accession_number: str = Query(..., description="SEC accession number"),
    primary_document: str = Query(..., description="Primary document file name"),
    question: str = Query(..., description="User question"),
    top_k: int = Query(5, ge=1, le=10, description="How many top chunks to use"),
    max_sentences: int = Query(4, ge=1, le=8, description="How many supporting sentences to use"),
    use_llm: bool = Query(True, description="Whether to use LLM answer generation"),
    llm_temperature: float = Query(RAG_LLM_TEMPERATURE, ge=0.0, le=1.0, description="LLM temperature"),
):
    try:
        normalized_cik = normalize_cik(cik)

        urls = build_filing_urls(
            cik=normalized_cik,
            accession_number=accession_number,
            primary_document=primary_document
        )

        html_content = fetch_filing_html(urls["filing_document_url"])
        text_content = extract_text_from_html(html_content)

        sections = extract_sections(text_content)
        priority_sections = get_priority_sections_for_question(question)

        selected_sections = []
        if priority_sections and sections:
            selected_sections = [
                section for section in sections
                if section["section_name"] in priority_sections
            ]

        chunk_records = []
        chunk_index = 0

        if selected_sections:
            for section in selected_sections:
                section_chunks = chunk_text(
                    section["text"],
                    chunk_size=800,
                    overlap=100
                )

                for chunk in section_chunks:
                    chunk_records.append({
                        "chunk_index": chunk_index,
                        "section_name": section["section_name"],
                        "text": chunk
                    })
                    chunk_index += 1
        else:
            full_chunks = chunk_text(text_content, chunk_size=800, overlap=100)
            for chunk in full_chunks:
                chunk_records.append({
                    "chunk_index": chunk_index,
                    "section_name": None,
                    "text": chunk
                })
                chunk_index += 1

        retrieved_chunks = retrieve_relevant_chunks(
            question=question,
            chunks=chunk_records,
            top_k=top_k
        )

        fallback_used = False
        model = None
        usage = {}

        if use_llm and RAG_LLM_ENABLED:
            try:
                answer_result = build_llm_grounded_answer(
                    question=question,
                    retrieved_chunks=retrieved_chunks,
                    temperature=llm_temperature,
                )
                model = answer_result.get("model")
                usage = answer_result.get("usage", {})
                mode = "llm_grounded_answer_v1"
            except LLMServiceError:
                fallback_used = True
                answer_result = build_grounded_answer(
                    question=question,
                    retrieved_chunks=retrieved_chunks,
                    max_sentences=max_sentences
                )
                mode = "grounded_answer_v2_fallback"
        else:
            answer_result = build_grounded_answer(
                question=question,
                retrieved_chunks=retrieved_chunks,
                max_sentences=max_sentences
            )
            mode = "grounded_answer_v2"

        return {
            "mode": mode,
            "cik": normalized_cik,
            "accession_number": accession_number,
            "primary_document": primary_document,
            "filing_document_url": urls["filing_document_url"],
            "question": question,
            "used_priority_sections": priority_sections,
            "matched_count": len(retrieved_chunks),
            "summary_answer": answer_result["summary_answer"],
            "answer": answer_result["answer"],
            "detected_topics": answer_result["detected_topics"],
            "supporting_sentences": answer_result["supporting_sentences"],
            "sources": answer_result["sources"],
            "fallback_used": fallback_used,
            "model": model,
            "usage": usage
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")
    

@router.get("/hybrid-answer")
def hybrid_answer_question_from_filing(
    cik: str = Query(..., description="Company CIK"),
    accession_number: str = Query(..., description="SEC accession number"),
    primary_document: str = Query(..., description="Primary document file name"),
    question: str = Query(..., description="User question"),
    top_k: int = Query(5, ge=1, le=10, description="How many top chunks to use"),
    max_sentences: int = Query(4, ge=1, le=8, description="How many supporting sentences to use"),
    use_llm: bool = Query(True, description="Whether to use LLM answer generation"),
    llm_temperature: float = Query(RAG_LLM_TEMPERATURE, ge=0.0, le=1.0, description="LLM temperature"),
):
    try:
        retrieval_result = hybrid_retrieve(
            cik=cik,
            accession_number=accession_number,
            primary_document=primary_document,
            question=question,
            top_k=top_k
        )

        retrieved_chunks = retrieval_result["results"]

        answer_result = build_grounded_answer(
            question=question,
            retrieved_chunks=retrieved_chunks,
            max_sentences=max_sentences
        )

        return {
            "mode": "hybrid_grounded_answer_v2",
            "cik": retrieval_result["cik"],
            "accession_number": accession_number,
            "primary_document": primary_document,
            "filing_document_url": retrieval_result["filing_document_url"],
            "question": question,
            "used_priority_sections": retrieval_result["used_priority_sections"],
            "matched_count": len(retrieved_chunks),
            "summary_answer": answer_result["summary_answer"],
            "answer": answer_result["answer"],
            "detected_topics": answer_result["detected_topics"],
            "supporting_sentences": answer_result["supporting_sentences"],
            "sources": answer_result["sources"],
            "fallback_used": fallback_used,
            "model": model,
            "usage": usage
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run hybrid answer: {str(e)}")