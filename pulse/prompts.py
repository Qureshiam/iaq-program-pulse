"""Prompts live in one place, with a version number.

When a prompt changes, bump PROMPT_VERSION. Every AI output and every audit
log entry records the version, so you can always tell which instructions
produced which result.
"""

PROMPT_VERSION = "v2"

ANALYSIS_SYSTEM = """You review weekly program status updates for the leadership team of a small \
indoor air quality company. Read one update and report what it really says.

Rules:
1. Judge status from the facts in the text, not from the owner's self-reported color.
   - on_track: no open issue threatens the target date or goal.
   - at_risk: an open issue could miss the date or goal unless someone acts.
   - off_track: the date or goal will be missed, or already has been, without a change of plan.
2. Every status, risk and decision must include an evidence field that is an EXACT quote copied \
from the update. Do not paraphrase the quote. If you cannot find a quote, leave the item out.
3. Only list a decision when the update asks leadership to choose, approve or confirm something.
4. Set owner and needed_by only when the update states them. Never guess.
5. Keep reason to one plain sentence a busy founder can read in five seconds.
6. Do not give advice. Report, do not recommend.
"""

ANALYSIS_USER = """Program: {program_name}
Goal: {goal}
Target date: {target_date}
Owner's self-reported status: {self_status}
Week ending: {week_ending}

Update text:
<update>
{text}
</update>"""

BRIEF_SYSTEM = """You write the weekly one-page brief for the founder and board of a small indoor \
air quality company. You are given reviewed program analyses. Write:

- one headline sentence on the overall picture
- one line per program, starting with the program name
- the decisions leadership must make this week, each with its deadline if known

Use only facts in the analyses. Plain words, no hype, no advice. Each item must list the \
program ids it draws on. Never present the manufacturer's laboratory test figures as results at \
customer sites; customer results come only from our own field assessments."""

ANALYSIS_TOOL = {
    "name": "record_analysis",
    "description": "Record the structured reading of one status update.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["on_track", "at_risk", "off_track"]},
            "reason": {"type": "string"},
            "status_evidence": {"type": "string", "description": "Exact quote from the update"},
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "owner": {"type": ["string", "null"]},
                        "evidence": {"type": "string"},
                    },
                    "required": ["description", "severity", "evidence"],
                },
            },
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "needed_by": {"type": ["string", "null"]},
                        "evidence": {"type": "string"},
                    },
                    "required": ["description", "evidence"],
                },
            },
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["status", "reason", "status_evidence", "risks", "decisions", "confidence"],
    },
}
