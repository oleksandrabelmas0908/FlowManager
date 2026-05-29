"""Register the LinkedIn job application flow via the FlowManager API."""
import json
import sys
import urllib.request

API_BASE = "http://localhost:8000/api/v1"

FLOW = {
    "id": "linkedin-job-application",
    "name": "LinkedIn Job Application Flow",
    "start_task": "linkedin_search_jobs",
    "tasks": [
        {"name": "linkedin_search_jobs", "description": "Login and search LinkedIn for matching jobs"},
        {"name": "linkedin_filter_jobs", "description": "Filter jobs by CV skill match and deduplicate"},
        {"name": "linkedin_apply_jobs", "description": "Apply to Easy Apply jobs via browser automation"},
        {"name": "linkedin_track_applications", "description": "Log all application results to file"},
    ],
    "conditions": [
        {
            "name": "after_search",
            "description": "Proceed to filtering after successful job search",
            "source_task": "linkedin_search_jobs",
            "outcome": "success",
            "target_task_success": "linkedin_filter_jobs",
            "target_task_failure": "end",
        },
        {
            "name": "after_filter",
            "description": "Proceed to applying after successful filtering",
            "source_task": "linkedin_filter_jobs",
            "outcome": "success",
            "target_task_success": "linkedin_apply_jobs",
            "target_task_failure": "end",
        },
        {
            "name": "after_apply",
            "description": "Always track application results regardless of outcome",
            "source_task": "linkedin_apply_jobs",
            "outcome": "success",
            "target_task_success": "linkedin_track_applications",
            "target_task_failure": "linkedin_track_applications",
        },
    ],
}


def register():
    payload = json.dumps({"flow": FLOW}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/flows",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
            print(f"Flow registered: {body.get('id')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def trigger():
    req = urllib.request.Request(
        f"{API_BASE}/flows/linkedin-job-application/execute",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
            execution_id = body.get("execution_id")
            print(f"Execution started: {execution_id}")
            print(f"Poll: GET {API_BASE}/executions/{execution_id}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "register"
    if action == "trigger":
        trigger()
    else:
        register()
