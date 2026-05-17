# Team Lead — Stage 2: Spec Authoring

> Loaded on demand by Team Lead when the input is an informal request OR a story file without a technical layer. Covers **Phase -1** (spawning `kiat-tech-spec-writer`) and the **prompt hygiene** rules that govern the writer prompt.

If the input is an already-complete story file (both `## Business Context` and the technical sections present), **skip this stage entirely** and load `validation.md` instead.

---

## Phase -1 — Spec authoring (conditional, runs only on informal requests)

Team Lead is the single entry point for the user, so the input can be either an already-written story file OR a free-text request. Route deterministically:

| Input shape | Route |
|---|---|
| The user points to a path like `delivery/epics/epic-X/story-NN.md` AND that file exists AND it contains both a `## Business Context` section and the technical sections below (`## Acceptance Criteria (technical)` or equivalent) | Skip Phase -1, go straight to Phase 0a |
| The user gives free-text, OR points to a file that exists but has only `## Business Context` (no technical layer yet), OR the file doesn't exist yet | Enter Phase -1 |

**In Phase -1, spawn `kiat-tech-spec-writer` as a sub-agent via the `Agent` tool, in a single message**. Pass it:
- The user's raw request, verbatim
- The path of any existing story file the user referenced (even if incomplete — the writer may be in enrichment mode)
- A directive to return a structured handoff (see below)

The writer handles clarification rounds with the user-facing conversation through you — if it needs to ask a question, it returns a clarification message, you forward it to the user, and you pass the answer back in a follow-up spawn. You are the relay; the writer never talks to the user directly.

---

## Prompt hygiene — NEVER assert runtime/config facts from memory (CRITICAL)

**The most dangerous failure mode of Phase -1 is Team Lead stating a config/runtime/CI fact in the writer's prompt that turns out to be wrong.** The writer trusts Team Lead's prompt and writes the whole spec on top of that premise. Every downstream layer (coder, reviewer, CI) inherits the bad premise. By the time the bug surfaces, the story has been shipped.

The incident that triggered this rule: Team Lead wrote in a Phase -1 prompt "Playwright in CI runs test-auth only", while in reality the project's `Makefile` + `.github/workflows/ci.yml` both configure `ENABLE_TEST_AUTH=false` (real-Clerk) for the E2E suite. The spec-writer authored ACs for the wrong auth branch, the coder then silently deviated to match CI reality, and the reviewer rightfully flagged the drift as `NEEDS_DISCUSSION` — costing one arbitration cycle and a spec in-place patch.

**Rule**: before writing ANY prompt line that asserts a fact about CI, runtime env, build flags, test harness config, deployment targets, or infra — **Read the source of truth file first and cite the line number in your prompt**. If you cannot cite, you do not assert.

The categories where this rule is load-bearing:

| Fact you want to assert | Source of truth (verify BEFORE asserting) |
|---|---|
| CI auth mode (real-Clerk vs test-auth for E2E) | `Makefile` (look for `_test-e2e-run` target) + `.github/workflows/*.yml` (look for `ENABLE_TEST_AUTH` in the env block) |
| Venom auth mode | `Makefile` `_test-venom-run` target |
| Env var values in prod | `delivery/specs/deployment.md` + `infra/environments/prod/` |
| Build-time vs runtime env vars | `frontend/next.config.*` + `Makefile` dev-*/ test-* targets |
| Which workflow runs on which trigger | `.github/workflows/*.yml` `on:` blocks |
| Test runner shards / parallelism | `Makefile` + `playwright.config.*` + CI workflow matrix |
| Cloud Run revisions / domain routing | `infra/environments/*/main.tf` + `.github/workflows/deploy*.yml` |
| Which skill a coder auto-loads | the coder agent's frontmatter `skills:` field |
| Test helper exists (`signInAsUserA`, `newTestDB`, etc.) | `grep -rn "<helper-name>" frontend/e2e/ backend/venom/` — must return ≥ 1 hit at a usable definition site, not just at consumption sites |
| CSS token (`--nv-status-info-bg`, etc.) is defined | `grep -n "<token-name>" frontend/src/app/globals.css` — must return a `:root` definition |
| Lib version supports the API you're citing | `cat frontend/package.json \| jq '.dependencies."<pkg>"'` (or `go list -m <pkg>` for Go) — verify the major version supports the API; cross-check on the lib's changelog if the assertion touches a feature added recently |
| Upstream API shape (BODACC, INPI, OpenSanctions, AMF, etc.) | look for a sample JSON in `delivery/business/<domain>/` OR in the repo's fixtures (`backend/tests/venom/*/responses/`) — if no sample exists, INSTRUCT the writer to obtain one before writing ACs |
| Counter values (department codes, NAF count, regions, etc.) | `wc -l <file>` or `grep -c <pattern> <file>` against the canonical source; never quote a count from memory |

**Rationale for the 5 extended rows** (each cites a verbatim audit incident motivating the row):

- **Test helpers** — `SIGNINASUSERA_HELPER_NONEXISTENT` recurred 3 times across epic-09 stories A/B/C, and `helper newTestDB(t) does not exist in repo` hit epic-11 story-01 — 4 incidents total where the writer asserted a helper that no consumer site actually had a definition for. The fix is one grep at the definition site before the assertion lands in the prompt.
- **CSS tokens** — `TOKEN_SUBSTITUTION_NEW_PILLS` (epic-09 story-B) and `SPEC_PROSE_DEPT_COUNT_MISMATCH` (epic-09 story-A, both BE and FE mirrors) — 3 incidents in 2 stories — both came from quoting a token name the writer had never grepped against `globals.css`. A `:root`-anchored grep distinguishes "token exists" from "token is referenced elsewhere".
- **Lib versions** — `SENTRY-SDK-V8-NO-ROUTER-TRANSITION-OR-LOGS` (epic-15 story-04) cost a full AC rewrite when the writer cited a v9 API on a v8 SDK. `package.json` + the lib's changelog is the verification path; the major version alone is not enough when the assertion touches a recently-added feature.
- **Upstream API shape** — `story-05-opensanctions-fr-linked-pep-companies` racked up **13 deviations**, most due to misunderstood OpenSanctions topic-buckets. A sample JSON in `delivery/business/<domain>/` or in the fixtures folder grounds the AC; if no sample exists yet, the writer must obtain one before drafting ACs — never reason about an external API shape from memory.
- **Counter values** — `SPEC_PROSE_DEPT_COUNT_MISMATCH` (99 vs 107 INSEE codes) was cited twice in a single story, once on the backend side and once on the frontend mirror. A `wc -l` or `grep -c` against the canonical source is the only acceptable way to quote a count; memory-based counts are banned.

**Correct patterns**:

1. **Quote the source** in your prompt:
   > "CI runs Playwright in real-Clerk mode (`Makefile:<line-nn-mm>`: `ENABLE_TEST_AUTH=false NEXT_PUBLIC_ENABLE_TEST_AUTH=false`; `.github/workflows/ci.yml:<line-nn>`: `ENABLE_TEST_AUTH: "false"`). Write AC-T01 to assert the `Authorization: Bearer` shape."

2. **Delegate the verification to the writer** when you don't need the value yourself:
   > "Before drafting any AC that names an auth header, Read `Makefile` target `_test-e2e-run` and confirm the CI auth mode; assert the header that mode produces."

3. **Escalate to the user** when the source of truth is ambiguous or doesn't exist yet (new project, or a question of policy rather than fact).

**Anti-patterns (every one of these is a prompt-hygiene violation)**:

- "Playwright in CI runs test-auth only" (memory-based assertion — WRONG on this project)
- "The coder will need `lib/api/foo.ts` which already does X" (unverified file claim)
- "The backend dispatcher at `main.go:340` is auth-gated" (unverified line number — probably stale)
- "Story size is S" (this one is OK if you've read the story; not OK if you're guessing)
- "`signInAsUserA` helper just works" (unverified helper claim — grep the codebase first)
- "package X supports this API" (unverified version claim — check `package.json` + the lib's changelog)

**Enforcement**: before sending the writer prompt, re-read your own prompt and flag every factual claim about code, config, or CI. For each flagged claim, either cite a file+line you have Read, or rewrite the claim as a verification directive ("writer should check X before asserting Y"). If you catch yourself thinking "I'm pretty sure X is the case", that's the trigger to go Read — "pretty sure" is not good enough for downstream dev to inherit.

**Audit line** (always emit before spawning the writer):
```
Prompt hygiene: verified N factual claims against sources (<file>:<line>, <file>:<line>, ...), M claims delegated to writer for verification, 0 claims asserted from memory
```

The `<file>:<line>` placeholders in the example above are literal — replace them with the actual files and lines you Read during verification (e.g., `Makefile:42`, `.github/workflows/ci.yml:17`). Do NOT copy a line-number example from this prompt as if it were a verified value.

If N+M = 0 (prompt makes no factual claims), emit:
```
Prompt hygiene: prompt makes no runtime/config claims — nothing to verify
```

---

## Required writer handoff format

The writer's final message must start with these lines, parseable by you:

```
SPEC_HANDOFF
story_path: delivery/epics/epic-X/story-NN.md
mode: greenfield | enrichment
size: XS | S | M | L
spec_verdict: CLEAR
spec_byte_count: <integer — output of `wc -c story-NN.md`>
skills_added: <comma-separated list, or "none">
```

The writer's frontmatter pre-loads `kiat-validate-spec`, so by contract it will not return `SPEC_HANDOFF` until the skill says `CLEAR`. If the writer returns `BLOCKED` or cannot recover after two clarification rounds, it escalates back to you with `SPEC_HANDOFF_FAILED` — treat that as a `story_escalated` event with `escalated_to: "user"` and `reason: "spec_blocked"`.

**Record the writer's handoff values** in your working log — you need `story_path` and `spec_byte_count` at Phase 0a, and `size` + `skills_added` at Phase 0b.

**Audit line**:
```
Spec authoring: story-NN drafted by tech-spec-writer, verdict CLEAR, size S, 4812 bytes ✓
```
or on a direct-to-Phase-0a input:
```
Spec authoring: skipped — input is a complete story file
```
