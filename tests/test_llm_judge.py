def test_llm_judge_importable():
    import importlib.util
    spec = importlib.util.spec_from_file_location("llm_judge", "evals/llm_judge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "judge_answer")
    assert hasattr(mod, "run_judge_eval")


def test_benchmark_importable():
    import importlib.util
    spec = importlib.util.spec_from_file_location("benchmark", "evals/benchmark.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run_benchmark")
