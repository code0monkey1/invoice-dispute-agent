"""An empty model setting (an unset CI variable arrives as "") falls back to the default model."""
import importlib


def test_empty_groq_model_falls_back_to_the_default(monkeypatch):
    import src.agent as agent_module
    monkeypatch.setenv("GROQ_MODEL", "")
    try:
        reloaded = importlib.reload(agent_module)
        assert reloaded.GROQ_MODEL == "openai/gpt-oss-120b"
    finally:
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        importlib.reload(agent_module)


def test_empty_judge_model_falls_back_to_the_default(monkeypatch):
    from evals.run import DEFAULT_JUDGE_MODEL, judge_model_name
    monkeypatch.setenv("EVAL_JUDGE_MODEL", "")
    assert judge_model_name(None) == DEFAULT_JUDGE_MODEL
    assert judge_model_name("other") == "other"
