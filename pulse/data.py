"""Load the synthetic data files into checked Python objects."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pulse.models import Analysis, Brief, Program, Update

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_company(data_dir: Path = DATA_DIR) -> dict:
    return json.loads((data_dir / "programs.json").read_text())["company"]


def load_programs(data_dir: Path = DATA_DIR) -> list[Program]:
    raw = json.loads((data_dir / "programs.json").read_text())["programs"]
    return [Program(**p) for p in raw]


def load_updates(data_dir: Path = DATA_DIR) -> list[Update]:
    raw = json.loads((data_dir / "updates.json").read_text())
    return sorted((Update(**u) for u in raw), key=lambda u: (u.program_id, u.week_ending))


def load_demo_analyses(data_dir: Path = DATA_DIR) -> dict[str, Analysis]:
    """Saved AI outputs, keyed by update id, so the demo runs without an API key."""
    raw = json.loads((data_dir / "demo_ai_outputs.json").read_text())
    return {a["update_id"]: Analysis(**a) for a in raw}


def load_demo_brief(data_dir: Path = DATA_DIR) -> Brief:
    return Brief(**json.loads((data_dir / "demo_brief.json").read_text()))


def load_assessments(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "assessments.csv", parse_dates=["before_date", "after_date"])
    for metric in ("mold", "tvoc", "pm25", "co2"):
        df[f"{metric}_change_pct"] = (df[f"{metric}_after"] - df[f"{metric}_before"]) / df[f"{metric}_before"] * 100
    return df


def latest_update_per_program(updates: list[Update]) -> dict[str, Update]:
    latest: dict[str, Update] = {}
    for u in updates:
        if u.program_id not in latest or u.week_ending > latest[u.program_id].week_ending:
            latest[u.program_id] = u
    return latest


def reporting_week(updates: list[Update]):
    """The most recent week anyone reported. Treated as 'this week' in the demo."""
    return max(u.week_ending for u in updates)
