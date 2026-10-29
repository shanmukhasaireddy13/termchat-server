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


def test_code_only_cleaning():
    from termchat.ai import is_code_only_request, clean_llm_response

    prompt = "write a python script, give me only python code no other text"
    assert is_code_only_request(prompt) is True

    # Simulate model that dumped thought process and conversational chatter before code
    raw_output = """<think>
    I need to write a script for the user.
    Let me think about the pins and setup.
    </think>
    Here is your python script:
    ```python
    import sys
    print("test code")
    ```
    I hope this helps!
    """

    cleaned = clean_llm_response(raw_output, is_code_only=True)
    assert "<think>" not in cleaned
    assert "Here is your python script" not in cleaned
    assert "I hope this helps" not in cleaned
    assert cleaned.startswith("```python")
    assert cleaned.endswith("```")
    assert 'print("test code")' in cleaned
