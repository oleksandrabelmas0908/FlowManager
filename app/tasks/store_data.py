from utils.celery_app import celery_app

_store: list[dict] = []


@celery_app.task(name="task3")
def store_data(context: dict) -> dict:
    """Persists processed records into an in-memory store."""
    try:
        previous = context.get("previous_results", [])
        process_output = next(
            (r["output"] for r in previous if r["task_name"] == "task2"),
            None,
        )
        if not process_output:
            return {"outcome": "failure", "data": {"error": "No output from task2"}}

        records = process_output.get("processed_records", [])
        _store.extend(records)
        return {
            "outcome": "success",
            "data": {"stored_count": len(records), "message": "Data persisted successfully"},
        }
    except Exception as e:
        return {"outcome": "failure", "data": {"error": str(e)}}
