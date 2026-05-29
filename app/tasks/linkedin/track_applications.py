import json
import os
from datetime import datetime, timezone

from utils.celery_app import celery_app

_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "applications_log.json")


def _load_log() -> list[dict]:
    try:
        with open(_LOG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_log(entries: list[dict]) -> None:
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with open(_LOG_PATH, "w") as f:
        json.dump(entries, f, indent=2)


@celery_app.task(name="linkedin_track_applications")
def track_linkedin_applications(context: dict) -> dict:
    """Append application results to the persistent JSON log."""
    try:
        previous = context.get("previous_results", [])
        apply_output = next(
            (r["output"] for r in previous if r["task_name"] == "linkedin_apply_jobs"),
            None,
        )
        if not apply_output:
            return {"outcome": "failure", "data": {"error": "No output from linkedin_apply_jobs"}}

        applied = apply_output.get("applied", [])
        failed = apply_output.get("failed", [])
        timestamp = datetime.now(timezone.utc).isoformat()

        log = _load_log()
        new_entries = []
        for entry in applied + failed:
            record = {**entry, "applied_at": timestamp}
            log.append(record)
            new_entries.append(record)

        _save_log(log)

        return {
            "outcome": "success",
            "data": {
                "logged": len(new_entries),
                "total_applied": len(applied),
                "total_failed": len(failed),
                "log_file": _LOG_PATH,
            },
        }
    except Exception as e:
        return {"outcome": "failure", "data": {"error": str(e)}}
