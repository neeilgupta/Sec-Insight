"""
Benchmark three retrieval configurations against ground truth.

Configs:
  naive   — vector-only, no BM25, no reranker
  hybrid  — BM25 + vector + RRF + cross-encoder (current system)
  longctx — full collection text stuffed into prompt (no retrieval)

Usage:
    python evals/benchmark.py --limit 5
    python evals/benchmark.py --output benchmark_results.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.retrieval.hybrid_search import hybrid_search
from backend.retrieval.reranker import rerank
from evals.llm_judge import judge_answer

_openai = AsyncOpenAI()
CHROMA_PATH = "./chroma_db"


def _naive_retrieve(question: str, collection_name: str, top_k: int = 8) -> list[str]:
    """Vector-only retrieval — no BM25, no reranker."""
    embedding = OpenAI().embeddings.create(
        model="text-embedding-3-small", input=question
    ).data[0].embedding
    db = chromadb.PersistentClient(path=CHROMA_PATH)
    col = db.get_collection(collection_name)
    results = col.query(query_embeddings=[embedding], n_results=top_k)
    return results["documents"][0]


def _longctx_retrieve(collection_name: str, max_chars: int = 60_000) -> str:
    """Return raw text from collection up to max_chars (~15k tokens)."""
    db = chromadb.PersistentClient(path=CHROMA_PATH)
    col = db.get_collection(collection_name)
    docs = col.get(limit=200)
    return "\n\n".join(docs["documents"])[:max_chars]


async def _generate(question: str, context: str) -> tuple[str, float]:
    """Returns (answer, latency_seconds)."""
    t0 = time.perf_counter()
    resp = await _openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Answer using ONLY the excerpts below. Be concise.\n\n" + context},
            {"role": "user", "content": question},
        ],
    )
    return resp.choices[0].message.content, time.perf_counter() - t0


async def _eval_config(config: str, item: dict) -> dict:
    question, collection = item["question"], item["collection"]
    t0 = time.perf_counter()

    if config == "naive":
        chunks = _naive_retrieve(question, collection)
        context = "\n\n---\n\n".join(chunks)
    elif config == "hybrid":
        candidates = hybrid_search(question, collection, top_k=20)
        ranked = rerank(question, candidates, collection, top_k=8)
        context = "\n\n---\n\n".join(r["text"] for r in ranked)
    else:  # longctx
        context = _longctx_retrieve(collection)

    retrieval_ms = (time.perf_counter() - t0) * 1000
    answer, llm_secs = await _generate(question, context)
    scores = await judge_answer(question, item["expected_answer"], answer, context)

    return {
        "id": item["id"],
        "config": config,
        "category": item["category"],
        "retrieval_ms": round(retrieval_ms),
        "llm_secs": round(llm_secs, 2),
        "total_secs": round(retrieval_ms / 1000 + llm_secs, 2),
        "context_chars": len(context),
        **scores,
    }


async def _collect_results(data: list[dict]) -> list[dict]:
    all_results = []
    for item in data:
        print(f"  {item['id']}...")
        for config in ("naive", "hybrid", "longctx"):
            all_results.append(await _eval_config(config, item))
    return all_results


def run_benchmark(limit: int | None = None) -> dict:
    data = json.loads(Path("evals/ground_truth.json").read_text())
    if limit:
        data = data[:limit]

    all_results = asyncio.run(_collect_results(data))

    summary = {}
    for config in ("naive", "hybrid", "longctx"):
        cr = [r for r in all_results if r["config"] == config]
        avg = lambda k, cr=cr: sum(r[k] for r in cr) / len(cr)
        summary[config] = {
            "avg_accuracy": round(avg("accuracy"), 2),
            "avg_faithfulness": round(avg("faithfulness"), 2),
            "avg_completeness": round(avg("completeness"), 2),
            "avg_latency_secs": round(avg("total_secs"), 2),
            "avg_context_chars": round(avg("context_chars")),
        }
    return {"summary": summary, "per_question": all_results}


def _print_table(summary: dict) -> None:
    print(f"\n{'Config':<12} {'Accuracy':>10} {'Faithful':>10} {'Complete':>10} {'Latency(s)':>12}")
    print("-" * 58)
    for config, s in summary.items():
        print(
            f"{config:<12} {s['avg_accuracy']:>10.2f} {s['avg_faithfulness']:>10.2f} "
            f"{s['avg_completeness']:>10.2f} {s['avg_latency_secs']:>12.2f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print(f"Running benchmark on {args.limit or 'all'} questions × 3 configs...")
    results = run_benchmark(args.limit)
    _print_table(results["summary"])

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"\nSaved to {args.output}")
