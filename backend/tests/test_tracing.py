import logging

from app.rag import tracing


def test_trace_function_uses_metadata_factory(monkeypatch):
    captured = {}

    def fake_trace_call(name, fn, *args, run_type, metadata, **kwargs):
        captured.update(name=name, run_type=run_type, metadata=metadata)
        return fn(*args, **kwargs)

    monkeypatch.setattr(tracing, "trace_call", fake_trace_call)

    @tracing.trace_function(
        "answer-question",
        metadata_factory=lambda value: {"value": value},
    )
    def decorated(value):
        return value.upper()

    assert decorated("hello") == "HELLO"
    assert captured == {
        "name": "answer-question",
        "run_type": "chain",
        "metadata": {"value": "hello"},
    }


def test_trace_function_shields_metadata_factory_exceptions(monkeypatch, caplog):
    captured = {}

    def fake_trace_call(name, fn, *args, run_type, metadata, **kwargs):
        captured["metadata"] = metadata
        return fn(*args, **kwargs)

    def failing_metadata_factory(value):
        raise KeyError(value)

    monkeypatch.setattr(tracing, "trace_call", fake_trace_call)

    @tracing.trace_function(
        "answer-question",
        metadata_factory=failing_metadata_factory,
    )
    def decorated(value):
        return value.upper()

    with caplog.at_level(logging.WARNING, logger=tracing.__name__):
        assert decorated("hello") == "HELLO"

    assert captured["metadata"] == {}
    assert "Metadata factory failed for trace 'answer-question'" in caplog.text
    assert "KeyError: 'hello'" in caplog.text
