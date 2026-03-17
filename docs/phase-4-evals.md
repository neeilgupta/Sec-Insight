# Phase 4 — Eval Harness

**Timeline:** Days 25-31  
**Goal:** A rigorous eval system that measures retrieval quality and answer
quality — and a README benchmark table that proves your system is better
than naive RAG.

This phase is what separates SEC Insight from every other RAG demo on GitHub.

---

## Learn before building

- [ ] What RAGAS measures — faithfulness, answer relevancy, context precision, context recall
- [ ] What LLM-as-a-judge means and why it works for open-ended answer quality
- [ ] How to design ground-truth Q&A pairs that test specific failure modes
- [ ] What a RAG benchmark table should show to be credible

---

## Build tasks

### 1. Ground-truth Q&A dataset
**File:** `evals/ground_truth.json`

Write 20+ question/answer pairs manually from real SEC filings.
This is intentional work — don't generate these with an LLM.

Categories to cover:
- **Prose queries** (5): "What are Apple's main risk factors?"
- **Numeric queries** (5): "What was Apple's total revenue in FY2024?"
- **Table queries** (5): "What was the YoY change in R&D spending?" (requires math across two rows)
- **Cross-section queries** (3): Questions that require combining info from two parts of the filing
- **Comparison queries** (2): Questions that compare Apple vs Microsoft on the same metric

Table and cross-section queries are where naive RAG fails. Document every failure.

```json
[
  {
    "id": "q001",
    "ticker": "AAPL",
    "filing": "10-K-2024",
    "question": "What was Apple's total net sales in fiscal year 2024?",
    "expected_answer": "$391.0 billion",
    "expected_source_section": "Consolidated Statements of Operations",
    "category": "numeric"
  }
]
```

---

### 2. RAGAS eval framework
**File:** `evals/ragas_eval.py`

```bash
pip install ragas
```

Four metrics RAGAS measures:
- **Faithfulness** — does the answer contradict the retrieved context?
- **Answer relevancy** — does the answer actually address the question?
- **Context precision** — are the retrieved chunks relevant to the question?
- **Context recall** — do the retrieved chunks contain the answer?

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision]
)
```

Run RAGAS against your ground truth dataset and record scores.

---

### 3. LLM-as-a-judge scoring (DIFFERENTIATOR)
**File:** `evals/llm_judge.py`

For each Q&A pair, ask GPT-4o to score the answer on a 1-5 scale with reasoning.

```python
JUDGE_PROMPT = """
You are evaluating a financial RAG system's answer quality.

Question: {question}
Expected answer: {expected}
System answer: {actual}
Source context provided: {context}

Score the system answer from 1-5 on:
1. Factual accuracy (does it match the expected answer?)
2. Faithfulness (is it grounded in the provided context?)
3. Completeness (does it fully address the question?)

Return JSON: {"accuracy": X, "faithfulness": X, "completeness": X, "reasoning": "..."}
"""
```

Aggregate scores across all 20+ questions. This is your headline eval number.

---

### 4. Benchmark comparison (DIFFERENTIATOR)
**File:** `evals/benchmark.py`

Run the same 20 questions through three system configurations:

| Configuration | Faithfulness | Answer Relevancy | Avg Latency | Cost/query |
|---|---|---|---|---|
| Naive RAG (fixed chunks, vector only) | ? | ? | ? | ? |
| Hybrid RAG (BM25 + vector + reranker) | ? | ? | ? | ? |
| Long-context (full 10-K in prompt) | ? | ? | ? | ? |

Also benchmark chunking strategies:
| Chunking Strategy | Context Precision | Context Recall |
|---|---|---|
| Fixed-size 512 tokens | ? | ? |
| Recursive 512 + overlap | ? | ? |
| Small-to-big 128/512 | ? | ? |

Fill in real numbers. This table goes in your README.

---

### 5. Failure analysis
**File:** `evals/failure_analysis.md`

For every question your system gets wrong, document:
- What went wrong (wrong chunk retrieved? LLM hallucinated? table parsing failed?)
- What you tried to fix it
- Whether the fix worked

This is gold in interviews. "Here's a failure mode I found and here's how I debugged it"
is exactly the story top labs want to hear.

---

## Validation checklist before Phase 5

- [ ] 20+ ground-truth Q&A pairs covering all categories
- [ ] RAGAS scores computed for all three system configurations
- [ ] LLM-as-a-judge scores computed for all 20 questions
- [ ] Benchmark table filled in with real numbers
- [ ] At least 3 documented failure cases with attempted fixes
- [ ] Hybrid RAG measurably outperforms naive RAG on at least context precision

---

## Check-in with Claude chat after this phase

Explain out loud:
1. Which of your 20 questions was hardest for the system and why
2. Where faithfulness broke down (if it did) — what caused hallucination?
3. What the latency/cost tradeoff looks like between RAG and long-context
4. One surprising finding from the benchmark

---

## Resume bullet (fill in your actual numbers)
"Designed RAGAS eval harness with 20+ ground-truth pairs and LLM-as-a-judge
scoring; hybrid RAG achieved [X]% higher faithfulness than naive baseline;
benchmarked retrieval strategies and embedding models in published README table."
