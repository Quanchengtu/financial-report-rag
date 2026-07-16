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

QUESTION_TEMPLATES = [
    "What are the major risk factors?",
    "Summarize revenue growth drivers and risks.",
    "What does management say about liquidity and cash flow?",
]

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
        .workflow-card, .analysis-card {
            padding: 1rem 1.15rem;
            border: 1px solid #e2e8f0;
            border-radius: 0.9rem;
            background: #ffffff;
            margin-bottom: 1rem;
        }
        .step-pill {
            display: inline-block;
            padding: 0.25rem 0.65rem;
            border-radius: 999px;
            background: #dbeafe;
            color: #1d4ed8;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 0.45rem;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
            gap: 0.75rem;
            margin: 0.75rem 0 1rem;
        }
        .metric-card {
            padding: 0.85rem 0.95rem;
            border: 1px solid #e2e8f0;
            border-radius: 0.85rem;
            background: #f8fafc;
        }
        .metric-label {
            color: #64748b;
            font-size: 0.78rem;
            margin-bottom: 0.25rem;
        }
        .metric-value {
            color: #0f172a;
            font-size: 1.05rem;
            font-weight: 750;
        }
        .question-template {
            padding: 0.65rem 0.75rem;
            border: 1px dashed #cbd5e1;
            border-radius: 0.75rem;
            color: #475569;
            background: #f8fafc;
            margin-bottom: 0.45rem;
            font-size: 0.9rem;
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
            line-height: 1.65;
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
        <p>Select a report, ask in Chinese or English, and review answer quality with grounded evidence.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Analysis Settings")
    st.caption(
        "Defaults are tuned for a concise investor-style answer. Open this only when you need more control."
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


def render_workflow_header(step_label: str, title: str, body: str):
    st.markdown(
        f"""
        <div class="workflow-card">
            <span class="step-pill">{escape(step_label)}</span>
            <strong>{escape(title)}</strong>
            <div class="section-note" style="margin-top:0.45rem;margin-bottom:0;">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False, ttl=600)
def fetch_recent_filings(cik: str, selected_form_type: str):
    resp = requests.get(f"{API_BASE_URL}/company/{cik}/filings", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    filings = data.get("filings", [])
    return [f for f in filings if f.get("form") == selected_form_type]


def ask_question(cik: str, filing: dict, question_text: str, company_label: str):
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


def render_analysis_overview(result: dict):
    fallback_used = result.get("fallback_used")
    mode = result.get("mode") or "N/A"
    model = result.get("model") or "N/A"
    matched_count = result.get("matched_count") or 0
    semantic_count = result.get("semantic_matched_count")
    semantic_value = "N/A" if semantic_count is None else semantic_count
    st.markdown(
        f"""
        <div class="analysis-card">
            <strong>Analysis overview</strong>
            <div class="metric-grid">
                <div class="metric-card"><div class="metric-label">Retrieval mode</div><div class="metric-value">{escape(str(mode))}</div></div>
                <div class="metric-card"><div class="metric-label">Evidence matches</div><div class="metric-value">{escape(str(matched_count))}</div></div>
                <div class="metric-card"><div class="metric-label">Semantic matches</div><div class="metric-value">{escape(str(semantic_value))}</div></div>
                <div class="metric-card"><div class="metric-label">Model</div><div class="metric-value">{escape(str(model))}</div></div>
                <div class="metric-card"><div class="metric-label">Fallback used</div><div class="metric-value">{escape(str(fallback_used))}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    if has_semantic_results(result) is False:
        st.warning(
            "No semantic/vector results were available for this filing. "
            "Hybrid retrieval is using rule-based fallback results only; index the filing in the vector store "
            "to enable semantic retrieval."
        )

    with st.expander("Advanced retrieval diagnostics", expanded=False):
        st.json(behavior_fields)


def render_evidence(result: dict):
    supporting_sentences = result.get("supporting_sentences", [])
    sources = result.get("sources", [])

    if supporting_sentences:
        for idx, item in enumerate(supporting_sentences, start=1):
            section_name = item.get("section_name") or "N/A"
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">Evidence #{idx} · {escape(str(section_name))}</div>
                    <div>{escape(str(item.get("sentence") or ""))}</div>
                    <div class="muted-meta">
                        chunk_index={escape(str(item.get("chunk_index")))} · chunk_rank={escape(str(item.get("chunk_rank")))} · sentence_score={escape(str(item.get("sentence_score")))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif sources:
        st.info("No sentence-level evidence was returned; showing retrieved source chunks instead.")
        for idx, source in enumerate(sources, start=1):
            source_rank = source.get("source_rank", idx)
            section_name = source.get("section_name") or "N/A"
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">Source #{escape(str(source_rank))} · {escape(str(section_name))}</div>
                    <div>{escape(str(source.get("text_excerpt") or ""))}</div>
                    <div class="muted-meta">
                        source_rank={escape(str(source_rank))} · chunk_index={escape(str(source.get("chunk_index")))} · score={escape(str(source.get("score")))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No supporting sentences were returned.")


render_workflow_header(
    "Step 1",
    "Choose the report",
    "Filings load automatically after you choose a company and report type, so the workflow is now select → ask → analyze.",
)
company_col, form_col = st.columns([2, 1])
with company_col:
    company_label = st.selectbox("Company", list(COMPANY_OPTIONS.keys()))
with form_col:
    form_type = st.radio("Report type", options=["10-K", "10-Q"], horizontal=True)

cik = COMPANY_OPTIONS[company_label]["cik"]
try:
    with st.spinner("Loading recent filings..."):
        filings = fetch_recent_filings(cik, form_type)
except Exception as exc:
    filings = []
    st.error(f"Failed to load filings: {exc}")

if not filings:
    st.warning(f"No recent {form_type} filings found for {company_label}.")
    st.stop()

filing_options = {
    f"{item.get('filing_date', 'N/A')} · {item.get('form', 'N/A')} · {item.get('primary_document', 'N/A')}": item
    for item in filings
}
selected_key = st.selectbox("Filing", list(filing_options.keys()))
selected_filing = filing_options[selected_key]
st.markdown(
    f"""
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">Selected company</div><div class="metric-value">{escape(company_label)}</div></div>
        <div class="metric-card"><div class="metric-label">Report date</div><div class="metric-value">{escape(str(selected_filing.get('filing_date', 'N/A')))}</div></div>
        <div class="metric-card"><div class="metric-label">Document</div><div class="metric-value">{escape(str(selected_filing.get('primary_document', 'N/A')))}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_workflow_header(
    "Step 2",
    "Ask a question",
    "Use a template below or write your own question. The answer will be grounded in the selected SEC filing.",
)
with st.expander("Question templates", expanded=False):
    for template in QUESTION_TEMPLATES:
        st.markdown(f'<div class="question-template">{escape(template)}</div>', unsafe_allow_html=True)
question = st.text_area(
    "Your question (中文 / English)",
    placeholder="e.g., What are the major risk factors?",
    height=110,
)

analyze_clicked = st.button("Analyze selected filing", type="primary", use_container_width=True)
if analyze_clicked:
    if not question.strip():
        st.warning("Please enter a question before analyzing.")
        st.stop()

    try:
        progress_text = st.empty()
        progress_text.info("Preparing filing context and retrieval settings...")
        with st.spinner("Analyzing filing and generating answer..."):
            result = ask_question(
                cik=cik,
                filing=selected_filing,
                question_text=question,
                company_label=company_label,
            )
        progress_text.success("Analysis complete. Review the answer, evidence, and diagnostics below.")

        render_analysis_overview(result)
        answer_tab, evidence_tab, diagnostics_tab = st.tabs(
            ["Answer", "Evidence & sources", "Diagnostics"]
        )

        with answer_tab:
            st.subheader("Answer")
            st.markdown(
                f"""
                <div class="answer-card">
                    {escape(str(result.get("answer") or "No answer generated."))}
                </div>
                """,
                unsafe_allow_html=True,
            )
            summary = result.get("summary_answer", "")
            if summary:
                st.subheader("Brief summary")
                st.markdown(
                    '<div class="section-note">A short preview of the generated summary answer.</div>',
                    unsafe_allow_html=True,
                )
                st.write(summary[:300] + ("..." if len(summary) > 300 else ""))

        with evidence_tab:
            st.subheader("Evidence & sources")
            st.markdown(
                '<div class="section-note">Grounded sentences or source chunks used to support the answer.</div>',
                unsafe_allow_html=True,
            )
            render_evidence(result)

        with diagnostics_tab:
            st.subheader("Retrieval diagnostics")
            show_retrieval_behavior(result)

    except Exception as exc:
        st.error(f"Failed to analyze filing: {exc}")
