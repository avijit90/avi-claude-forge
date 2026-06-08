# tiny-service

## Purpose
A minimal HTTP service for the auth team.

## Features
- POST /healthz — returns 200
- POST /metrics — Prometheus scrape endpoint

## Architecture
Single-file Node Express app, `src/server.js`. No DB.

## Gotchas
- Port comes from `PORT` env var only. Don't hardcode.

## Conventions
- Logs JSON, correlation IDs from `X-Request-Id` headers.

## Reference
See `docs/` (none yet).
