import os
from html import escape

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

COMPANY_OPTIONS = {
    "NVIDIA (NVDA)": {"cik": "1045810", "ticker": "NVDA"},
    "Apple (AAPL)": {"cik": "320193", "ticker": "AAPL"},
    "Microsoft (MSFT)": {"cik": "789019", "ticker": "MSFT"},
}

st.set_page_config(
    page_title="Financial Report RAG Demo", page_icon="📊", layout="wide"
)
st.markdown(
    """
    <style>
        .hero-card {
            padding: 1.4rem 1.6rem;
            border-radius: 1rem;
            background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #2563eb 100%);
            color: white;
            margin-bottom: 1.25rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
        }
        .hero-card h1 {
            color: white;
            margin: 0 0 0.35rem 0;
            font-size: 2rem;
        }
        .hero-card p {
            color: rgba(255, 255, 255, 0.86);
            margin: 0;
            font-size: 1rem;
        }
        .section-note {
            color: #64748b;
            font-size: 0.92rem;
            margin-bottom: 0.75rem;
        }
        .answer-card {
            padding: 1.1rem 1.25rem;
            border: 1px solid #e2e8f0;
            border-radius: 0.9rem;
            background: #f8fafc;
            margin-bottom: 1rem;
        }
        .source-card {
            padding: 1rem 1.15rem;
            border: 1px solid #e5e7eb;
            border-left: 4px solid #2563eb;
            border-radius: 0.85rem;
            background: #ffffff;
            margin-bottom: 0.8rem;
        }
        .source-title {
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.45rem;
        }
        .muted-meta {
            color: #64748b;
            font-size: 0.82rem;
            margin-top: 0.5rem;
        }
    </style>
    <div class="hero-card">
        <h1>📊 Financial Report Q&A Demo</h1>
        <p>Select a company and filing, ask in Chinese or English, then review the answer with grounded evidence.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Analysis Settings")
    st.caption(
        "These controls keep the original RAG behavior, but use friendlier labels."
    )
    with st.expander("Advanced retrieval settings", expanded=False):
        top_k = st.slider(
            "Evidence depth",
            min_value=1,
            max_value=8,
            value=4,
            help="How many evidence chunks the system should retrieve before answering.",
        )
        max_sentences = st.slider(
            "Answer length",
            min_value=1,
            max_value=8,
            value=4,
            help="Maximum number of supporting sentences used to keep the answer concise.",
        )

company_label = st.selectbox("Company", list(COMPANY_OPTIONS.keys()))
form_type = st.radio("Filing Type", options=["10-K", "10-Q"], horizontal=True)
question = st.text_area(
    "Your Question (中文 / English)",
    placeholder="e.g., What are the major risk factors?",
)


def fetch_recent_filings(cik: str):
    resp = requests.get(f"{API_BASE_URL}/company/{cik}/filings", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    filings = data.get("filings", [])
    return [f for f in filings if f.get("form") == form_type]


def ask_question(cik: str, filing: dict, question_text: str):
    params = {
        "cik": cik,
        "accession_number": filing["accession_number"],
        "primary_document": filing["primary_document"],
        "question": question_text,
        "top_k": top_k,
        "max_sentences": max_sentences,
        "use_llm": "true",
        "auto_index": "true",
        "ticker": COMPANY_OPTIONS[company_label]["ticker"],
        "form_type": filing.get("form") or form_type,
        "filing_date": filing.get("filing_date") or "",
    }
    resp = requests.get(f"{API_BASE_URL}/rag/hybrid-answer", params=params, timeout=180)
    resp.raise_for_status()
    return resp.json()


def has_semantic_results(result: dict) -> bool | None:
    """Return whether the hybrid response reports semantic/vector matches, if available."""
    semantic_matched_count = result.get("semantic_matched_count")
    if semantic_matched_count is not None:
        return semantic_matched_count > 0

    retrieval_diagnostics = result.get("retrieval_diagnostics") or {}
    vector_matched_count = retrieval_diagnostics.get("vector_matched_count")
    if vector_matched_count is None:
        vector_matched_count = retrieval_diagnostics.get("vector_raw_count")
    if vector_matched_count is not None:
        return vector_matched_count > 0

    return None


def show_retrieval_behavior(result: dict):
    behavior_fields = {
        "mode": result.get("mode"),
        "fallback_used": result.get("fallback_used"),
        "fallback_reason": result.get("fallback_reason") or "None",
        "model": result.get("model") or "N/A",
        "matched_count": result.get("matched_count"),
        "semantic_matched_count": result.get("semantic_matched_count"),
        "index_status": result.get("index_status") or {},
        "used_priority_sections": result.get("used_priority_sections") or [],
    }
    mode = behavior_fields["mode"] or "N/A"
    model = behavior_fields["model"] or "N/A"
    fallback_used = behavior_fields["fallback_used"]
    st.caption(
        f"Retrieval status: mode={mode} | model={model} | fallback_used={fallback_used}"
    )

    with st.expander("Advanced retrieval diagnostics", expanded=False):
        st.json(behavior_fields)

    if has_semantic_results(result) is False:
        st.warning(
            "No semantic/vector results were available for this filing. "
            "Hybrid retrieval is using rule-based fallback results only; index the filing in the vector store "
            "to enable semantic retrieval."
        )


if st.button("Load Filings"):
    try:
        cik = COMPANY_OPTIONS[company_label]["cik"]
        filtered_filings = fetch_recent_filings(cik)
        st.session_state["filings"] = filtered_filings
        st.session_state["selected_company_cik"] = cik

        if not filtered_filings:
            st.warning(f"No recent {form_type} filings found for {company_label}.")
        else:
            st.success(f"Loaded {len(filtered_filings)} {form_type} filings.")
    except Exception as exc:
        st.error(f"Failed to load filings: {exc}")

filings = st.session_state.get("filings", [])
if filings:
    filing_options = {
        f"{item.get('filing_date', 'N/A')} | {item.get('form', 'N/A')} | {item.get('primary_document', 'N/A')}": item
        for item in filings
    }
    selected_key = st.selectbox("Select Filing", list(filing_options.keys()))
    selected_filing = filing_options[selected_key]

    if st.button("Analyze"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                with st.spinner("Analyzing filing..."):
                    result = ask_question(
                        cik=st.session_state["selected_company_cik"],
                        filing=selected_filing,
                        question_text=question,
                    )

                st.subheader("Answer")
                st.markdown(
                    f"""
                    <div class="answer-card">
                        {escape(str(result.get("answer") or "No answer generated."))}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                show_retrieval_behavior(result)

                fallback_used = result.get("fallback_used")
                mode = result.get("mode") or "N/A"
                model = result.get("model") or "N/A"
                fallback_reason = result.get("fallback_reason") or "None"

                st.caption(
                    " | ".join(
                        [
                            f"fallback_used={fallback_used}",
                            f"mode={mode}",
                            f"model={model}",
                            f"fallback_reason={fallback_reason}",
                        ]
                    )
                )
                st.subheader("Summary")
                st.markdown(
                    '<div class="section-note">A short preview of the generated summary answer.</div>',
                    unsafe_allow_html=True,
                )
                # summary = result.get("answer", "")
                summary = result.get("summary_answer", "")
                st.write(summary[:300] + ("..." if len(summary) > 300 else ""))
                # st.caption(
                #     f"mode={result.get('mode')} | fallback_used={result.get('fallback_used')} | model={result.get('model') or 'N/A'}"
                # )

                st.subheader("Evidence")
                st.markdown(
                    '<div class="section-note">Grounded sentences or source chunks used to support the answer.</div>',
                    unsafe_allow_html=True,
                )
                supporting_sentences = result.get("supporting_sentences", [])

                sources = result.get("sources", [])
                if supporting_sentences:
                    for idx, item in enumerate(supporting_sentences, start=1):
                        section_name = item.get("section_name") or "N/A"
                        st.markdown(
                            f"""
                            <div class="source-card">
                                <div class="source-title">Evidence #{idx} · {section_name}</div>
                                <div>{escape(str(item.get("sentence") or ""))}</div>
                                <div class="muted-meta">
                                    chunk_index={item.get("chunk_index")} · chunk_rank={item.get("chunk_rank")} · sentence_score={item.get("sentence_score")}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                elif sources:
                    st.info(
                        "No sentence-level evidence was returned; showing retrieved source chunks instead."
                    )
                    for idx, source in enumerate(sources, start=1):
                        source_rank = source.get("source_rank", idx)
                        section_name = source.get("section_name") or "N/A"
                        st.markdown(
                            f"""
                            <div class="source-card">
                                <div class="source-title">Source #{source_rank} · {section_name}</div>
                                <div>{escape(str(source.get("text_excerpt") or ""))}</div>
                                <div class="muted-meta">
                                    source_rank={source_rank} · chunk_index={source.get("chunk_index")} · score={source.get("score")}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("No supporting sentences were returned.")

            except Exception as exc:
                st.error(f"Failed to analyze filing: {exc}")
else:
    st.info("Load filings first to continue.")
