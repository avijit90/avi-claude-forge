# Feature detection heuristics

The drafting skill auto-detects what it can from the repo. Auto-detection is RELIABLE only for the **Commands** section. Everything else needs user input.

## Stack detection

Probe order (first match wins; multiple matches → AskUserQuestion):

| File present | Stack |
|---|---|
| `package.json` | Node |
| `pom.xml`, `build.gradle`, `build.gradle.kts` | JVM |
| `pyproject.toml`, `setup.py`, `requirements.txt` | Python |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `Gemfile` | Ruby |

## Commands extraction

### Node (package.json)

Read `scripts` object. Translate keys to standard commands:
- `test`, `test:*` → test commands
- `build`, `compile` → build commands
- `start`, `dev`, `serve` → run commands
- `lint`, `lint:fix` → quality commands

Also include `npm install` as the install step.

### JVM (Maven / Gradle)

Maven: prefer `./mvnw` if the wrapper is committed (`mvnw` script + `.mvn/wrapper/` dir present); otherwise `mvn`. Examples: `mvn clean install`, `mvn test`, `mvn spring-boot:run` (if `spring-boot-starter` in pom.xml).

Gradle: prefer `./gradlew` if the wrapper is committed (`gradlew` script + `gradle/wrapper/` dir present); otherwise `gradle`. Examples: `gradle build`, `gradle test`, `gradle bootRun` (Spring Boot) or `gradle run`.

**Auto-detection rule:** check for the wrapper script. If absent, emit the bare command (`mvn`/`gradle`). Emitting `./mvnw` against a repo that doesn't ship the wrapper produces a non-runnable command — exactly the failure mode the rubric's "copy-pasteable Commands" criterion is meant to catch.

### Python

If `pyproject.toml` with poetry: `poetry install`, `poetry run pytest`, etc.
If `requirements.txt`: `pip install -r requirements.txt`, `pytest`.
If a `[scripts]` table exists: surface it.

### Rust

`cargo build`, `cargo test`, `cargo run`.

### Go

`go build ./...`, `go test ./...`, `go run ./cmd/<binary>`.

## Entry-point detection (Architecture starter)

For each stack, look for the typical entry point and name it:

| Stack | Typical entry point file |
|---|---|
| Node (Express) | `src/server.js`, `src/index.js`, `src/app.ts` |
| Node (NestJS) | `src/main.ts` |
| JVM (Spring Boot) | Class with `@SpringBootApplication` |
| Python (FastAPI) | File with `app = FastAPI()` |
| Python (Django) | `manage.py`, `wsgi.py` |
| Go | `cmd/<binary>/main.go` |
| Rust | `src/main.rs` or `src/lib.rs` |

Use Grep to find the marker (`@SpringBootApplication`, `app = FastAPI`, etc.).

## What NOT to auto-detect

- Features. The repo's externally visible capabilities cannot be derived from code structure. Always ask.
- Architecture intent. The starter shape from the tree is just a hint — the user owns the final phrasing.
- Gotchas. By definition non-obvious; cannot be extracted.
- Conventions selection. The user knows which rules apply.
- Purpose. The repo's reason to exist is a human framing decision.
