# Failure Analysis

For each question where accuracy < 3 in the benchmark, document root cause and fix.

Fill this in after running the full benchmark:
```
python evals/benchmark.py --output evals/benchmark_results.json
```

Then look at `per_question` entries where `accuracy < 3`.

---

## Template

**Question ID:**
**Question:**
**Config:** naive / hybrid / longctx
**Scores:** accuracy=, faithfulness=, completeness=

**What went wrong:**

**Fix attempted:**

**Result:**

---

## Failure #1

*(fill in after running full benchmark)*

---

## Failure #2

*(fill in after running full benchmark)*

---

## Failure #3

*(fill in after running full benchmark)*
