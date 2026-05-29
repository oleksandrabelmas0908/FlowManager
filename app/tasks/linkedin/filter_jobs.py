import json
import os

from utils.celery_app import celery_app

_CV_KEYWORDS = [
    "python", "backend", "fastapi", "django", "drf", "postgresql", "postgres",
    "redis", "kafka", "rabbitmq", "docker", "kubernetes", "aws", "celery",
    "sqlalchemy", "microservice", "microservices", "rest", "api", "engineer",
    "senior", "developer",
]

_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "applications_log.json")


def _load_applied_ids() -> set[str]:
    try:
        with open(_LOG_PATH) as f:
            entries = json.load(f)
        return {e["job_id"] for e in entries}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return set()


def _score_job(job: dict) -> int:
    text = (job.get("title", "") + " " + job.get("company", "")).lower()
    return sum(1 for kw in _CV_KEYWORDS if kw in text)


@celery_app.task(name="linkedin_filter_jobs")
def filter_matching_jobs(context: dict) -> dict:
    """Filter scraped jobs by CV keyword match and remove already-applied ones."""
    try:
        previous = context.get("previous_results", [])
        search_output = next(
            (r["output"] for r in previous if r["task_name"] == "linkedin_search_jobs"),
            None,
        )
        if not search_output:
            return {"outcome": "failure", "data": {"error": "No output from linkedin_search_jobs"}}

        jobs = search_output.get("jobs", [])
        applied_ids = _load_applied_ids()

        filtered = []
        skipped = 0
        for job in jobs:
            if job["job_id"] in applied_ids:
                skipped += 1
                continue
            if _score_job(job) >= 1:
                filtered.append(job)
            else:
                skipped += 1

        return {
            "outcome": "success",
            "data": {"filtered_jobs": filtered, "skipped": skipped, "total_to_apply": len(filtered)},
        }
    except Exception as e:
        return {"outcome": "failure", "data": {"error": str(e)}}
