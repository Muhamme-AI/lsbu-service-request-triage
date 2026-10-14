"""The AI step is exercised with a fake HTTP opener: no network, no keys, no cost."""

import json
import urllib.error

import pytest

from tests.conftest import AS_OF, EDGE_CSV, SAMPLE_CSV
from triage.ai import AIConfigError, AIDraftError, AISettings, build_messages, provider_chain, validate_draft
from triage.pipeline import run

AZURE_ENV = {
    "TRIAGE_AI_PROVIDER": "azure",
    "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "fake-key",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def reply_with(text_for_request_id):
    def opener(request, timeout=None):
        body = json.loads(request.data)
        facts_json = body["messages"][1]["content"].split("Facts (JSON):\n", 1)[1].split("\n\nReference template", 1)[0]
        request_id = json.loads(facts_json)["request_id"]
        return FakeResponse({"model": "gpt-4o-mini-test", "choices": [{"message": {"content": text_for_request_id(request_id)}}]})

    return opener


def good_text(request_id):
    return f"Dear colleague,\n\nThank you for your request {request_id}. We have logged it and will respond within the stated time.\n\nKind regards,\nDigital Services Team"


def test_settings_are_none_when_provider_unset():
    assert AISettings.from_env({}) is None


def test_azure_settings_build_the_right_url_and_header():
    settings = AISettings.from_env(AZURE_ENV)
    assert settings.url == "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2024-10-21"
    assert settings.headers["api-key"] == "fake-key"


def test_openai_settings_and_incomplete_config():
    settings = AISettings.from_env({"TRIAGE_AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"})
    assert settings.url.endswith("/v1/chat/completions") and settings.headers["Authorization"] == "Bearer sk-test"
    with pytest.raises(AIConfigError):
        AISettings.from_env({"TRIAGE_AI_PROVIDER": "azure"})
    with pytest.raises(AIConfigError):
        AISettings.from_env({"TRIAGE_AI_PROVIDER": "gemini"})


def test_prompt_marks_summary_as_untrusted_and_truncates():
    facts = {"request_id": "REQ-1", "request_summary": "x" * 2000}
    messages = build_messages(facts, "template")
    assert "untrusted" in messages[0]["content"]
    assert len(json.loads(messages[1]["content"].split("Facts (JSON):\n", 1)[1].split("\n\nReference template", 1)[0])["request_summary"]) < 600


def test_validate_draft_rejects_bad_replies():
    with pytest.raises(AIDraftError):
        validate_draft("", "REQ-1")
    with pytest.raises(AIDraftError):
        validate_draft("Dear colleague, thanks for your request, we will be in touch shortly. Kind regards", "REQ-1")
    with pytest.raises(AIDraftError):
        validate_draft("```text\nDear colleague REQ-1 ... Kind regards team\n```", "REQ-1")
    assert validate_draft(good_text("REQ-1"), "REQ-1").endswith("\n")


def test_successful_ai_drafts_replace_templates():
    settings = AISettings.from_env(AZURE_ENV)
    result = run(SAMPLE_CSV, as_of=AS_OF, ai_settings=settings, ai_opener=reply_with(good_text))
    assert result.summary["acknowledgement_sources"] == {"ai": 10}
    assert result.ai_enabled and result.ai_provider == "azure:gpt-4o-mini"
    assert "REQ-001" in result.results[0].acknowledgement


def test_network_failure_falls_back_to_template():
    def failing_opener(request, timeout=None):
        raise urllib.error.URLError("name resolution failed")

    result = run(SAMPLE_CSV, as_of=AS_OF, ai_settings=AISettings.from_env(AZURE_ENV), ai_opener=failing_opener)
    assert result.summary["acknowledgement_sources"] == {"template": 10}
    assert "template used" in result.results[0].ai_note


def test_reply_without_reference_is_rejected():
    result = run(SAMPLE_CSV, as_of=AS_OF, ai_settings=AISettings.from_env(AZURE_ENV), ai_opener=reply_with(lambda _rid: good_text("REQ-999")))
    assert result.summary["acknowledgement_sources"] == {"template": 10}
    assert "did not quote the request reference" in result.results[0].ai_note


def test_groq_is_the_free_provider_and_paid_models_are_the_fallback():
    settings = AISettings.from_env({"TRIAGE_AI_PROVIDER": "groq", "GROQ_API_KEY": "gsk-test"})
    assert settings.url == "https://api.groq.com/openai/v1/chat/completions"
    assert settings.model == "openai/gpt-oss-20b"
    assert settings.headers["Authorization"] == "Bearer gsk-test"
    assert settings.describe() == "groq:gpt-oss-20b"
    with pytest.raises(AIConfigError):
        AISettings.from_env({"TRIAGE_AI_PROVIDER": "groq"})

    chain = provider_chain({
        "TRIAGE_AI_PROVIDER": "groq",
        "GROQ_API_KEY": "gsk-test",
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "azure-key",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
        "OPENAI_API_KEY": "sk-test",
    })
    assert [item.provider for item in chain] == ["groq", "azure", "openai"]
    # A half-filled Azure block is skipped rather than failing the free path.
    groq_only = provider_chain({"TRIAGE_AI_PROVIDER": "groq", "GROQ_API_KEY": "gsk-test", "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com"})
    assert [item.provider for item in groq_only] == ["groq"]


def test_groq_failure_uses_azure_before_the_template():
    chain = provider_chain({
        "TRIAGE_AI_PROVIDER": "groq",
        "GROQ_API_KEY": "gsk-test",
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "azure-key",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
    })
    calls = []

    def opener(request, timeout=None):
        calls.append(request.full_url)
        if "api.groq.com" in request.full_url:
            raise urllib.error.URLError("groq unavailable")
        return reply_with(good_text)(request, timeout)

    result = run(SAMPLE_CSV, as_of=AS_OF, ai_settings=chain, ai_opener=opener)
    assert result.summary["acknowledgement_sources"] == {"ai": 10}
    assert result.ai_provider.startswith("groq:gpt-oss-20b")
    assert "fallback: azure:gpt-4o-mini" in result.ai_provider
    note = result.results[0].ai_note
    assert "Drafted by azure" in note and "groq:" in note
    assert any("api.groq.com" in url for url in calls)
    assert any("openai.azure.com" in url for url in calls)


def test_personal_or_sensitive_requests_are_never_sent_to_the_model():
    calls = []

    def recording_opener(request, timeout=None):
        calls.append(json.loads(request.data))
        return reply_with(good_text)(request, timeout)

    result = run(EDGE_CSV, as_of=AS_OF, ai_settings=AISettings.from_env(AZURE_ENV), ai_opener=recording_opener)
    by_id = {r.request.request_id: r for r in result.results}
    assert by_id["REQ-107"].ack_source == "template" and "POSSIBLE_PERSONAL_DATA" in by_id["REQ-107"].ai_note
    assert by_id["REQ-113"].ack_source == "template" and "SENSITIVE_CONTENT" in by_id["REQ-113"].ai_note
    sent_text = json.dumps(calls)
    assert "j.bloggs@example.ac.uk" not in sent_text
    assert "disability" not in sent_text
