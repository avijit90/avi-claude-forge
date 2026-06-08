# orders

## Purpose
Owns order lifecycle: create, update, cancel, fulfillment notifications.

## Features
- POST /orders
- PATCH /orders/{id}
- DELETE /orders/{id}
- GET /orders/{id}/events

## Architecture
Flask HTTP server, entry point `app.py`. SQLite via raw SQL. Background worker is a thread spawned at startup.

## Commands
```bash
pip install -r requirements.txt
pytest
python app.py
```

## Gotchas
- SQLite locks on writes; serialize writes via the worker thread.

## Conventions
- Logs JSON. Errors raise typed exceptions.

## Reference
See `docs/api/` for the OpenAPI spec.
