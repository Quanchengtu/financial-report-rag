# Financial Report RAG Assistant

A backend-first Retrieval-Augmented Generation (RAG) project for analyzing U.S. public company financial reports from SEC EDGAR filings. The current implementation focuses on building a solid retrieval pipeline over 10-K and 10-Q filings: fetching filings from SEC, cleaning HTML, chunking text, detecting important sections, and returning the most relevant passages for a user question.

## Overview

Large language models are good at generating answers, but they should not be trusted to answer questions about a specific financial filing without first seeing the source document. This project uses a RAG-style pipeline so the system can retrieve relevant filing passages before answer generation.

Current scope:

* Query SEC company information by CIK
* Retrieve recent 10-K / 10-Q filings
* Build filing document URLs from SEC metadata
* Download and clean filing HTML into text
* Chunk long filing text into smaller passages
* Apply rule-based retrieval to find the most relevant chunks for a question
* Return matched chunks with metadata for debugging and future citation support

## Current Status

This repository currently provides a working **backend retrieval pipeline**.

Implemented:

* FastAPI backend structure with routers, services, schemas, and config
* SEC EDGAR integration for company submissions and recent filings
* Filing HTML download and text extraction
* Filing text chunking with overlap-aware splitting
* Basic section-aware retrieval for filing questions
* Question-to-section routing for common filing topics such as risk factors and MD&A

Planned / not yet implemented:

* Embedding-based retrieval
* Vector database integration
* LLM answer generation
* Final citation-formatted answers
* Frontend UI
* User-uploaded filings

## Key Features

### 1. SEC EDGAR integration

The backend can fetch company submissions and recent filings directly from SEC EDGAR using a normalized 10-digit CIK.

### 2. Filing parsing and text cleaning

Filing HTML is converted into cleaner plain text by removing scripts, styles, common XBRL/iXBRL tags, and noisy lines.

### 3. Smarter chunking

Instead of hard-cutting text every fixed number of characters, the chunker:

* splits by paragraph first
* merges shorter paragraphs when possible
* splits long paragraphs at more natural boundaries
* keeps overlap to preserve local context

### 4. Section-aware retrieval

The retriever tries to detect important filing sections such as:

* Item 1. Business
* Item 1A. Risk Factors
* Item 3. Legal Proceedings
* Item 7. Management’s Discussion and Analysis
* Item 7A. Market Risk

If a question clearly points to one of these sections, retrieval prioritizes that section before falling back to full-document retrieval.

### 5. Retrieval metadata

Retrieved chunks include metadata such as:

* `chunk_index`
* `section_name`
* `score`
* `matched_terms`

This improves transparency, debugging, and future support for citations and vector database storage.

## Project Structure

```text
backend/
├── app/
│   ├── core/
│   │   └── config.py
│   ├── routers/
│   │   ├── company.py
│   │   ├── filing.py
│   │   └── rag.py
│   ├── schemas/
│   │   └── sec.py
│   ├── services/
│   │   ├── html_parser.py
│   │   ├── retriever.py
│   │   ├── sec_client.py
│   │   ├── section_parser.py
│   │   └── text_chunker.py
│   └── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Architecture

```text
User Question
    │
    ▼
FastAPI Endpoint (/rag/retrieve)
    │
    ├─► SEC filing URL construction
    ├─► Filing HTML download
    ├─► HTML → cleaned text
    ├─► Section detection
    ├─► Chunk generation
    ├─► Chunk scoring / ranking
    ▼
Top-K relevant chunks
```

## Retrieval Pipeline

The current retrieval flow is:

1. Receive `cik`, `accession_number`, `primary_document`, and `question`
2. Normalize the CIK and construct SEC filing URLs
3. Download the filing HTML from SEC
4. Clean the HTML into plain text
5. Detect known filing sections
6. Infer which sections are most relevant for the question
7. Chunk the selected text into manageable passages
8. Score each chunk using token overlap, phrase match, and section bonus
9. Return the top-k matched chunks

This is currently a **rule-based retriever**, not an embedding retriever yet.

## Tech Stack

* **Language:** Python
* **Framework:** FastAPI
* **Validation:** Pydantic
* **HTTP Client:** requests
* **HTML Parsing:** BeautifulSoup4
* **Environment Management:** python-dotenv
* **Server:** Uvicorn

## Requirements

Dependencies currently listed in `requirements.txt`:

* fastapi
* uvicorn
* requests
* python-dotenv
* pydantic
* beautifulsoup4

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Quanchengtu/financial-report-rag.git
cd financial-report-rag/backend
```

### 2. Create and activate a virtual environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install -r backend/requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
SEC_USER_AGENT=Your Name; your_email@example.com
```

Why this is required:

* SEC requests a descriptive `User-Agent` for API access
* this project reads the value from `app/core/config.py`

### 5. Run the backend server

```bash
cd backend
uvicorn main:app --reload
```

Default local server:

```text
http://127.0.0.1:8000
```

Interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

### Health check

**GET** `/`

Returns a simple message confirming that the backend is running.

### Get company information

**GET** `/company/{cik}`

Example:

```bash
curl "http://127.0.0.1:8000/company/320193"
```

### Get recent filings

**GET** `/company/{cik}/filings`

Returns recent 10-K and 10-Q filings with filing detail URL and filing document URL.

Example:

```bash
curl "http://127.0.0.1:8000/company/1045810/filings"
```

### Inspect filing HTML / cleaned text / chunks

**GET** `/filing/html`

Query parameters:

* `cik`
* `accession_number`
* `primary_document`

Example:

```bash
curl "http://127.0.0.1:8000/filing/html?cik=1045810&accession_number=0001045810-24-000029&primary_document=nvda-20240128.htm"
```

### Retrieve relevant chunks for a question

**GET** `/rag/retrieve`

Query parameters:

* `cik`
* `accession_number`
* `primary_document`
* `question`
* `top_k` (default: 3)

Example:

```bash
curl "http://127.0.0.1:8000/rag/retrieve?cik=1045810&accession_number=0001045810-24-000029&primary_document=nvda-20240128.htm&question=What%20are%20the%20main%20risk%20factors%3F&top_k=3"
```

## Example Response Shape

Example retrieval response fields:

```json
{
  "cik": "0001045810",
  "accession_number": "0001045810-24-000029",
  "primary_document": "nvda-20240128.htm",
  "filing_document_url": "...",
  "question": "What are the main risk factors?",
  "text_length": 123456,
  "section_count": 5,
  "used_priority_sections": ["item_1a_risk_factors"],
  "chunk_count": 42,
  "matched_count": 3,
  "results": [
    {
      "chunk_index": 7,
      "section_name": "item_1a_risk_factors",
      "score": 14,
      "matched_terms": ["risk", "factors"],
      "text": "..."
    }
  ]
}
```

## Retrieval Logic Summary

The current retriever is intentionally simple and explainable.

Scoring signals include:

* token overlap between the question and chunk text
* full-query phrase match bonus
* section-based bonus when the chunk belongs to a likely relevant filing section
* small density bonus to favor chunks with stronger term concentration

This makes the current system easier to debug while the project is still in its retrieval-first stage.

## Limitations

Current limitations include:

* retrieval is still keyword / rule-based, not semantic
* no embedding model yet
* no vector database yet
* no answer generation layer yet
* section detection depends on known patterns and may not cover every filing layout
* multilingual querying is a target direction, but retrieval is currently optimized for English filing text

## Roadmap

### Near term

* improve retrieval quality and ranking robustness
* add embedding-based semantic retrieval
* compare rule-based vs embedding retrieval quality
* add answer generation on top of retrieved chunks
* support source-grounded answers with citations

### Mid term

* add vector database support
* support multiple companies and filing types through a UI
* add bilingual question answering workflow
* improve evaluation with test questions and expected evidence chunks

### Longer term

* allow user-uploaded reports
* support summarization workflows
* add production-oriented logging, caching, and observability

## Development Notes

This repository is currently organized in a service-oriented backend structure:

* `routers/` handles API endpoints
* `services/` contains SEC access, parsing, chunking, and retrieval logic
* `schemas/` defines response models
* `core/` stores configuration

This separation makes the project easier to maintain and extend as it grows toward a full RAG application.

## Suggested Demo Flow

A simple demo can follow this sequence:

1. Query a company by CIK
2. Get recent 10-K / 10-Q filings
3. Pick one filing
4. Call `/filing/html` to inspect cleaned text and chunks
5. Call `/rag/retrieve` with a financial question
6. Show the returned top-k evidence chunks
7. Later, add an LLM layer to generate a final answer from those chunks

## Contributing

This project is currently under active personal development. If you fork or extend it, keep changes focused, well-documented, and easy to test.

## License

No license has been added yet. If you plan to make this repository public for reuse, add an appropriate license file.
