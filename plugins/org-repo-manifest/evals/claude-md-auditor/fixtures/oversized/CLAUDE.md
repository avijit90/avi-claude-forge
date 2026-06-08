# bloated-service

## Purpose
This service handles a wide range of responsibilities including but not limited to authentication, authorization, session management, audit logging, rate limiting, and several other cross-cutting concerns that the platform team has consolidated here over the years. It is the primary entry point for several upstream callers and integrates with many downstream systems via both synchronous HTTP and asynchronous messaging patterns.

## Features
- POST /v1/auth — authenticate
- POST /v1/auth/refresh — refresh tokens
- POST /v1/auth/revoke — revoke tokens
- GET /v1/userinfo — get user profile
- POST /v1/sessions — create session
- GET /v1/sessions/{id} — fetch session
- DELETE /v1/sessions/{id} — end session
- POST /v1/audit/log — log audit event
- GET /v1/audit/events — query audit events
- POST /v1/permissions/grant — grant permission
- POST /v1/permissions/revoke — revoke permission
- GET /v1/permissions/check — check permission
- POST /v1/groups — create group
- PATCH /v1/groups/{id} — update group
- DELETE /v1/groups/{id} — delete group
- GET /v1/groups/{id}/members — list members
- POST /v1/groups/{id}/members — add member
- DELETE /v1/groups/{id}/members/{userId} — remove member
- POST /v1/rate-limit/check — check rate limit
- POST /v1/rate-limit/reset — reset rate limit counter

## Architecture
The service follows a standard layered architecture pattern with a presentation layer, a business logic layer, and a data access layer. The presentation layer is implemented using the FastAPI framework with Pydantic models for request/response validation. The business logic layer contains all the domain rules and orchestrates calls between the various subsystems. The data access layer uses SQLAlchemy ORM with PostgreSQL as the primary datastore, Redis for caching and rate limit counters, and Kafka for emitting audit events to the downstream pipeline. The service is deployed as a set of replicas behind a load balancer, with horizontal autoscaling driven by CPU and request-rate metrics. Background workers run as separate processes managed by Supervisor.

## Commands
```bash
poetry install
poetry run pytest
poetry run uvicorn app.main:app --reload
```

## Gotchas
- The session table grows unbounded; we have a cleanup job that runs nightly
- Rate limit counters in Redis are eventually consistent across replicas
- Audit log writes are async; there is a small window where they can be lost
- Group membership has a cache with a 60 second TTL
- The permission check endpoint has a fast path that skips the DB if the cache hits
- Tokens are ECDSA-signed; key rotation happens weekly
- Refresh tokens are single-use; rotation is atomic via a Postgres advisory lock
- User deletion is cascaded via Kafka events; we listen for `user-deleted`
- The audit pipeline owner is a different team; coordinate before changing event schemas
- Settings live in env vars; required vars fail fast at startup
- Logs are JSON; correlation IDs come from X-Request-Id headers
- Don't put PII in logs; use the redaction helper
- The /metrics endpoint is exposed on port 9090, not the main port
- Health checks use /healthz; readiness uses /readyz
- The service depends on user-service for /userinfo enrichment
- If user-service is down, /userinfo falls back to claims-only
- Don't use the deprecated /v0 endpoints; they're scheduled for removal
- The Kafka consumer is at-least-once; idempotency is the responsibility of consumers
- We use semantic versioning for the API; breaking changes bump the major
- The deployment config lives in a sibling repo (deploys-platform)

## Conventions
- Structured JSON logging only
- Correlation IDs propagated via X-Request-Id
- Typed errors at boundaries
- Files in kebab-case
- Functions verb-first
- Tests next to source
- No DB mocking — use real Postgres via docker-compose
- Config from env vars only
- Secrets from secret manager
- REST: nouns in URLs, verbs in methods
- Error responses include error.code and error.message
- Versioning in the URL path
- Pagination is cursor-based

## Reference
See docs/ for ADRs, runbooks, and the OpenAPI spec.
