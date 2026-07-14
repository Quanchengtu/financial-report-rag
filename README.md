# Financial Report RAG Assistant

A backend-focused project for retrieving relevant information from U.S. public company SEC filings and answering questions with grounded evidence.

This project currently focuses on the core workflow: fetching filings from SEC EDGAR, extracting cleaner text from filing HTML, splitting long documents into chunks, indexing/retrieving relevant passages, and optionally generating LLM-backed answers.

Financial Report RAG Assistant 讓使用者能直接用一般問句查詢美國上市公司的年度與季度財報，如公司的「營運狀況」」「主要風險」與「財務表現」等相關問題。系統會自動取得並整理篇幅龐大的 SEC 財報，找出與問題最相關的內容，再產生清楚易讀的回答，同時附上原始財報段落，方便確認答案來源，降低 AI 回答缺乏依據的問題。
專案使用 FastAPI 建立後端服務，搭配 Streamlit 實作前端使用者介面，並支援 Docker 執行。目前已完成財報資料取得、文件清理、章節辨識、內容切分（chunking）、向量檢索（embedding）、相關段落搜尋及有依據的回答生成等核心流程。

## Current Scope

- Query company information by CIK
- Retrieve recent 10-K and 10-Q filings
- Build filing document URLs from SEC metadata
- Download filing HTML from SEC
- Extract cleaner plain text from filing HTML
- Split long filing text into chunks
- Retrieve relevant chunks for a user question
- Optionally index filings into a vector store for semantic retrieval
- Optionally generate grounded answers with an OpenAI-compatible LLM API
- Provide a lightweight Docker backend deployment path

## Implemented Features

### 1. SEC EDGAR integration

The backend can retrieve company submissions and recent filings from SEC EDGAR using a normalized 10-digit CIK.

### 2. Filing HTML parsing

The project downloads filing HTML and converts it into cleaner plain text by removing unnecessary tags and common noisy content.

### 3. Text chunking

Long filing text is split into smaller chunks so retrieval can work on manageable passages instead of the full document at once.

### 4. Rule-based retrieval

The basic retrieval flow returns relevant text chunks for a question based on filing content.

### 5. Section-aware parsing

The project includes basic section detection for common filing sections, such as Business, Risk Factors, Legal Proceedings, and MD&A, so retrieval can focus on more relevant parts of a filing when possible.

### 6. Semantic and hybrid retrieval

The project includes vector indexing and semantic retrieval support. Hybrid answer generation can combine indexed semantic results with rule-based fallback behavior.

### 7. Grounded answer generation

The answer endpoints can produce grounded answers from retrieved filing chunks. When LLM generation is enabled and configured, the backend can use an OpenAI-compatible API; otherwise, it can fall back to extractive grounded answers.

## Tech Stack

- **Language:** Python
- **Framework:** FastAPI
- **Validation:** Pydantic
- **HTTP Client:** requests
- **HTML Parsing:** BeautifulSoup4
- **Environment Management:** python-dotenv
- **Server:** Uvicorn
- **Demo UI:** Streamlit
- **Optional Vector Store:** ChromaDB
- **Optional Embeddings:** sentence-transformers
- **Optional LLM:** OpenAI-compatible chat completions API

## Project Structure

```text
financial-report-rag/
├── README.md
├── .gitignore
├── chunking_eval.md
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── main.py
│   ├── requirements.txt         # lightweight dependencies
│   ├── requirements-full.txt    # optional full RAG dependencies
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── routers/
│   │   │   ├── company.py
│   │   │   ├── filing.py
│   │   │   └── rag.py
│   │   ├── schemas/
│   │   │   └── sec.py
│   │   ├── scripts/
│   │   │   └── index_filing.py
│   │   └── services/
│   │       ├── answer_service.py
│   │       ├── embedding_service.py
│   │       ├── html_parser.py
│   │       ├── hybrid_retrieval.py
│   │       ├── indexing_service.py
│   │       ├── llm_service.py
│   │       ├── retriever.py
│   │       ├── sec_client.py
│   │       ├── section_parser.py
│   │       ├── text_chunker.py
│   │       └── vector_store.py
│   └── tests/
└── frontend/
    └── streamlit_app.py
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

The default dependency set is intended to stay relatively lightweight. Some advanced semantic retrieval features may require optional packages such as `chromadb` and `sentence-transformers` if they are not enabled in your local requirements file.

### 4. Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
SEC_USER_AGENT=Your Name; your_email@example.com

# Optional vector store / embeddings
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=financial_filings

# Optional LLM answer generation
RAG_LLM_ENABLED=true
LLM_MODEL_NAME=gpt-4.1-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_API_TIMEOUT_SECONDS=30
RAG_LLM_TEMPERATURE=0.2
RAG_LLM_MAX_CONTEXT_CHUNKS=5
RAG_LLM_MAX_CHARS_PER_CHUNK=1200
```

`SEC_USER_AGENT` is important for SEC EDGAR requests. LLM-related variables are only required if you want LLM-generated grounded answers.

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

## Docker Deployment

The backend includes a lightweight Dockerfile under `backend/Dockerfile`. The image installs `backend/requirements.txt` only, so it is intended for lightweight API/server testing and does **not** include heavier optional full-RAG dependencies such as `chromadb`, `torch`, or `sentence-transformers`.

From the repository root:

```bash
docker build -t financial-report-rag-backend ./backend
```

Run the backend container:

```bash
docker run --rm -p 8000:8000 --env-file backend/.env financial-report-rag-backend
```

If you build a custom full-dependency image and want to persist local ChromaDB/vector-store data, mount a volume:

```bash
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  -v "$(pwd)/backend/chroma_db:/app/chroma_db" \
  financial-report-rag-backend
```

The `.dockerignore` file excludes local environment files, virtual environments, Git metadata, and local vector-store data from the image. To run the full semantic retrieval stack in Docker, update the image to install `requirements-full.txt` and account for the larger build/runtime footprint.

## Streamlit Demo UI

A simple Streamlit demo is available in `frontend/streamlit_app.py`.

Start the backend first, then from the repository root run:

```bash
streamlit run frontend/streamlit_app.py
```

If your backend is not running on the default URL, set `API_BASE_URL`:

```bash
API_BASE_URL=http://127.0.0.1:8000 streamlit run frontend/streamlit_app.py
```

The demo lets you select a company, choose a filing type, ask a question, and inspect the answer with supporting evidence.

## API Endpoints

### Health check

**GET** `/`

Returns a simple message confirming that the backend is running.

### LLM health check

**GET** `/health/llm`

Checks whether LLM answer generation is enabled and whether required LLM configuration is present.

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

### Filing preview

**GET** `/filing/html`

Query parameters:

- `cik`
- `accession_number`
- `primary_document`

Example:

```bash
curl "http://127.0.0.1:8000/filing/html?cik=1045810&accession_number=0001045810-24-000029&primary_document=nvda-20240128.htm"
```

### Rule-based chunk retrieval

**GET** `/rag/retrieve`

Query parameters:

- `cik`
- `accession_number`
- `primary_document`
- `question`
- `top_k` (default: 3)

Example:

```bash
curl "http://127.0.0.1:8000/rag/retrieve?cik=1045810&accession_number=0001045810-24-000029&primary_document=nvda-20240128.htm&question=What%20are%20the%20main%20risk%20factors%3F&top_k=3"
```

### Index filing for semantic retrieval

**POST** `/rag/index`

Indexes a filing into the vector store when semantic or hybrid retrieval is needed.

Common query parameters:

- `cik`
- `accession_number`
- `primary_document`
- `ticker` (optional)
- `form_type` (optional)
- `filing_date` (optional)
- `force_reindex` (default: false)

### Filing index status

**GET** `/rag/index-status`

Checks whether a filing has already been indexed.

### Semantic retrieval

**GET** `/rag/semantic-retrieve`

Retrieves similar chunks from the vector store using embeddings. Optional filters include `cik`, `ticker`, and `form_type`.

### Grounded answer

**GET** `/rag/answer`

Builds an answer from retrieved filing chunks. It can use LLM generation when enabled or fall back to extractive grounded answers.

### Hybrid answer

**GET** `/rag/hybrid-answer`

Combines indexing, hybrid retrieval, and grounded answer generation. This is the main endpoint used by the Streamlit demo.

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

## LLM Configuration

LLM generation is optional. If `RAG_LLM_ENABLED=true` and the LLM settings are valid, answer endpoints can generate a grounded answer with an OpenAI-compatible API.

Use this endpoint to inspect LLM readiness without exposing secrets:

```bash
curl "http://127.0.0.1:8000/health/llm"
```

If LLM generation is disabled or not configured, the answer flow can still use non-LLM grounded fallback behavior.

## Testing

From the `backend/` directory:

```bash
python -m pytest
```

Current tests cover answer generation helpers, indexing behavior, retrieval behavior, and text chunking.

## Project Notes

This project is focused on backend experimentation for SEC filing retrieval, text extraction, chunking, retrieval, and grounded financial-report Q&A.

The lightweight setup is suitable for local API testing and Docker deployment. Semantic retrieval and LLM-backed answers are optional extensions that may require extra dependencies and API credentials.The lightweight setup is suitable for local API testing and lightweight Docker deployment. Full semantic retrieval and LLM-backed answers are optional extensions that may require `requirements-full.txt`, extra runtime resources, and API credentials.
