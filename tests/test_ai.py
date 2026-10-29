from termchat.ai import get_ai_config, query_llm


def test_get_ai_config_defaults():
    base_url, key, model = get_ai_config()
    assert isinstance(base_url, str)
    assert key is None or isinstance(key, str)
    assert isinstance(model, str)
    assert "kilo" in base_url.lower() or "kilo" in model.lower()


def test_query_llm_fallback():
    # Calling query_llm with invalid endpoint should return a friendly diagnostic error message, not crash
    ans = query_llm("test question", custom_url="http://127.0.0.1:59999", custom_key="invalid")
    assert isinstance(ans, str)
    assert len(ans) > 0
