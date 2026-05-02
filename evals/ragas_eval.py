"""
RAGAS evaluation runner.

Usage:
    python evals/ragas_eval.py --limit 5
    python evals/ragas_eval.py --output results.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from statistics import mean

from datasets import Dataset
from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import ContextPrecision, Faithfulness

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.retrieval.hybrid_search import hybrid_search
from backend.retrieval.reranker import rerank


def _build_metrics() -> list:
    return [Faithfulness(), ContextPrecision()]


def _retrieve(question: str, collection: str) -> tuple[str, list[str]]:
    candidates = hybrid_search(question, collection, top_k=20)
    ranked = rerank(question, candidates, collection, top_k=8)
    chunks = [r["text"] for r in ranked]
    return "\n\n---\n\n".join(chunks), chunks


async def _generate(question: str, context: str) -> str:
    from openai import AsyncOpenAI
    resp = await AsyncOpenAI().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Answer using ONLY the excerpts below. Be concise.\n\n" + context},
            {"role": "user", "content": question},
        ],
    )
    return resp.choices[0].message.content


async def _collect_answers(data: list[dict]) -> tuple[list, list, list, list]:
    """Async part: retrieve + generate answers for each question."""
    questions, answers, contexts, references = [], [], [], []
    for item in data:
        print(f"  {item['id']}: {item['question'][:60]}...")
        context, chunks = _retrieve(item["question"], item["collection"])
        answer = await _generate(item["question"], context)
        questions.append(item["question"])
        answers.append(answer)
        contexts.append(chunks)
        references.append(item["expected_answer"])
    return questions, answers, contexts, references


def run_ragas_eval(limit: int | None = None) -> dict:
    """Collect answers asynchronously, then run RAGAS evaluation synchronously."""
    data = json.loads(Path("evals/ground_truth.json").read_text())
    if limit:
        data = data[:limit]

    questions, answers, contexts, references = asyncio.run(_collect_answers(data))

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": references,
    })
    result = evaluate(dataset, metrics=_build_metrics())
    return {
        "faithfulness": mean(result["faithfulness"]),
        "context_precision": mean(result["context_precision"]),
        "n_questions": len(questions),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print(f"Running RAGAS eval on {args.limit or 'all'} questions...")
    scores = run_ragas_eval(args.limit)

    print("\n=== RAGAS Results ===")
    for k, v in scores.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, (float, int)) else f"  {k}: {v}")

    if args.output:
        Path(args.output).write_text(json.dumps(scores, indent=2))
        print(f"\nSaved to {args.output}")
