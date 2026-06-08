# Org Conventions (Canonical Reference)

This is the full set of org-level conventions across stacks. Each repo's CLAUDE.md Conventions section should be a *curated summary* — pick the rules that apply to that repo's stack and runtime.

## Logging

1. Structured logs only (JSON). No `print`, no `console.log` in committed code.
2. Log levels: ERROR for actionable failures, WARN for degraded paths, INFO for state transitions, DEBUG for diagnostic detail. No INFO in hot loops.
3. Every log line must carry a correlation ID. Generate at the edge if absent; propagate via headers.
4. Never log secrets, tokens, PII. Use the shared redaction helper.

## Error handling

5. Throw typed errors at boundaries; convert to wire format at the edge (HTTP/queue).
6. Don't catch-and-swallow. If you catch, either re-throw or convert with reason.
7. Retries: only at the edge, only with backoff, only when the operation is idempotent.
8. Never use exceptions for control flow.

## Naming

9. Files: kebab-case for everything (`order-service.ts`, not `OrderService.ts`).
10. Functions/methods: verb-first (`processOrder`, not `orderProcessor`).
11. Types/classes: PascalCase, noun-form.
12. Constants: SCREAMING_SNAKE_CASE only for truly module-level invariants.

## Testing

13. Tests live next to source: `foo.ts` → `foo.test.ts`.
14. No mocking the database — use a real test instance (in-memory or docker).
15. Test names are full sentences: `it("rejects a duplicate order with a 409", ...)`.
16. No `sleep()` in tests. Use polling with a hard timeout.

## API design

17. REST: nouns in URLs, verbs in methods. `/orders` + POST, not `/createOrder`.
18. All responses are JSON. Error responses include `{ "error": { "code", "message" } }`.
19. Versioning lives in the URL path (`/v1/orders`). Breaking changes bump the major.
20. Pagination is cursor-based, never offset.

## Configuration

21. Config from env vars only. No config files committed.
22. Required env vars fail-fast at startup with a clear message naming each missing var.
23. Secrets come from the secret manager, never from env vars directly in prod.

## Frontend (React MFEs)

24. Components: function components only, no class components.
25. State: prefer local component state; lift only when proven necessary.
26. Side effects: in `useEffect` with explicit dependencies; never in render.
27. No CSS-in-JS for new components; use the shared design tokens.
