"""AI calls are checked without touching the network."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from pulse import ai
from pulse.models import Analysis
from pulse.prompts import ANALYSIS_TOOL

PAYLOAD = {
    "status": "at_risk",
    "reason": "Stock may run out.",
    "status_evidence": "Shipment still held at customs",
    "risks": [
        {
            "description": "Stock out",
            "severity": "high",
            "owner": None,
            "evidence": "about 3 weeks of filter stock left",
        }
    ],
    "decisions": [],
    "confidence": "high",
}


def test_parse_valid_payload():
    a = ai.parse_analysis(PAYLOAD, "SUPP-1", "test-model")
    assert isinstance(a, Analysis) and a.model == "test-model" and a.prompt_version


def test_parse_rejects_unknown_status():
    with pytest.raises(ValidationError):
        ai.parse_analysis({**PAYLOAD, "status": "probably fine"}, "SUPP-1", "m")


def test_tool_schema_matches_model():
    required = set(ANALYSIS_TOOL["input_schema"]["required"])
    assert required <= set(Analysis.model_fields)


def test_analyze_update_uses_forced_tool_call(monkeypatch, programs, updates):
    calls = {}

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            block = SimpleNamespace(type="tool_use", name="record_analysis", input=PAYLOAD)
            return SimpleNamespace(content=[block])

    monkeypatch.setattr(ai, "_client", lambda key: SimpleNamespace(messages=FakeMessages()))
    update = next(u for u in updates if u.program_id == "SUPP")
    result = ai.analyze_update(update, programs["SUPP"], api_key="fake")
    assert result.update_id == update.id
    assert calls["tool_choice"] == {"type": "tool", "name": "record_analysis"}
    assert update.text in calls["messages"][0]["content"]


def test_missing_tool_call_raises():
    with pytest.raises(ValueError):
        ai._tool_input(SimpleNamespace(content=[SimpleNamespace(type="text", text="hi")]), "record_analysis")
