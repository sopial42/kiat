# Backend Testing Pitfalls & Decisions (Venom API + Go Service Tests)

Living registry of pitfalls, best practices, and technical decisions for backend tests. Loaded by `kiat-backend-coder` and `kiat-backend-reviewer` when the story involves writing or modifying Venom YAML tests or Go service tests.

> **Relationship to other docs:**
> - [`testing.md`](testing.md) — Test pyramid structure, infra requirements, CI gate.
> - [`testing-playwright.md`](testing-playwright.md) — Playwright pitfalls (loaded by frontend agents).
> - [`smocker-patterns.md`](smocker-patterns.md) — The universal external-API mock pattern used by Venom AND Playwright. Go unit tests use in-process fakes (GS01) — NOT Smocker.
> - [`backend-conventions.md`](backend-conventions.md) — Project structure, naming, error codes.

---

## How to maintain this file

After each story that discovers a surprising backend test failure, add an entry. Number sequentially (VP01, VP02...). Template at the bottom.

**Size budget:** 4k tokens max. This file is loaded alongside the story spec — keep entries concise.

---

## Venom API pitfalls

### VP01: Venom lowercases all JSON keys in `bodyjson`

**Symptom:** Assertions on `result.bodyjson.fetchedAt` fail silently — Venom sees `fetchedat`.
**Rule:** Always use lowercased keys: `bodyjson.meta.fetchedat`, `bodyjson.data.sourcecoverage`, `bodyjson.error.code`.
**Prevention:** Run with `-vvv` and inspect actual key paths before writing assertions.

### VP02: Venom array access uses suffix notation, not brackets

**Symptom:** `bodyjson.data[0].code` fails — Venom doesn't support bracket syntax.
**Rule:** Use `bodyjson.data.data0.code`. Nested: `bodyjson.data.items.items0.code`.

### VP03: psql output needs `| trim` in variable extraction

**Symptom:** URL built with extracted ID fails: `/items/ abc-123\n` (trailing newline).
**Rule:** Always use `{{.variable | trim}}` when referencing psql-extracted variables. Use `psql -t -A` flags.

### VP04: Use UUID strings for X-Test-User-Id (not arbitrary strings)

**Symptom:** DB cleanup can't find rows — the auth middleware hashed the string into a UUID via sha256.
**Rule:** Use valid UUID strings (e.g., `11111111-0000-0000-0000-000000000001`). The test-auth middleware parses valid UUIDs directly without hashing, so DB `user_id` matches the header exactly. If your middleware hashes non-UUID strings, invalid UUIDs will silently diverge from what you seed — always use valid UUIDs.

### VP05: Cleanup first, seed second — in every testcase

**Symptom:** Test passes locally but fails in CI (dirty data from crashed previous run).
**Rule:** Every testcase starts with DELETE, then seeds. Never rely on teardown.
```yaml
- type: exec
  script: |
    psql "{{.db_dsn}}" -c "DELETE FROM audit_log WHERE user_id = '{{.user_id}}'::uuid;"
```

### VP06: Use `ShouldBeIn` for error codes that depend on Gin routing

**Symptom:** Test expects `400` but Gin returns `404` for malformed path params.
**Rule:** For invalid path params (SQL injection, empty), assert `ShouldBeIn 400 404`. The point is "not 500".

### VP07: Separate psql INSERT + RETURNING into its own step

**Symptom:** Variable extraction from multi-statement exec captures combined stdout.
**Rule:** Put `INSERT ... RETURNING id` in its own exec step with `psql -t -A ... | head -n1`.

### VP08: RLS verification in psql requires SET LOCAL inside a transaction

**Symptom:** Direct `SELECT` as superuser bypasses RLS — always returns all rows.
**Rule:** Wrap in a transaction with `SET LOCAL request.jwt.claim.sub = '<uuid>';` to simulate the RLS policy applied to a real authenticated request.

---

## Go service test pitfalls

### GS01: Service tests use httptest, not a real server

**Rule:** Colocated Go `_test.go` files wire a `gin.Engine` with `httptest.NewRecorder` (handler tests) or spin up a `httptest.Server` (adapter/fetcher tests). They never start the real `cmd/api` binary, never connect to a real DB, never call real upstream sources. Fakes and mocks only.

### GS02: Integration tests MUST be behind `//go:build integration`

**Rule:** Any test that needs a real DB connection uses the `integration` build tag. `make test-back` (`go test ./...`) must pass with zero containers running — this is a hard invariant for the Kiat test gate.

### GS03: Never use `t.Skip()` — use build tags

**Rule:** `kiat-test-patterns-check` Block F forbids `t.Skip()` in committed tests. Use `//go:build integration` instead — the test is either fully executed or fully absent, never silently skipped.

---

## Technical decisions

### TD01: Venom tests run against test-auth mode

**Decision:** `make test-venom` starts backend with `ENABLE_TEST_AUTH=true`. Venom uses `X-Test-User-Id` header.
**Rationale:** Venom has no browser — can't obtain a Clerk JWT.

### TD02: Every new endpoint MUST ship with Venom tests

**Decision:** No endpoint merged without a Venom suite covering: happy path, validation (400), auth (401), one security case (RLS or cross-tenant check).
**Enforcement:** Reviewer checks for `backend/tests/venom/<resource>/`.

### TD03: Test user IDs are valid UUIDs, unique per test file

**Decision:** Each file uses a unique UUID (e.g., `11111111-0000-0000-0000-000000000001`, `22222222-0000-0000-0000-000000000002`). No collision between files.
**Rationale:** Prevents cross-file state pollution. UUID format avoids sha256 hashing (VP04).

### TD04: Go tests colocated next to source code (standard Go convention)

**Decision:** Go `_test.go` files live next to the code they test: `handler/item_test.go` tests `item.go`. NOT in a centralized `venom/` or `tests/` directory.
**Rationale:** Standard Go. Developer finds tests next to code. No naming confusion with Venom CLI. `go test ./...` discovers tests in all packages.
**Rule for new code:** All new Go tests MUST be colocated. If a legacy centralized `backend/venom/` directory exists in an older codebase, migrate progressively — never add new tests there.

### TD05: Venom tests verify HTTP contracts, Go tests verify internal logic

**Decision:** Venom YAML tests (in `backend/tests/venom/`) verify the HTTP contract against a running backend (status codes, response shapes, headers, auth, DB state). Go service tests (colocated `_test.go`) verify handlers, usecases, and fetchers with httptest + fakes — no running server, no DB. Complementary layers, not overlap.

### TD06: Upstream sources go through Smocker in every non-prod mode

**Decision:** External upstream sources (third-party APIs the backend consumes) are mocked by **Smocker** in `make dev-offline`, `make test-venom`, and `make test-e2e`. The backend binary is unchanged — it's the production-shape artifact; only the `<SOURCE>_BASE_URL` env var is overridden to point at `http://localhost:8100/<slug>` in test modes. `make dev` is the only mode that hits the real APIs. See [`smocker-patterns.md`](smocker-patterns.md) for the full pattern.

**Rationale:**
- Offline-deterministic Venom runs (no rate limits, no flaky upstream, no 429).
- The production binary is what gets tested — every header, timeout, retry, and error-handling path is exercised against a real HTTP round-trip. No parallel in-process client to maintain.
- A shape drift upstream surfaces the next time a scenario is refreshed (see TD07). Error scenarios (503, timeout, malformed JSON) are trivial to inject via Smocker YAML.
- **Production guard in `cmd/api/main.go`**: `log.Fatal` if any `EXTERNAL_*_BASE_URL` contains `smocker`, `localhost:8100`, or `127.0.0.1:8100` when `ENV=production`.

**One pattern, not two.** Earlier drafts proposed a parallel in-process `FixtureClient` for Venom alongside Smocker for Playwright. That was simplified to Smocker-everywhere. See [`smocker-patterns.md`](smocker-patterns.md) section 1 for the full rationale — summary: one mental model across dev-offline/Venom/Playwright, better debuggability via Smocker admin UI, no drift between two mock sources, fewer production guards to maintain.

**Not applicable to Go unit tests** (see GS01): `go test ./...` doesn't run docker-compose, so colocated `_test.go` files inject a Go fake (a `struct` implementing the client interface) directly into the usecase. That pattern is orthogonal to Smocker and doesn't go through any env var.

### TD07: Venom tests assert every field the envelope exposes for a given contract

**Decision:** When a story makes the envelope responsible for a logical grouping of fields (e.g. a business-document endpoint that aggregates several upstream sources into one response), its Venom suite asserts **every field in a single HTTP call**, grouped under one testcase with a flat list of assertions. Use strict `ShouldEqual` (not `ShouldNotBeEmpty`) with the real captured values. Fields that should currently be `null` (because the upstream source does not expose them, or because a fallback source is disabled) are asserted as `ShouldBeNil` with a comment naming the gap.

**Rationale:**
- **One call, many assertions.** Avoids N round-trips for N fields (slow), avoids per-field boilerplate, and when the envelope drifts the failure report lists every divergent field in one pass.
- `ShouldNotBeEmpty` passes even when the mapper is silently wrong — strict equality catches it.
- `ShouldBeNil` + a comment is a documented gap, readable as a living spec. When a follow-up story wires the source, the assertion flips to `ShouldEqual <value>`.
- Group the assertions in the YAML with header comments per sub-object (`# -- identity ---`, `# -- metadata ---`, `# -- computed ---`) for readability. One fat happy-path testcase + separate testcases only for branches that need a different Smocker scenario.

**Scenario refresh workflow** (when upstream shape or values drift):
```bash
# 1. Capture from the real upstream
curl -s "https://<upstream>/<endpoint>?..." | jq '.' > /tmp/capture.json

# 2. Sanitize (strip secrets, anonymize identifiers), then edit the
#    matching Smocker scenario under frontend/e2e/fixtures/smocker/<source>.*.yml
#    to reflect the new shape / values.

# 3. Update the corresponding *.venom.yml assertions to match the new values.
# 4. Commit scenario + venom asserts together.
```

**Canonical template** — every envelope-wide Venom suite MUST follow this skeleton:

```yaml
name: <domain> - <logical grouping> (<epic> story-<NN>)
vars:
  base_url: "{{.venom.var.base_url}}"
  db_dsn: "{{.venom.var.db_dsn}}"
  user_id: "<UUID unique per file — see TD03>"
  # <Smocker scenario reference — primary_id + path to YAML scenario>
  primary_id: "<id>"

# ---------------------------------------------------------------------------
# One single HTTP call, all assertions grouped — every field the envelope
# exposes for <entity> is verified. If the capture drifts upstream, the
# testcase fails with all divergent fields in one pass.
# ---------------------------------------------------------------------------
testcases:

  - name: reset audit log
    steps:
      - type: exec
        script: |
          psql "{{.db_dsn}}" -c "DELETE FROM audit_log WHERE user_id = '{{.user_id}}'::uuid;"

  - name: envelope exposes every expected field for <entity> ({{.primary_id}})
    steps:
      - type: http
        method: GET
        url: "{{.base_url}}/api/<resource>/{{.primary_id}}"
        headers:
          X-Test-User-Id: "{{.user_id}}"
        timeout: 30
        assertions:
          # -- Envelope --------------------------------------------------------
          - result.statuscode ShouldEqual 200
          - result.bodyjson.data ShouldNotBeNil
          - result.bodyjson.meta ShouldNotBeNil

          # -- <sub-object A> (source <X>) -------------------------------------
          - result.bodyjson.data.<fieldA1> ShouldEqual "<captured value>"
          - result.bodyjson.data.<fieldA2> ShouldBeNil   # <source> does not expose it — follow-up

          # -- <sub-object B> (source <Y>) -------------------------------------
          - result.bodyjson.data.<collection> ShouldHaveLength <n>
          - result.bodyjson.data.<collection>.<collection>0.<field> ShouldEqual "<value>"

          # -- <sub-object C — source disabled, asserted null> -----------------
          - result.bodyjson.data.<fieldC> ShouldBeNil
```

**Rules that MUST hold** (reviewer checklist, verbatim — these are the non-negotiable invariants behind TD07):

1. **Exactly one `type: http` step** per happy-path testcase. No per-field HTTP calls.
2. **Strict equality** (`ShouldEqual`, `ShouldHaveLength`, `ShouldBeNil`) — never `ShouldNotBeEmpty` / `ShouldNotBeNil` on fields where the Smocker scenario gives us a known value.
3. **Captured values**, not invented ones. Pull them from the Smocker scenario response body under `frontend/e2e/fixtures/smocker/<source>.*.yml` — the scenario is the source of truth for assertions.
4. **Null fields are asserted as `ShouldBeNil`**, never omitted. Each `ShouldBeNil` carries an inline comment naming the reason (source gap, disabled fetcher, follow-up story).
5. **Section comments** (`# -- <name> (source <X>) ---`) group assertions by sub-object.
6. **One scenario, one happy-path testcase.** Additional testcases only for variants that need a different Smocker scenario (e.g. "entity with empty collection", "entity with flag set"). Those testcases reuse the exact same structure.

---

## Pitfall template

```markdown
### VPNN / GSNN: <short title>

**Symptom:** <what went wrong>
**Rule:** <what to do instead>
**Prevention:** <how to catch this before it happens>
```

---

See also:
- [testing.md](testing.md) — Test pyramid, Venom YAML format, infra requirements
- [testing-playwright.md](testing-playwright.md) — Playwright E2E pitfalls
- [smocker-patterns.md](smocker-patterns.md) — External API mocking for E2E
- [clerk-patterns.md](clerk-patterns.md) — Test-auth bypass protocol
- [security-checklist.md](security-checklist.md) — RLS testing
