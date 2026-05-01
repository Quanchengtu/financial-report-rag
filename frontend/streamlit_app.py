import os
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

COMPANY_OPTIONS = {
    "NVIDIA (NVDA)": "1045810",
    "Apple (AAPL)": "320193",
    "Microsoft (MSFT)": "789019",
}

st.set_page_config(page_title="Financial Report RAG Demo", page_icon="📊", layout="wide")
st.title("📊 Financial Report Q&A Demo")
st.caption("Select company + filing type, ask in Chinese or English, and review grounded evidence chunks.")

with st.sidebar:
    st.header("Settings")
    top_k = st.slider("Top-k evidence", min_value=1, max_value=8, value=4)
    max_sentences = st.slider("Answer sentence limit", min_value=1, max_value=8, value=4)

company_label = st.selectbox("Company", list(COMPANY_OPTIONS.keys()))
form_type = st.radio("Filing Type", options=["10-K", "10-Q"], horizontal=True)
question = st.text_area("Your Question (中文 / English)", placeholder="e.g., What are the major risk factors?")


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
    }
    resp = requests.get(f"{API_BASE_URL}/rag/answer", params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


if st.button("Load Filings"):
    try:
        cik = COMPANY_OPTIONS[company_label]
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
                st.write(result.get("answer", "No answer generated."))

                st.subheader("Summary")
                summary = result.get("answer", "")
                st.write(summary[:300] + ("..." if len(summary) > 300 else ""))

                st.subheader("Evidence")
                supporting_sentences = result.get("supporting_sentences", [])
                if not supporting_sentences:
                    st.info("No supporting sentences were returned.")
                else:
                    for idx, item in enumerate(supporting_sentences, start=1):
                        with st.expander(f"Evidence #{idx} | section: {item.get('section_name') or 'N/A'}"):
                            st.write(item.get("sentence", ""))
                            st.caption(
                                f"chunk_index={item.get('chunk_index')} | chunk_rank={item.get('chunk_rank')} | sentence_score={item.get('sentence_score')}"
                            )

            except Exception as exc:
                st.error(f"Failed to analyze filing: {exc}")
else:
    st.info("Load filings first to continue.")
