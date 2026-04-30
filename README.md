# Flow Manager

A microservice that executes sequential task flows with condition-based routing. Flows are defined in JSON, stored in PostgreSQL, and tasks are executed via Celery workers.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Running the project

### 1. Clone and start

```bash
docker compose up --build
```

No `.env` file is required — default values are used automatically.

### 2. Override defaults (optional)

Copy the example env file and edit as needed:

```bash
cp .env .env.local
```

Or create a `.env` file manually:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=flowmanager
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/flowmanager
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

### 3. Verify

```bash
curl http://localhost:8000/api/v1/flows
```

Interactive API docs are available at **http://localhost:8000/docs**.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/flows` | Register a flow definition |
| `GET` | `/api/v1/flows` | List all flows |
| `GET` | `/api/v1/flows/{id}` | Get a flow |
| `DELETE` | `/api/v1/flows/{id}` | Delete a flow |
| `POST` | `/api/v1/flows/{id}/execute` | Execute a flow |
| `GET` | `/api/v1/flows/{id}/executions` | List executions for a flow |
| `GET` | `/api/v1/executions/{id}` | Get execution result |

### Example: register and run a flow

```bash
curl -X POST http://localhost:8000/api/v1/flows \
  -H "Content-Type: application/json" \
  -d '{
    "flow": {
      "id": "flow123",
      "name": "Data processing flow",
      "start_task": "task1",
      "tasks": [
        {"name": "task1", "description": "Fetch data"},
        {"name": "task2", "description": "Process data"},
        {"name": "task3", "description": "Store data"}
      ],
      "conditions": [
        {
          "name": "condition_task1_result",
          "description": "Proceed to task2 on success",
          "source_task": "task1",
          "outcome": "success",
          "target_task_success": "task2",
          "target_task_failure": "end"
        },
        {
          "name": "condition_task2_result",
          "description": "Proceed to task3 on success",
          "source_task": "task2",
          "outcome": "success",
          "target_task_success": "task3",
          "target_task_failure": "end"
        }
      ]
    }
  }'

curl -X POST http://localhost:8000/api/v1/flows/flow123/execute
```

## Services

| Service | Description |
|---------|-------------|
| `api` | FastAPI app on port 8000 |
| `worker` | Celery worker for task execution |
| `db` | PostgreSQL 16 |
| `redis` | Redis 7 (Celery broker) |

## Stopping

```bash
docker compose down          # stop containers
docker compose down -v       # stop and delete all data
```
