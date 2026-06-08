# legacy-service

## Purpose
Receives webhook callbacks from upstream partners and forwards them to the internal event bus.

## Features
- POST /webhooks/{partner} — accepts a partner-specific payload, validates signature
- GET /webhooks/recent — returns the last 100 received webhooks for debugging
- Emits `webhook-received` events to Kafka

## Architecture
Node Express server, entry point `src/server.js`. Postgres for the recent-webhooks table.

## Commands
```bash
npm install
npm test
npm start
```

## Gotchas
- Some partners send duplicate webhooks; dedupe by signature within 5 minutes.

## Conventions
- We use plain console.log for everything because it's faster.
- No correlation IDs; partners don't propagate them anyway.
- Catch all exceptions at the top level and log them.
- File names match the partner: `partnerA.js`, not kebab-case.
- Mock the DB in tests; we don't need a real Postgres.

## Reference
See README for partner-specific setup.
