# REST API Reference

The GUI runs a debug HTTP server on port 5679.

**OpenAPI Spec:** `curl http://127.0.0.1:5679/api/openapi.json`

## Read Endpoints

### Health & State

```bash
# API documentation (self-describing)
curl http://127.0.0.1:5679/

# Health check
curl http://127.0.0.1:5679/api/health

# Full application state
curl http://127.0.0.1:5679/api/state

# Scheduler status
curl http://127.0.0.1:5679/api/scheduler
```

### Tasks

```bash
# List all tasks
curl http://127.0.0.1:5679/api/tasks

# Get single task
curl http://127.0.0.1:5679/api/tasks/{id}
```

### Runs

```bash
# List all runs
curl http://127.0.0.1:5679/api/runs

# Get single run
curl http://127.0.0.1:5679/api/runs/{id}
```

### Jobs

```bash
# List all jobs
curl http://127.0.0.1:5679/api/jobs

# Get single job
curl http://127.0.0.1:5679/api/jobs/{id}

# List tasks in job
curl http://127.0.0.1:5679/api/jobs/{id}/tasks

# Get task order
curl http://127.0.0.1:5679/api/jobs/{id}/task-order

# Export job
curl http://127.0.0.1:5679/api/jobs/{id}/export
```

### Profiles

```bash
# List all profiles
curl http://127.0.0.1:5679/api/profiles

# Get single profile
curl http://127.0.0.1:5679/api/profiles/{id}
```

### UI Inspection

```bash
# UI state
curl http://127.0.0.1:5679/api/ui

# UI analysis
curl http://127.0.0.1:5679/api/ui/analysis

# Screenshot
curl http://127.0.0.1:5679/api/ui/screenshot/task_list
```

## Write Endpoints

### Tasks CRUD

```bash
# Create task
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Test","prompt":"your prompt here","profile":"<profile-id>"}' \
  http://127.0.0.1:5679/api/tasks

# Create task in job
curl -X POST -H "Content-Type: application/json" \
  -d '{"job_id":"<uuid>","name":"Test","prompt":"your prompt here","model":"sonnet","profile":"<profile-id>"}' \
  http://127.0.0.1:5679/api/tasks

# Update task
curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Updated"}' \
  http://127.0.0.1:5679/api/tasks/{id}

# Delete task
curl -X DELETE http://127.0.0.1:5679/api/tasks/{id}
```

### Task Actions

```bash
# Run task now
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/run

# Enable task
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/enable

# Disable task
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/disable
```

### Runs Actions

```bash
# Stop running task
curl -X POST http://127.0.0.1:5679/api/runs/{id}/stop

# Restart task
curl -X POST http://127.0.0.1:5679/api/runs/{id}/restart

# Delete run record
curl -X DELETE http://127.0.0.1:5679/api/runs/{id}
```

### Jobs CRUD

```bash
# Create job
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Daily Maintenance"}' \
  http://127.0.0.1:5679/api/jobs

# Create job with profile
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Feature","profile":"<uuid>"}' \
  http://127.0.0.1:5679/api/jobs

# Update job
curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Updated"}' \
  http://127.0.0.1:5679/api/jobs/{id}

# Update task order
curl -X PUT -H "Content-Type: application/json" \
  -d '{"task_order":["uuid1","uuid2","uuid3"]}' \
  http://127.0.0.1:5679/api/jobs/{id}/task-order

# Delete job
curl -X DELETE http://127.0.0.1:5679/api/jobs/{id}
```

### Job Actions

```bash
# Run job (sequential execution of tasks)
curl -X POST http://127.0.0.1:5679/api/jobs/{id}/run

# Stop running job
curl -X POST http://127.0.0.1:5679/api/jobs/{id}/stop

# Export job to file
curl -X POST -H "Content-Type: application/json" \
  -d '{"output_path":"/path/to/export.json"}' \
  http://127.0.0.1:5679/api/jobs/{id}/export

# Import job
curl -X POST -H "Content-Type: application/json" \
  -d '{"file_path":"/path/to/import.json","force":false}' \
  http://127.0.0.1:5679/api/jobs/import
```

### Profiles CRUD

```bash
# Create profile
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Production"}' \
  http://127.0.0.1:5679/api/profiles

# Update profile
curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Updated"}' \
  http://127.0.0.1:5679/api/profiles/{id}

# Delete profile
curl -X DELETE http://127.0.0.1:5679/api/profiles/{id}
```

## Response Format

### Success Response

```json
{
  "success": true,
  "task": { ... }
}
```

### Error Response

```json
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "Task not found"
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (invalid JSON, validation failed) |
| 404 | Not found |
| 409 | Conflict (UUID already exists) |
| 422 | Unprocessable (profile not found) |
| 500 | Server error |

## Port Configuration

| Service | Default Port | Environment |
|---------|--------------|-------------|
| GUI Debug Server | 5679 | `--restport` |
| Daemon HTTP API | 8787 | `--api-port` |

**Check port conflicts:**
```bash
lsof -i :5679
lsof -i :8787

# Kill processes using ports
lsof -ti:5679 | xargs kill -9
```
