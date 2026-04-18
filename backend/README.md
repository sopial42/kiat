# Backend — Go + Gin + Bun + Clean Architecture

> **Status**: Skeleton placeholder. The working code will land in EPIC 00 (see [`delivery/epics/epic-00/`](../delivery/epics/epic-00/)).

## Planned structure

```
backend/
├── cmd/
│   └── api/
│       └── main.go                        # entrypoint — production guards in init()
├── internal/
│   ├── domain/                            # Layer 1 — pure domain entities, no deps
│   │   └── item/                          # canonical example resource (rename per project)
│   │       └── item.go
│   ├── application/                       # Layer 2 — use cases, orchestration
│   │   └── item/
│   │       ├── create_item.go
│   │       └── create_item_test.go        # colocated (TD04)
│   ├── infrastructure/                    # Layer 3 — adapters (DB, external APIs)
│   │   ├── persistence/
│   │   │   └── bun/
│   │   │       └── item_repository.go
│   │   └── clerk/
│   │       └── jwt_validator.go
│   └── interface/                         # Layer 4 — handlers, middleware, routing
│       ├── handler/
│       │   └── item_handler.go
│       ├── middleware/
│       │   ├── auth.go                    # Clerk JWT validation
│       │   ├── test_auth.go               # X-Test-User-Id (guarded out of prod)
│       │   └── cors.go                    # emits Access-Control-Expose-Headers
│       └── router/
│           └── router.go
├── external/
│   └── sources/                           # third-party API HTTP clients
│       └── <source-slug>/
│           ├── client.go                  # production client, reads EXTERNAL_<SLUG>_BASE_URL
│           └── client_test.go             # colocated unit tests, inject a FakeHTTPClient (GS01)
├── migrations/                            # SQL migrations (RLS policies included)
├── tests/
│   └── venom/                             # Venom YAML black-box HTTP tests
│       └── <resource>/
│           └── <resource>.venom.yml
└── go.mod
```

## Layer rules (enforced by `kiat-backend-reviewer`)

See [`delivery/specs/architecture-clean.md`](../delivery/specs/architecture-clean.md) for the full spec. Headline:
- Outer layers depend on inner layers; **never the reverse**.
- `domain/` has zero external imports (no Gin, no Bun, no Clerk SDK).
- `application/` depends on `domain/` interfaces, never on infrastructure.
- `infrastructure/` implements interfaces declared in `application/`.
- `interface/` (handlers) depends on `application/` — never on infrastructure directly.

## Production guards (MANDATORY in `cmd/api/main.go`)

At binary startup, `init()` MUST `log.Fatal` on any of these misconfigurations when `ENV=production`:

- `ENABLE_TEST_AUTH=true`
- Any `EXTERNAL_*_BASE_URL` containing `smocker`, `localhost:8100`, or `127.0.0.1:8100` (Smocker leaked into prod)
- `DATABASE_URL` containing `localhost` or `127.0.0.1`

This is non-negotiable. Every new test-mode env var MUST ship with its matching guard in the same commit. See [`../delivery/specs/smocker-patterns.md`](../delivery/specs/smocker-patterns.md) section 7 for the canonical guard implementation.

## Testing

Two backend test layers live here (see [`../delivery/specs/testing.md`](../delivery/specs/testing.md)):

| Layer | Tool | Runner | Location | External API mocking |
|---|---|---|---|---|
| Unit + handler | Go `testing` + `httptest` | `make test-back` (`go test ./...`) | colocated `*_test.go` (TD04) | In-process fakes (GS01) — `FakeHTTPClient` struct injected in test |
| Black-box HTTP | Venom YAML | `make test-venom` | `backend/tests/venom/` | Smocker (TD06) — real HTTP, out-of-process, shared scenarios with E2E |

Venom runs in test-auth mode (`ENABLE_TEST_AUTH=true`, UUID-only user IDs — see [`testing-pitfalls-backend.md:VP04`](../delivery/specs/testing-pitfalls-backend.md)), with every `EXTERNAL_*_BASE_URL` routed to Smocker (`http://localhost:8100/<slug>`). See [`../delivery/specs/smocker-patterns.md`](../delivery/specs/smocker-patterns.md) for the full pattern.

## Where this code comes from

EPIC 00 (bootstrap) materializes this skeleton. Subsequent epics ship business features on top.

The **tech-spec-writer** does NOT invent the structure above; it comes from the contract enforced by `kiat-backend-coder` + `kiat-backend-reviewer` + `delivery/specs/`. When in doubt, read the relevant spec in `delivery/specs/`.
