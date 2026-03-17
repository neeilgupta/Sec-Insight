# Phase 5 — Deploy + Ship

**Timeline:** Days 32-40  
**Goal:** Live public URL, clean README with benchmark table, ready to put
on resume and show in interviews.

---

## Build tasks

### 1. Dockerize the backend
**File:** `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File:** `docker-compose.yml` (for local dev)
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data  # persist Chroma DB
    env_file: .env
```

Environment variables to handle:
- `OPENAI_API_KEY`
- `CHROMA_PERSIST_DIR`
- `CORS_ORIGINS` (Vercel frontend URL)

---

### 2. Deploy backend to Railway

Steps:
1. Push backend to GitHub
2. Connect Railway to the GitHub repo
3. Set environment variables in Railway dashboard
4. Railway auto-detects Dockerfile and deploys
5. Note the Railway URL (e.g. `https://sec-insight-backend.railway.app`)

Cost: ~$5/month on Railway Starter plan. Free tier available with limits.

---

### 3. Deploy frontend to Vercel

Steps:
1. Update `frontend/.env.production` with Railway backend URL
2. Push frontend to GitHub
3. Connect Vercel to the GitHub repo
4. Vercel auto-detects Vite config and deploys
5. Note the Vercel URL (e.g. `https://sec-insight.vercel.app`)

Cost: Free on Vercel Hobby plan.

---

### 4. README (make this good)
**File:** `README.md`

Structure:
```
# SEC Insight

One-line description + live demo link + screenshot

## What it does
2-3 sentences. Non-technical enough for a recruiter, specific enough for an engineer.

## Architecture
[Diagram showing: EDGAR → Parser → Chunker → Chroma | FastAPI → Vue]

## Technical highlights
- Table-aware parsing with Unstructured
- Hybrid search (BM25 + vector + cross-encoder reranker)
- Small-to-big retrieval
- Source highlighting in UI
- RAGAS eval harness

## Benchmark results
[Your benchmark table from Phase 4]

## Stack
Backend: FastAPI, Python, Chroma, OpenAI, Unstructured, sentence-transformers
Frontend: Vue 3, Vite, TypeScript
Deploy: Railway + Vercel + Docker

## Running locally
[Setup instructions]
```

The benchmark table and architecture diagram are what make this README stand out.
Ask Claude to generate an architecture diagram as an SVG or Mermaid diagram for the README.

---

### 5. Demo prep

Before putting this on your resume, verify:
- [ ] Live URL works from a fresh browser with no local setup
- [ ] Ticker input works for at least AAPL, MSFT, GOOGL
- [ ] Source highlighting visible and correct
- [ ] Comparison mode works
- [ ] Mobile layout acceptable
- [ ] Error states handled (invalid ticker, API timeout)

Record a 60-second screen recording demo. Upload to YouTube (unlisted) or
GitHub. Link it in the README. This is the first thing a recruiter or
interviewer will watch.

---

## Validation checklist

- [ ] Backend live on Railway with public URL
- [ ] Frontend live on Vercel with public URL
- [ ] End-to-end test: query AAPL 10-K from the live URL, get correct answer
- [ ] README has architecture diagram + benchmark table + demo link
- [ ] GitHub repo is public and clean (no API keys, no debug code)
- [ ] Demo recording uploaded and linked

---

## Check-in with Claude chat after this phase

This is your interview prep session. Come here and do a mock interview:
"I'm going to pretend I'm an Anthropic interviewer. Walk me through SEC Insight."

You should be able to explain:
1. The full architecture in 2 minutes
2. Why you chose hybrid search over pure vector search
3. One specific technical problem you hit and how you debugged it
4. What your eval numbers actually mean
5. What you would do differently or build next

---

## Resume bullet (final version — fill in your numbers)
"Built and deployed SEC Insight, a production RAG system for querying SEC
10-K/10-Q filings — implemented hybrid search (BM25 + vector + cross-encoder
reranking), table-aware PDF parsing, and RAGAS eval harness showing [X]%
faithfulness improvement over naive baseline; live at [URL]."
