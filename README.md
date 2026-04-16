# HRX AI Chatbot Platform

Production-oriented FastAPI service for HR conversational workflows.
The platform converts natural language questions into HR module queries (attendance, leave, payroll, employee), calls upstream HRX APIs, generates user-friendly answers, and optionally creates downloadable Excel reports.

## Overview

This project provides:

- A chat API for natural language HR questions
- Tool extraction and response generation using Gemini
- MCP-style tool registry for dynamic HR endpoint execution
- Redis-backed in-memory report generation with expiring download links
- PostgreSQL persistence for chat history and tool registry metadata
- Celery worker and beat services for background jobs/scheduling

## Core Features

- Natural language to tool routing (`get_attendance`, `get_leave`, `get_payroll`, `get_employees`)
- Organization-scoped upstream HR API calls
- Tool parameter sanitization based on registry schema
- Local filter support for extracted parameters not accepted upstream (for example `name`)
- Structured chat response format with metadata and optional report payload
- Report download endpoint with TTL-based expiration (default 300 seconds)
- Startup auto-seeding of tool registry definitions

## High-Level Architecture

1. Client sends request to `POST /chat/message`
2. `ChatUsecase` stores incoming message in `chat_history`
3. Gemini extracts `tool_name` and `parameters`
4. `MCPExecutor` resolves active tool from `tool_registry`
5. `HRXService` calls upstream HRX endpoint
6. Returned records are summarized by Gemini
7. Report bytes are generated in-memory and stored in Redis
8. API returns response with answer, tool metadata, and optional report download URL

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy + PostgreSQL
- Redis
- Celery (worker + beat)
- Google Gemini (via `langchain-google-genai`)
- Pandas + OpenPyXL (Excel reports)
- Docker + Docker Compose

## Project Structure

```text
app/
	chatbot/
		dto/            # Request/response schemas
		handler/        # API handlers
		repository/     # DB operations for chat
		usecase/        # Chat orchestration pipeline
	mcp/
		dto/            # Tool DTOs
		handler/        # Tool management endpoints
		seed/           # Startup seed for tool registry
		usecase/        # MCP tool usecases
	report/
		handler/        # Report download endpoint

common/             # Logging, API response helpers
config/             # Environment/Consul configuration
infrastructure/     # DB and task queue wiring
models/             # SQLAlchemy models
services/
	gemini/           # Prompting and LLM integration
	hrx/              # Upstream HRX API client
	mcp/              # Tool execution engine
	report/           # In-memory Excel report service
worker/             # Celery app and jobs
```

## API Endpoints

### Chat

- `POST /chat/message`

Request body:

```json
{
	"message": "Give me Hossain Rabbi attendance",
	"organizationId": "cacc9e5d-3f10-4e32-9732-d9e27990efe9"
}
```

Response shape:

```json
{
	"success": true,
	"status": "completed",
	"data": {
		"chatId": "...",
		"answer": "...",
		"toolUsed": {
			"name": "get_attendance",
			"endpoint": "api/attendance/attendance-list",
			"status": "success",
			"recordsCount": 2
		},
		"report": {
			"id": "...",
			"downloadUrl": "/report/download/...",
			"format": "xlsx",
			"expiresIn": 300
		},
		"metadata": {
			"responseTime": "6.96s",
			"recordsCount": 2,
			"timestamp": "..."
		}
	},
	"error": null
}
```

### Report Download

- `GET /report/download/{report_id}`

Returns Excel file from Redis if still available within TTL.

### MCP Tool Registry

- `POST /mcp/tool/`
- `GET /mcp/tool/`
- `GET /mcp/tool/{tool_name}`
- `POST /mcp/tool/{tool_name}/disable`

### Health

- `GET /health`

## Tool Mapping (Seeded at Startup)

By default, these tools are seeded into `tool_registry`:

- `get_attendance` -> `api/attendance/attendance-list`
- `get_leave` -> `api/leave/leave-list`
- `get_payroll` -> `api/payroll/payroll-list`
- `get_employees` -> `api/employee/employee-list`

## Configuration

Create a `.env` file in the project root.

Minimum required values:

```env
APP_DATABASE_URL=postgresql+psycopg2://admin:admin@postgres:5432/app_db
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
HRX_BASE_URL=https://api-staging-monolithic-b2b.hrxbd.org
HRX_BEARER_TOKEN=your_hrx_token
GOOGLE_API_KEY=your_google_api_key
```

Optional values:

- `USE_CONSUL=true|false`
- `CONSUL_HOST`, `CONSUL_PORT`, `CONSUL_KEY`
- Gemini tuning: `GEMINI_TEMPERATURE`, `GEMINI_MAX_TOKENS`, `GEMINI_TIMEOUT`, etc.
- MinIO-related keys if object storage is needed

## Running with Docker Compose (Recommended)

```bash
docker compose up --build
```

Services started:

- `web` (FastAPI): `http://localhost:8000`
- `worker` (Celery)
- `beat` (Celery Beat)
- `postgres` (5432)
- `redis` (6379)

Swagger docs:

- `http://localhost:8000/docs`

## Local Development (Without Docker)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure PostgreSQL and Redis are available and `.env` points to them.

3. Start API:

```bash
uvicorn app.serve:app --host 0.0.0.0 --port 8000 --reload
```

4. Start Celery worker (optional but recommended):

```bash
celery -A worker.celery_app worker --loglevel=info
```

5. Start Celery beat (optional):

```bash
celery -A worker.celery_app beat --loglevel=info
```

## Data Model Summary

- `chat_history`: incoming and generated chat content
- `tool_registry`: active tool definitions and schemas
- `report_log`: report metadata model (available for extension)

Tables are auto-created at startup via SQLAlchemy `create_all`.

## Report Generation Details

- Excel is generated fully in memory using Pandas/OpenPyXL
- Binary bytes are stored in Redis with key prefix `report:`
- Default expiry is 300 seconds
- Download API streams bytes directly without disk persistence

## Troubleshooting

### Chat returns fallback answer instead of data

Possible causes:

- Upstream HRX API validation failure (for example HTTP 422)
- Missing or invalid `HRX_BEARER_TOKEN`
- Invalid `organizationId`

Check logs:

```bash
docker compose logs web --tail=200
```

### Report is `null`

`report` becomes `null` when:

- No list records were returned
- Report generation failed
- Redis backend is unavailable

Check report and Redis logs:

```bash
docker compose logs web --tail=200
docker compose logs redis --tail=200
```

### Gemini extraction/answer issues

Verify:

- `GOOGLE_API_KEY` is valid
- Quota is available
- Prompt output is valid JSON for tool extraction

## Security and Operations Notes

- Never commit `.env` or tokens to version control
- Restrict HRX and Gemini keys per environment
- Add request tracing and centralized log aggregation for production
- Add CI checks (lint/test) before deployment

## Suggested Next Improvements

- Add automated tests for usecases and services
- Add DB migrations (Alembic) instead of only `create_all`
- Add strict response contracts and schema validation for upstream payloads
- Add rate limiting and API authentication for public deployment
