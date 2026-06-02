# Chunking Evaluation Plan

## Goal
Find a reasonable chunk_size and overlap setting for financial report RAG.

## Settings to test
- chunk_size=500, overlap=50
- chunk_size=800, overlap=100
- chunk_size=1200, overlap=150

## Metrics
- Retrieval Recall: whether the correct evidence chunk appears in top-k results
- Answer Groundedness: whether the final answer is supported by retrieved chunks
- Chunk Readability: whether each chunk keeps enough context

## Testing Questions
1. [Revenue] What was the company’s revenue in 2026?
2. [Net Income] What was the company’s net income in 2026?
3. [Cash Flow] What was the company’s operating cash flow?
4. [Risk Factors] What are the main risk factors mentioned in the annual report?
5. [Debt / Borrowings] What does the annual report say about the company’s debt or borrowings?
6. [Research and Development Expenses] How much did the company spend on research and development?
7. [Gross Margin] What was the company’s gross margin?
8. [Business Overview / Business Segments] What are the company’s main business segments?
9. [Liquidity] What does the company say about liquidity?
10. [Future Outlook / Guidance] What does the company say about its future outlook or guidance?


