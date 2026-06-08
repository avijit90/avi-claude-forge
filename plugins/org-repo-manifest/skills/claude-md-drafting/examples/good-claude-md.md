# Example: a good CLAUDE.md

This is what the drafting skill aims to produce — a CLAUDE.md for a fictional `auth-service`, ~95 lines, all 7 sections, copy-pasteable commands, specific gotchas, curated conventions.

---

```markdown
# auth-service

## Purpose

Issues, verifies, and revokes short-lived JWT access tokens for the org's internal services. Owns the OAuth2 password-grant and client-credentials flows; refresh-token rotation; and the `/userinfo` endpoint.

## Features

- POST /v1/token — issues access + refresh tokens given valid credentials
- POST /v1/token/refresh — rotates refresh tokens; old token is revoked atomically
- POST /v1/token/revoke — blacklists a token by jti
- GET /v1/userinfo — returns the authenticated user profile claims
- Subscribes to `user-deleted` events and revokes all tokens for the user
- Emits `token-issued` and `token-revoked` events for audit pipeline

## Architecture

FastAPI HTTP server, entry point `src/api/main.py`. Kafka consumer in `src/consumers/user_events.py`. Postgres via SQLAlchemy (`src/db/`). Token signing uses ECDSA keys loaded from the secret manager at startup. Background revocation sweep in `src/jobs/sweep.py`, scheduled by APScheduler.

## Commands

```bash
# install
poetry install

# test
poetry run pytest
poetry run pytest tests/integration -m integration

# run locally
poetry run uvicorn auth_service.api.main:app --reload

# deploy
make deploy ENV=staging
```

## Gotchas

- Token signing keys rotate weekly. If you're testing locally, point `KEY_SOURCE=file` at `tests/fixtures/keys/` — production secret manager has request limits.
- The `jti` blacklist lives in Redis with a TTL matching the token expiry. **Never** set TTL longer than the token lifetime; the table will explode.
- We talk to user-service for `/userinfo` payload enrichment. If user-service is down, `/userinfo` falls back to claims-only — but `/token` requests still fail closed.
- Refresh-token rotation is atomic via a Postgres advisory lock. Don't replace with optimistic concurrency; we've burned on that before.

## Conventions

- Structured JSON logs only; correlation IDs propagated via `X-Request-Id`
- Typed errors at boundaries (`AuthError` subclasses), converted to HTTP at the edge
- Files: kebab-case (`token-issuer.py`). Functions: verb-first (`issue_token`).
- Tests next to source: `token_issuer.py` → `token_issuer_test.py`. No DB mocking — real Postgres via docker-compose.
- Config from env vars; required vars fail-fast at startup naming each missing one.
- Secrets from the secret manager only. Never in env vars in prod.
- REST: nouns in URLs, verbs in methods. Error responses: `{"error": {"code", "message"}}`.

## Reference

See `docs/` for:
- `docs/adrs/` — architecture decisions (ECDSA key rotation, refresh-token semantics)
- `docs/runbooks/` — on-call procedures (revoke-all, key-rotation, blacklist-cleanup)
- `docs/api/` — generated OpenAPI spec
```

---

## Why this is good

- **Purpose** is a positive definition of what the service IS, with the actual scope.
- **Features** are distinct, specific, and externally observable.
- **Architecture** names files an engineer can navigate to.
- **Commands** are copy-pasteable, grouped by purpose.
- **Gotchas** are non-obvious things — no engineer can infer them from the code.
- **Conventions** is a curated subset of the canonical file, inlined.
- **Reference** points to where deeper docs live, with one-line purposes.

Line count: ~70 content lines, ~95 total including headers and blank lines. Under the 150 cap with room to spare.
