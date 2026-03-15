from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from common import ensure_parent
from constants import RUNS_DIR


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


class RunStatusTracker:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.status_path = run_dir / "status.json"
        self.latest_status_path = RUNS_DIR / "latest_status.json"
        self.data: dict[str, Any] = {
            "status": "running",
            "started_at": now_iso(),
            "finished_at": None,
            "run_dir": str(run_dir),
            "current_stage": "initializing",
            "stages": [],
            "metrics": {},
            "error": None,
        }
        self.write()

    def write(self) -> None:
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        ensure_parent(self.status_path)
        self.status_path.write_text(payload, encoding="utf-8")
        ensure_parent(self.latest_status_path)
        self.latest_status_path.write_text(payload, encoding="utf-8")

    def set_stage(self, name: str, details: dict[str, Any] | None = None) -> None:
        self.data["current_stage"] = name
        self.data["stages"].append(
            {
                "name": name,
                "started_at": now_iso(),
                "details": details or {},
            }
        )
        self.write()

    def set_metric(self, key: str, value: Any) -> None:
        self.data["metrics"][key] = value
        self.write()

    def fail(self, error: Exception) -> None:
        self.data["status"] = "failed"
        self.data["finished_at"] = now_iso()
        self.data["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
        self.write()

    def complete(self) -> None:
        self.data["status"] = "completed"
        self.data["finished_at"] = now_iso()
        self.data["current_stage"] = "completed"
        self.write()
