from utils.celery_app import celery_app


@celery_app.task(name="task2")
def process_data(context: dict) -> dict:
    """Transforms records fetched by task1 (doubles each value)."""
    try:
        previous = context.get("previous_results", [])
        fetch_output = next(
            (r["output"] for r in previous if r["task_name"] == "task1"),
            None,
        )
        if not fetch_output:
            return {"outcome": "failure", "data": {"error": "No output from task1"}}

        records = fetch_output.get("records", [])
        processed = [{"id": r["id"], "doubled_value": r["value"] * 2} for r in records]
        return {
            "outcome": "success",
            "data": {"processed_records": processed},
        }
    except Exception as e:
        return {"outcome": "failure", "data": {"error": str(e)}}
