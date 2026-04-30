from utils.celery_app import celery_app


@celery_app.task(name="task1")
def fetch_data(context: dict) -> dict:
    """Simulates fetching data from an external source."""
    try:
        raw_data = [
            {"id": 1, "value": 42},
            {"id": 2, "value": 17},
            {"id": 3, "value": 99},
        ]
        return {
            "outcome": "success",
            "data": {"records": raw_data, "count": len(raw_data)},
        }
    except Exception as e:
        return {"outcome": "failure", "data": {"error": str(e)}}
