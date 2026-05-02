"""
LLM-as-a-judge scorer.

Usage:
    python evals/llm_judge.py --limit 5
    python evals/llm_judge.py --output judge_results.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.retrieval.hybrid_search import hybrid_search
from backend.retrieval.reranker import rerank

_openai = AsyncOpenAI()

JUDGE_PROMPT = """\
You are evaluating a financial RAG system's answer quality.

Question: {question}
Expected answer: {expected}
System answer: {actual}
Source context (first 800 chars): {context}

Score 1-5 on each dimension:
- accuracy: Does it match the expected answer on key facts/figures?
- faithfulness: Is every claim grounded in the source context?
- completeness: Does it fully address the question?

Return ONLY valid JSON with no extra text:
{{"accuracy": <int 1-5>, "faithfulness": <int 1-5>, "completeness": <int 1-5>, "reasoning": "<one sentence>"}}
"""


async def judge_answer(question: str, expected: str, actual: str, context: str) -> dict:
    resp = await _openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=question,
            expected=expected,
            actual=actual,
            context=context[:800],
        )}],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


async def _generate(question: str, context: str) -> str:
    resp = await _openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Answer using ONLY the excerpts below. Be concise.\n\n" + context},
            {"role": "user", "content": question},
        ],
    )
    return resp.choices[0].message.content


async def run_judge_eval(limit: int | None = None) -> list[dict]:
    data = json.loads(Path("evals/ground_truth.json").read_text())
    if limit:
        data = data[:limit]

    results = []
    for item in data:
        print(f"  {item['id']}: {item['question'][:60]}...")
        candidates = hybrid_search(item["question"], item["collection"], top_k=20)
        ranked = rerank(item["question"], candidates, item["collection"], top_k=8)
        context = "\n\n---\n\n".join(r["text"] for r in ranked)
        actual = await _generate(item["question"], context)
        scores = await judge_answer(item["question"], item["expected_answer"], actual, context)
        results.append({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "expected": item["expected_answer"],
            "actual": actual,
            **scores,
        })
    return results


def _print_summary(results: list[dict]) -> None:
    avg = lambda key: sum(r[key] for r in results) / len(results)
    print(f"\n=== LLM Judge Results ({len(results)} questions) ===")
    print(f"  Avg accuracy:     {avg('accuracy'):.2f}/5")
    print(f"  Avg faithfulness: {avg('faithfulness'):.2f}/5")
    print(f"  Avg completeness: {avg('completeness'):.2f}/5")

    print("\nBy category:")
    for cat in ("numeric", "prose", "table", "cross-section", "comparison"):
        cat_results = [r for r in results if r["category"] == cat]
        if cat_results:
            cat_avg = sum(r["accuracy"] for r in cat_results) / len(cat_results)
            print(f"  {cat:<14}: acc={cat_avg:.1f}/5  ({len(cat_results)} questions)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print(f"Running LLM judge on {args.limit or 'all'} questions...")
    results = asyncio.run(run_judge_eval(args.limit))
    _print_summary(results)

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"\nSaved to {args.output}")
