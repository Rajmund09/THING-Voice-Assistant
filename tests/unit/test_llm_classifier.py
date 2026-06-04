import pytest
from unittest.mock import MagicMock, patch
from backend.engine.llm_intent_classifier import classify_intent_llm


@patch("backend.engine.llm_intent_classifier._client")
def test_llm_classification_success(mock_client):
    """Tests successful LLM classification and normalization."""
    # Mock the Groq response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"intent": "play_youtube", "entities": {"query": "smooth jazz"}, "confidence": 0.95}'
    mock_client.chat.completions.create.return_value = mock_response

    # Mock memory to avoid file IO
    with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=[]):
        result = classify_intent_llm("put on some smooth jazz")

    assert result is not None
    assert result["action"] == "play_youtube"
    assert result["query"] == "smooth jazz"
    assert result["_source"] == "llm"


@patch("backend.engine.llm_intent_classifier._client")
def test_llm_multi_step_classification(mock_client):
    """Tests multi-step command classification."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '''
    {
        "intent": "multi_step",
        "multi_step": [
            {"intent": "open_app", "entities": {"app_name": "chrome"}},
            {"intent": "open_url", "entities": {"url": "google.com"}}
        ],
        "confidence": 0.98
    }
    '''
    mock_client.chat.completions.create.return_value = mock_response

    with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=[]):
        result = classify_intent_llm("open chrome and go to google")

    assert result is not None
    assert result["action"] == "multi_step"
    assert len(result["steps"]) == 2
    assert result["steps"][0]["action"] == "open_app"
    assert result["steps"][1]["action"] == "open_url"


@patch("backend.engine.llm_intent_classifier._client")
def test_llm_low_confidence_fallback(mock_client):
    """Tests that low confidence results are rejected."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"intent": "open_app", "entities": {"app_name": "unknown"}, "confidence": 0.3}'
    mock_client.chat.completions.create.return_value = mock_response

    with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=[]):
        result = classify_intent_llm("do something weird")

    assert result is None


# ── New Tests ─────────────────────────────────────────────────────────────────

@patch("backend.engine.llm_intent_classifier._client")
def test_llm_pronoun_resolution_via_context(mock_client):
    """
    Tests that pronoun resolution works when history is injected into context.
    The LLM should receive context that allows it to resolve 'him' → 'raj'.
    We verify the classifier passes history through and returns a valid intent.
    """
    mock_response = MagicMock()
    # Simulate the LLM resolving 'him' to 'raj' from context
    mock_response.choices[0].message.content = (
        '{"intent": "send_whatsapp", '
        '"entities": {"contact_name": "raj", "message": "hello"}, '
        '"confidence": 0.91}'
    )
    mock_client.chat.completions.create.return_value = mock_response

    fake_history = [
        {"speaker": "user",      "text": "message raj hello"},
        {"speaker": "assistant", "text": "Message sent to raj."},
    ]
    with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=fake_history):
        result = classify_intent_llm("send it to him")

    assert result is not None
    assert result["action"] == "send_whatsapp"
    # The mock resolved 'him' → 'raj'; verify entity passed through
    assert result["contact_name"] == "raj"
    # Confirm the Groq call received the history context in its prompt
    call_args = mock_client.chat.completions.create.call_args
    user_message_content = call_args[1]["messages"][1]["content"]
    assert "raj" in user_message_content.lower()


@patch("backend.engine.llm_intent_classifier._client")
def test_llm_json_parse_error_recovery(mock_client):
    """
    Tests that the classifier gracefully recovers when the LLM wraps its
    JSON response in markdown code fences (a common model behaviour).
    The parser must strip fences and still extract a valid result.
    """
    mock_response = MagicMock()
    # Simulate an LLM that wraps output in ```json ... ```
    mock_response.choices[0].message.content = (
        "```json\n"
        '{"intent": "get_time", "entities": {}, "confidence": 0.99}\n'
        "```"
    )
    mock_client.chat.completions.create.return_value = mock_response

    with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=[]):
        result = classify_intent_llm("what time is it")

    # The parser uses start/end brace extraction — should recover the JSON
    assert result is not None
    assert result["action"] == "get_time"


@patch("backend.engine.llm_intent_classifier._client")
def test_llm_transient_error_triggers_one_retry(mock_client):
    """
    Tests the 1-retry logic: if the first Groq call raises a 503 error,
    the classifier should retry exactly once and succeed.
    """
    # First call raises a 503-style error; second call succeeds
    success_response = MagicMock()
    success_response.choices[0].message.content = (
        '{"intent": "get_date", "entities": {}, "confidence": 0.88}'
    )
    mock_client.chat.completions.create.side_effect = [
        Exception("503 Service Unavailable"),
        success_response,
    ]

    with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=[]):
        result = classify_intent_llm("what day is it")

    # Should have retried and returned the successful second call
    assert result is not None
    assert result["action"] == "get_date"
    assert result.get("_retried") is True
    assert mock_client.chat.completions.create.call_count == 2
