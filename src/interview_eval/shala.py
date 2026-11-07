from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXPORT_SCHEMA = "interview-shala-evaluation-export/v1"


def load_shala_export(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != EXPORT_SCHEMA:
        raise ValueError(f"Expected Interview Shala export schema {EXPORT_SCHEMA!r}")
    session = data.get("session")
    transcript = data.get("transcript")
    if not isinstance(session, dict) or not isinstance(transcript, list):
        raise ValueError("Export must contain a session object and transcript array")
    return data


def export_to_case(data: dict[str, Any]) -> dict[str, Any]:
    session = data["session"]
    transcript = data["transcript"]
    return {
        "id": f"shala-{session.get('id', 'unknown')}",
        "type": "shala_session",
        "session": session,
        "transcript": transcript,
        "skill_scores": data.get("skill_scores", []),
    }


def write_case(data: dict[str, Any], output: str | Path) -> None:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(export_to_case(data), ensure_ascii=False) + "\n",
                      encoding="utf-8")
