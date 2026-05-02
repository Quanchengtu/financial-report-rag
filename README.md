# Financial Report RAG Assistant

A backend project for retrieving relevant information from U.S. public company SEC filings.

This project currently focuses on the core backend workflow: fetching filings from SEC EDGAR, extracting cleaner text from filing HTML, splitting long documents into chunks, and returning relevant passages for a user question.

## Current Scope

- Query company information by CIK
- Retrieve recent 10-K and 10-Q filings
- Build filing document URLs from SEC metadata
- Download filing HTML from SEC
- Extract cleaner plain text from filing HTML
- Split long filing text into chunks
- Retrieve relevant chunks for a user question

## Implemented Features

### 1. SEC EDGAR integration

The backend can retrieve company submissions and recent filings from SEC EDGAR using a normalized 10-digit CIK.

### 2. Filing HTML parsing

The project downloads filing HTML and converts it into cleaner plain text by removing unnecessary tags and common noisy content.

### 3. Text chunking

Long filing text is split into smaller chunks so retrieval can work on manageable passages instead of the full document at once.

### 4. Basic retrieval

The current retrieval flow returns relevant text chunks for a question based on filing content.

### 5. Section-aware parsing

The project includes basic section detection for common filing sections, such as Business, Risk Factors, Legal Proceedings, and MD&A, so retrieval can focus on more relevant parts of a filing when possible.

## Tech Stack

- **Language:** Python
- **Framework:** FastAPI
- **Validation:** Pydantic
- **HTTP Client:** requests
- **HTML Parsing:** BeautifulSoup4
- **Environment Management:** python-dotenv
- **Server:** Uvicorn

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
│   ├── scripts/
│   │   └── index_filing.py
│   └── services/
│       ├── __init__.py
│       ├── answer_service.py
│       ├── embedding_service.py
│       ├── html_parser.py
│       ├── hybrid_retrieval.py
│       ├── indexing_service.py
│       ├── retriever.py
│       ├── sec_client.py
│       ├── section_parser.py
│       ├── text_chunker.py
│       └── vector_store.py
├── chroma_db/
├── main.py
├── requirements.txt
├── .gitignore
└── README.md

```
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
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
SEC_USER_AGENT=Your Name; your_email@example.com
```


### 5. Run the backend server

```bash
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

### Company information

**GET** `/company/{cik}`

Example:

```bash
curl "http://127.0.0.1:8000/company/320193"
```

### Recent filings

**GET** `/company/{cik}/filings`

Returns recent 10-K and 10-Q filings with filing detail URL and filing document URL.

Example:

```bash
curl "http://127.0.0.1:8000/company/1045810/filings"
```

### Filing Preview
<!-- Inspect filing HTML / cleaned text / chunks -->
**GET** `/filing/html`

Query parameters:

* `cik`
* `accession_number`
* `primary_document`

Example:

```bash
curl "http://127.0.0.1:8000/filing/html?cik=1045810&accession_number=0001045810-24-000029&primary_document=nvda-20240128.htm"
```

### Chunk Retrieval
<!-- Retrieve relevant chunks for a question -->
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

## Project Notes

This project is currently focused on the backend side, especially SEC filing retrieval, text extraction, chunking, and basic retrieval testing.

The current version is intended for inspection and backend experimentation, so the main goal is to make the pipeline clear and easy to test.

## LLM Configuration (Phase 1)

The project now includes an `llm_service.py` abstraction for chat-completions-compatible APIs.

Add the following optional settings to `backend/.env` when enabling LLM answer generation:

```env
LLM_API_KEY=<your_api_key>
LLM_MODEL_NAME=gpt-4.1-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_TIMEOUT_SECONDS=30
```
