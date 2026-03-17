# Phase 1 — Ingestion Pipeline

**Timeline:** Days 4-9  
**Goal:** A working pipeline that fetches a real SEC filing, parses it
(preserving tables), chunks it, embeds it, and stores it in Chroma.

---

## Learn before building

Before using Claude Code for any of these, talk through the concepts in chat:

- [ ] Chunking strategy tradeoffs — fixed-size vs recursive vs semantic
- [ ] Why chunk overlap prevents losing context at boundaries
- [ ] What Unstructured does differently from naive PDF text extraction
- [ ] How OpenAI's embedding API works (rate limits, dimensions, cost)

---

## Build tasks

### 1. SEC EDGAR fetcher
**File:** `backend/ingestion/edgar_fetcher.py`

Fetch the latest 10-K or 10-Q for a given ticker symbol using the EDGAR API.

Key endpoints:
- `https://data.sec.gov/submissions/CIK{cik}.json` — get company info + filings list
- `https://www.sec.gov/Archives/edgar/full-index/` — access raw filing documents

Steps:
1. Ticker → CIK lookup
2. Find most recent 10-K or 10-Q filing
3. Download the primary document (usually an HTML or PDF)

Do this manually first — fetch a real Apple 10-K and open it before writing any code.

---

### 2. Table-aware PDF parsing (DIFFERENTIATOR)
**File:** `backend/ingestion/parser.py`

Use `unstructured` library to parse the filing, preserving table structure.

```bash
pip install unstructured[pdf]
```

Key difference from naive extraction:
- `pdfplumber` or `PyPDF2` → mashes tables into unreadable text
- `Unstructured` → identifies table elements, preserves rows/columns

Test: after parsing, verify you can find a specific revenue figure from the
income statement by querying the parsed output.

**Validation checkpoint:** Can you query "What was Apple's total net sales in 2024?"
and get the correct number from the parsed document?

---

### 3. Recursive chunker with overlap
**File:** `backend/ingestion/chunker.py`

Write this yourself first without Claude Code.

```python
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    # your implementation
    pass
```

Then refactor with Claude Code. Understanding this from scratch matters.

Settings to start with:
- `chunk_size`: 512 tokens
- `overlap`: 50 tokens
- Split on: paragraphs first, then sentences, then words (recursive)

---

### 4. Small-to-big chunk indexing (DIFFERENTIATOR)
**File:** `backend/ingestion/indexer.py`

Two-level chunking strategy:
- **Child chunks** (small, ~128 tokens) — used for embedding + similarity search
- **Parent chunks** (large, ~512 tokens) — stored separately, fed to LLM

Data structure:
```python
{
  "child_chunk": "revenue was $89.5 billion",
  "parent_chunk": "Full paragraph with surrounding context...",
  "parent_id": "uuid",
  "source": "AAPL_10K_2024",
  "page": 42
}
```

When retrieval returns a child chunk, look up and return its parent.

---

### 5. Chroma vector store
**File:** `backend/ingestion/vector_store.py`

```bash
pip install chromadb openai
```

Steps:
1. Initialize Chroma client (local persistence)
2. Create a collection per company+filing (e.g. `AAPL_10K_2024`)
3. Embed child chunks with `text-embedding-3-small`
4. Store child chunks with parent chunk in metadata

---

## Validation checklist before Phase 2

- [ ] Fetcher successfully downloads a real AAPL 10-K
- [ ] Parser correctly identifies and preserves at least one table
- [ ] Chunker produces chunks of roughly the right size with overlap
- [ ] Small-to-big indexer stores both child + parent chunks
- [ ] Chroma collection created and queryable
- [ ] Manual spot-check: querying a known fact returns the right chunk

---

## Check-in with Claude chat after this phase

Explain out loud:
1. How your chunker decides where to split
2. Why you chose chunk_size=512 and overlap=50 (or whatever you picked)
3. What Unstructured found in the tables that plain extraction missed
4. How the small-to-big mapping is stored in Chroma metadata

---

## Resume bullet (fill in your actual numbers)
"Built ingestion pipeline with table-aware PDF parsing (Unstructured), small-to-big
chunk indexing, and OpenAI embeddings stored in Chroma — processing a full 10-K
filing in under [X] seconds."
