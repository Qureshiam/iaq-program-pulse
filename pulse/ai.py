"""Calls to the Claude API.

The model is forced to answer through a tool with a fixed schema, so the
reply is always structured data, never free text we have to parse. The raw
reply is then checked by Pydantic before the app uses it.

The app only calls this module in Live mode. Demo mode reads saved outputs
from data/demo_ai_outputs.json instead, so the public demo costs nothing.
"""

from __future__ import annotations

import os
from datetime import date

from pulse.models import Analysis, Brief, BriefItem, Program, Update
from pulse.prompts import (
    ANALYSIS_SYSTEM,
    ANALYSIS_TOOL,
    ANALYSIS_USER,
    BRIEF_SYSTEM,
    PROMPT_VERSION,
)

DEFAULT_MODEL = os.getenv("PULSE_MODEL", "claude-sonnet-5-5")

BRIEF_TOOL = {
    "name": "record_brief",
    "description": "Record the weekly brief.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "enum": ["headline", "program", "ask"]},
                        "text": {"type": "string"},
                        "program_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["section", "text", "program_ids"],
                },
            }
        },
        "required": ["items"],
    },
}


def _client(api_key: str):
    import anthropic  # imported here so tests and demo mode never need the package configured

    return anthropic.Anthropic(api_key=api_key)


def _tool_input(response, tool_name: str) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return block.input
    raise ValueError(f"Model did not return the {tool_name} tool call")


def parse_analysis(payload: dict, update_id: str, model: str) -> Analysis:
    """Turn the tool payload into a checked Analysis. Raises if the shape is wrong."""
    return Analysis(update_id=update_id, model=model, prompt_version=PROMPT_VERSION, **payload)


def analyze_update(update: Update, program: Program, api_key: str, model: str = DEFAULT_MODEL) -> Analysis:
    response = _client(api_key).messages.create(
        model=model,
        max_tokens=1500,
        system=ANALYSIS_SYSTEM,
        tools=[ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": ANALYSIS_TOOL["name"]},
        messages=[
            {
                "role": "user",
                "content": ANALYSIS_USER.format(
                    program_name=program.name,
                    goal=program.goal,
                    target_date=program.target_date,
                    self_status=update.self_status.value,
                    week_ending=update.week_ending,
                    text=update.text,
                ),
            }
        ],
    )
    return parse_analysis(_tool_input(response, ANALYSIS_TOOL["name"]), update.id, model)


def draft_brief(
    analyses: list[tuple[Program, Analysis]], week_ending: date, api_key: str, model: str = DEFAULT_MODEL
) -> Brief:
    lines = []
    for program, a in analyses:
        risks = "; ".join(f"{r.severity.value}: {r.description}" for r in a.risks) or "none"
        decisions = "; ".join(f"{d.description} (by {d.needed_by or 'no date given'})" for d in a.decisions) or "none"
        lines.append(
            f"[{program.id}] {program.name} | status: {a.status.value} | {a.reason} | "
            f"risks: {risks} | decisions: {decisions}"
        )
    response = _client(api_key).messages.create(
        model=model,
        max_tokens=1500,
        system=BRIEF_SYSTEM,
        tools=[BRIEF_TOOL],
        tool_choice={"type": "tool", "name": BRIEF_TOOL["name"]},
        messages=[{"role": "user", "content": f"Week ending {week_ending}\n\n" + "\n".join(lines)}],
    )
    items = _tool_input(response, BRIEF_TOOL["name"])["items"]
    return Brief(
        week_ending=week_ending,
        items=[BriefItem(id=f"B{i}", **item) for i, item in enumerate(items, start=1)],
        model=model,
        prompt_version=PROMPT_VERSION,
    )
