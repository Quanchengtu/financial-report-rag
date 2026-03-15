# Financial Report RAG Assistant

A financial report RAG assistant built with FastAPI and React.

## Project Goal
This project aims to build a Retrieval-Augmented Generation (RAG) assistant for U.S. public company financial reports, starting with SEC EDGAR filings such as 10-K and 10-Q.

Users will be able to:
- select a company
- select a filing
- ask questions about the filing
- get answers with cited source passages

## Current Progress
Current backend progress includes:
- FastAPI project setup
- SEC EDGAR company submissions API integration
- company information endpoint
- recent filings endpoint for 10-K and 10-Q

## Tech Stack
- Backend: Python, FastAPI
- Frontend: React
- Data Source: SEC EDGAR
- Parsing: BeautifulSoup
- HTTP Client: requests

## Current Endpoints
- `GET /`
- `GET /company/{cik}`
- `GET /company/{cik}/filings`

## Example Company
- NVIDIA CIK: `0001045810`

## Next Steps
- build filing document URL from accession number and primary document
- fetch filing HTML
- parse and clean filing text
- chunk filing content
- add embedding and retrieval
- support question answering with citations

## Run Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload