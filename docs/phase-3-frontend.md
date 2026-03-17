# Phase 3 — Frontend + Source Highlighting

**Timeline:** Days 17-24  
**Goal:** A clean, deployed-quality Vue 3 UI with streaming chat, source
highlighting, and two-company comparison mode.

---

## Learn before building

- [ ] How Server-Sent Events (SSE) work — EventSource API in the browser
- [ ] How to display streaming tokens in Vue as they arrive
- [ ] How to pass source chunk metadata back from the API for highlighting
- [ ] Instructor/Pydantic structured output — how to enforce JSON schema on LLM output

---

## Build tasks

### 1. Vue 3 chat UI
**Directory:** `frontend/src/`

Stack: Vue 3 + Vite + TypeScript

Core components:
- `TickerInput.vue` — stock ticker input + submit
- `ChatWindow.vue` — conversation history display
- `MessageBubble.vue` — individual message with source citation link
- `StreamingResponse.vue` — token-by-token display as SSE arrives

SSE in Vue:
```typescript
const source = new EventSource(`/api/query?session=${sessionId}`)
source.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'token') appendToken(data.content)
  if (data.type === 'sources') setSources(data.chunks)
}
```

---

### 2. Source highlighting + citations panel (DIFFERENTIATOR)
**Component:** `SourcePanel.vue`

This is the interpretability feature — critical for Anthropic specifically.

When the LLM finishes responding:
- Right panel shows the source passages used
- Each passage is highlighted/bordered
- Clicking a citation scrolls to and highlights the relevant passage
- Show: company name, filing type, section name, page number

The backend already returns source metadata in SSE events. The frontend
just needs to render it cleanly.

Design:
```
[Chat window - left 60%] | [Sources panel - right 40%]
                          | > Apple 10-K 2024, p.42
                          | > Risk Factors section
                          | "Revenue from iPhone..."
                          |
                          | > Apple 10-K 2024, p.67
                          | "International operations..."
```

---

### 3. Two-company comparison mode
**Component:** `ComparisonView.vue`

Side-by-side layout:
- Two ticker inputs at top
- Both companies queried simultaneously with the same question
- Responses stream in parallel, displayed side by side
- Sources panel shows citations from both companies, color-coded

Implementation: fire two simultaneous SSE connections, render in parallel columns.

---

### 4. Structured JSON output (Instructor)
**Backend file:** `backend/api/structured.py`

For queries like "What was Apple's revenue?" — return structured data instead
of prose so the frontend can render it as a formatted number card.

```bash
pip install instructor
```

```python
from pydantic import BaseModel
import instructor

class FinancialFigure(BaseModel):
    metric: str
    value: float
    unit: str  # "billions USD"
    period: str  # "FY2024"
    source_section: str

client = instructor.patch(openai.OpenAI())
```

Frontend renders this as a metric card rather than prose when the response
is a structured financial figure.

---

## Validation checklist before Phase 4

- [ ] Ticker input fetches and indexes a filing on submit
- [ ] Chat streams tokens correctly, no flickering
- [ ] Source panel appears after each response with correct citations
- [ ] Clicking a citation highlights the passage
- [ ] Comparison mode streams two companies in parallel
- [ ] Structured output renders as a metric card for financial figure queries
- [ ] Works on mobile (basic responsive layout)

---

## Check-in with Claude chat after this phase

Explain out loud:
1. How SSE differs from WebSockets and why you chose it
2. How source metadata flows from the retrieval step to the frontend highlight
3. One UX decision you made and why (layout, interaction, error state)

---

## Notes
You have Vue experience from J&J and LyftLogic — lean on it. The new concepts
here are SSE streaming and the source highlighting architecture. Spend your
learning time there, not on basic Vue patterns.
