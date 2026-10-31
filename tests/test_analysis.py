import json

import requests

from veritylens.analysis import analyze_with_llm
from veritylens.models import Source


class FakeResponse:
    status_code = 200

    def __init__(self, content):
        self.content = json.dumps({"choices": [{"message": {"content": json.dumps(content)}}]}).encode()

    def iter_content(self, chunk_size):
        yield self.content

    def close(self):
        pass


def test_missing_api_key_uses_explicit_deterministic_fallback(monkeypatch):
    monkeypatch.delenv("VERITYLENS_LLM_API_KEY", raising=False)
    result = analyze_with_llm("What is established?", [Source("S1", "Notice", "Eligibility: enrolled students.")])
    assert result.mode == "deterministic_fallback"
    assert "No API key" in result.error_message
    assert not result.insights


def test_ai_insight_requires_verbatim_source_citation(monkeypatch):
    monkeypatch.setenv("VERITYLENS_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "veritylens.analysis.requests.post",
        lambda *_args, **_kwargs: FakeResponse({
            "summary": "Eligibility is stated in one source.",
            "insights": [{
                "category": "key_claim",
                "statement": "Applicants must be enrolled.",
                "evidence_type": "direct evidence",
                "explanation": "A direct passage states this.",
                "citations": [{"source_id": "S1", "quote": "Eligibility: enrolled students."}],
            }],
        }),
    )

    result = analyze_with_llm(
        "Who is eligible?", [Source("S1", "Notice", "Eligibility: enrolled students.")],
    )
    assert result.mode == "ai_assisted"
    assert result.insights[0].citations[0].quote == "Eligibility: enrolled students."


def test_invalid_ai_citation_falls_back_instead_of_showing_claim(monkeypatch):
    monkeypatch.setenv("VERITYLENS_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "veritylens.analysis.requests.post",
        lambda *_args, **_kwargs: FakeResponse({
            "summary": "A claim.",
            "insights": [{
                "category": "key_claim",
                "statement": "Invented claim.",
                "evidence_type": "direct evidence",
                "explanation": "",
                "citations": [{"source_id": "S1", "quote": "Not in the evidence."}],
            }],
        }),
    )

    result = analyze_with_llm("Question", [Source("S1", "Notice", "Original source text.")])
    assert result.mode == "deterministic_fallback"
    assert "did not match collected source text" in result.error_message
    assert not result.insights


def test_provider_timeout_is_visible_and_uses_fallback(monkeypatch):
    monkeypatch.setenv("VERITYLENS_LLM_API_KEY", "test-key")

    def timeout(*_args, **_kwargs):
        raise requests.Timeout()

    monkeypatch.setattr("veritylens.analysis.requests.post", timeout)
    result = analyze_with_llm("Question", [Source("S1", "Notice", "Some readable source text.")])
    assert result.mode == "deterministic_fallback"
    assert "timed out" in result.error_message


def test_untrusted_or_non_https_api_base_is_rejected_without_request(monkeypatch):
    monkeypatch.setenv("VERITYLENS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("VERITYLENS_LLM_BASE_URL", "http://localhost:9000/v1")

    def unexpected_request(*_args, **_kwargs):
        raise AssertionError("Invalid API base URL must not be contacted.")

    monkeypatch.setattr("veritylens.analysis.requests.post", unexpected_request)
    result = analyze_with_llm("Question", [Source("S1", "Notice", "Some readable source text.")])
    assert result.mode == "deterministic_fallback"
    assert "HTTPS origin" in result.error_message


def test_oversized_provider_response_uses_fallback(monkeypatch):
    class OversizedResponse(FakeResponse):
        def iter_content(self, chunk_size):
            yield b"x" * (1_500_001)

    monkeypatch.setenv("VERITYLENS_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "veritylens.analysis.requests.post",
        lambda *_args, **_kwargs: OversizedResponse({}),
    )
    result = analyze_with_llm("Question", [Source("S1", "Notice", "Readable source text.")])
    assert result.mode == "deterministic_fallback"
    assert "size limit" in result.error_message
