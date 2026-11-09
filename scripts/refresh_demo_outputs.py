"""Regenerate the saved demo outputs with the live Claude API.

Usage (from the project folder, with ANTHROPIC_API_KEY set):
    python scripts/refresh_demo_outputs.py

Writes data/demo_ai_outputs.json and data/demo_brief.json. Review the diff
before committing: these files are what visitors see in demo mode.
Note: the shipped demo files contain two planted mistakes (an unsupported quote
on the investor update and a lab figure in the brief) to show the controls. A fresh run will
not include it unless the model makes the same kind of mistake.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pulse import ai, data  # noqa: E402


def main() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("Set ANTHROPIC_API_KEY first.")
    programs = {p.id: p for p in data.load_programs()}
    updates = data.load_updates()
    latest = data.latest_update_per_program(updates)

    analyses = []
    for pid, update in latest.items():
        print(f"Analyzing {update.id}...")
        analyses.append(ai.analyze_update(update, programs[pid], key))
    (data.DATA_DIR / "demo_ai_outputs.json").write_text(
        json.dumps([a.model_dump(mode="json") for a in analyses], indent=2)
    )

    print("Drafting brief...")
    pairs = [(programs[pid], a) for pid, a in zip(latest, analyses, strict=True)]
    brief = ai.draft_brief(pairs, data.reporting_week(updates), key)
    (data.DATA_DIR / "demo_brief.json").write_text(json.dumps(brief.model_dump(mode="json"), indent=2))
    print("Done. Check the changes before committing.")


if __name__ == "__main__":
    main()
