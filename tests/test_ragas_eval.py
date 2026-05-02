import json
from pathlib import Path


def test_ground_truth_file_exists_and_valid():
    path = Path("evals/ground_truth.json")
    assert path.exists(), "evals/ground_truth.json must exist"
    data = json.loads(path.read_text())
    assert len(data) >= 20, f"Need at least 20 Q&A pairs, got {len(data)}"
    required = {"id", "ticker", "collection", "question", "expected_answer", "category"}
    for item in data:
        missing = required - item.keys()
        assert not missing, f"Item {item.get('id')} missing fields: {missing}"


def test_ground_truth_covers_all_categories():
    data = json.loads(Path("evals/ground_truth.json").read_text())
    categories = {item["category"] for item in data}
    expected = {"numeric", "prose", "table", "cross-section", "comparison"}
    assert expected <= categories, f"Missing categories: {expected - categories}"


def test_ragas_eval_has_run_function():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ragas_eval", "evals/ragas_eval.py")
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run_ragas_eval"), "ragas_eval.py must expose run_ragas_eval()"
    assert hasattr(mod, "_build_metrics"), "ragas_eval.py must expose _build_metrics()"
