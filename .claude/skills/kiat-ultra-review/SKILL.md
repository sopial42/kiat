---
name: kiat-ultra-review
description: >
  Pre-prod / pre-cutover multi-phase audit orchestration. Use this skill
  when a project approaches production deployment and the human needs a
  systematic, defensive review across all dimensions (security, code
  quality, infra, CI/supply chain, DB/RLS, docs, ops readiness), with
  multiple competing remediation plans, and an adversarial meta-review
  to spot blind spots before settling on a final plan. Distinct from
  per-story review skills (`kiat-review-backend`, `kiat-review-frontend`)
  which gate a single diff — this skill audits the whole codebase as it
  stands and produces a cutover plan, not a verdict on a PR.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
  - Agent
---

# Ultra-Review — Pre-Prod Multi-Phase Audit

## Why this skill exists

Per-story reviews catch *individual* defects in *individual* PRs. They do not catch the cumulative-state question: "is this whole project actually ready for production right now, across every dimension, and what's the cheapest plan to close the remaining gaps?"

That question requires a different cadence:
1. **Multi-axis parallel audit** — code, infra, DB, CI, docs, ops, security each get an independent expert pass, because a single agent loaded with all axes loses focus and audits everything shallowly.
2. **Multiple competing plans** — "minimal viable / defensive / belt-and-suspenders" — because the *first* plan an agent produces almost always reflects its priors, and side-by-side competing plans expose those priors explicitly.
3. **Adversarial meta-review** — a cynical pass + an edge-case-hunter pass — because plan authors fall in love with their plans. The meta-reviewers are not asked to produce a plan, only to break the existing ones.
4. **Final synthesis** — a single plan that picks the least-wrong base and grafts the fixes the meta-reviewers identified as cross-plan gaps.

The skill encodes that protocol so the next pre-cutover audit doesn't have to reinvent it.

## When to invoke

- A Kiat project is preparing a cutover to production for the first time.
- A major epic just closed that changed the operational surface (auth, persistence, deployment pipeline, RLS, IAM) and you want a fresh end-to-end audit before the next release.
- The human asks for an "ultra review", "pre-prod audit", "cutover readiness check", or equivalent.
- An external regulator or compliance review is scheduled (LCB-FT, RGPD, SOC2 audit prep).

**When NOT to invoke**:
- Reviewing a single PR or diff — use `kiat-review-backend` / `kiat-review-frontend` / `differential-review` instead.
- Reviewing a single story's spec — use `kiat-validate-spec`.
- Reviewing one specific dimension (e.g., "just the security") — invoke the matching specialised skill directly or spawn a single audit agent (Phase 1 only, single axis).

## Input

- Project root path (default: current working directory).
- Optional scope filter:
  - `axis=backend|frontend|infra|ci|db|docs|ops|all` (default `all`)
  - `plans=A,B,C` or `plans=B` (default `A,B,C` — full 3-plan run)
  - `meta=cynical,edge-case` or `meta=cynical` (default both)

## Output

All artefacts written under `_bmad-output/ultra-review/` (gitignored by Kiat default — these are working drafts, not shippable):

```
_bmad-output/ultra-review/
├── findings/
│   ├── 01-backend.md
│   ├── 02-frontend.md
│   ├── 03-infra.md
│   ├── 04-ci-supply-chain.md
│   ├── 05-database.md
│   ├── 06-docs.md
│   └── 07-ops-readiness.md
├── plans/
│   ├── plan-A-minimal.md
│   ├── plan-B-defensive.md
│   └── plan-C-belt.md
└── final/
    ├── meta-review-cynical.md
    ├── meta-review-edge-case.md
    └── plan-final.md
```

The shippable artefact is the **final plan transcribed into Kiat story specs** under `delivery/epics/epic-NN-pre-prod-cutover/` (one story per remediation theme, Business Context + AC + Skills tag + pointer to `plan-final.md` for technical detail). The orchestrator session is responsible for that transcription — see "After the audit" below.

## Severity scheme (used by all Phase 1 audit agents)

| Severity | Definition |
|---|---|
| **S0** | Blocks prod. Faille exploitable, panne user-facing certaine, perte de données, non-conformité légale claire (LCB-FT / RGPD / regulatory). |
| **S1** | Must-fix pré-prod. Sécu importante, dette opérationnelle visible sous charge, doc qui ment sur la sécu. |
| **S2** | Post-prod cycle 1. Qualité de code, edge cases, hygiène. |
| **S3** | Nice-to-have. Polish, style, refactor cosmétique. |

Every finding S0 / S1 **must cite** `file:line` (or `workflow:job:step` for CI). Without a cite it's not a finding — it's an opinion.

## Phase 1 — Parallel multi-axis audit

Spawn 7 audit agents **in parallel** (one single tool message with multiple `Agent` invocations). Each agent gets:
- A scope (paths + relevant `delivery/specs/` files for the project's conventions)
- A checklist of what to look for (per-axis, see below)
- The severity scheme above
- Output path : `_bmad-output/ultra-review/findings/<NN>-<axis>.md`
- A length cap (~350-400 lines markdown, no exhaustive S3 listing)
- A formal verdict GO / NO-GO / GO-WITH-CAVEATS at the end

### Standard 7 axes

| # | Axis | Checklist priorities |
|---|---|---|
| 01 | Backend (code) | OWASP, auth bypass, panics in goroutines, error handling, concurrency, N+1, Clean Architecture violations |
| 02 | Frontend (code) | XSS via `dangerouslySetInnerHTML`, tokens in client bundle, RSC boundary, hooks, a11y, design system drift |
| 03 | Infra (IaC) | Secrets in code, IAM over-privilege, public ingress, PITR off, deletion protection, disk autoresize cap, alerting policies, Dockerfile hygiene |
| 04 | CI / supply chain | Workflow permissions, action SHA pinning, mutable image tags, `:latest`, deps lockfile, `pull_request_target`, secrets in CI logs |
| 05 | Database | RLS coverage, policies coverage SELECT+INSERT+UPDATE+DELETE, FK indexes, migrations reversibility, append-only grants, PII columns |
| 06 | Docs | Code-vs-doc drift, contradictions between specs, security doc accuracy, runbook completeness, README onboarding |
| 07 | Ops readiness | Structured logging, /healthz vs /readyz, metrics, tracing, alerting, runbook, kill-switches, error.tsx FE boundary |

Each axis can be **dropped** if `scope=axis-filter` excludes it. Default = all 7.

### Standard audit-agent prompt template

```
You are a senior <axis> auditor. Pre-prod audit of <project-name>.

## Scope
<repository absolute paths>

## Conventions
Read (short) these spec files to calibrate expectations:
<delivery/specs/*.md relevant to this axis>

## Checklist
<axis-specific bullet list, ~10 items>

## Output format
Write a single file: `<project-root>/_bmad-output/ultra-review/findings/<NN>-<axis>.md`
- Executive summary (3-5 bullets)
- Findings table (ID, Severity, File:line, Category, Description, Recommandation)
- Top 3 must-fix (S0/S1)
- Verdict prod (GO | NO-GO | GO-WITH-CAVEATS)

## Constraints
- NE LANCE PAS de build/test (pure static analysis).
- Cap ~350-400 lignes. Cite file:line on every S0/S1.
- Report a < 200 word summary back after writing the file.
```

## Phase 2 — Three competing plans

After all Phase 1 agents complete, spawn 3 plan agents **in parallel**. Each reads **all** finding files in full (not summaries) and produces a single plan from a distinct philosophy.

| Plan | Philosophy | Includes | Defers |
|---|---|---|---|
| **A — Minimal Viable** | "Ship now, harden in flight." Risk-acceptance posture. | S0 only | S1, S2, S3 |
| **B — Defensive** | "Ship without immediate regret." Refuse to navigate blind. | S0 + S1 + S2 critical to first on-call | S2 non-critical + S3 |
| **C — Belt-and-Suspenders** | "Do it right or don't do it." | S0 + S1 + S2 | S3 only, documented |

Each plan must include:
- Philosophy & assumptions paragraph
- Must-fix table grouped by axis
- Stories proposed (Kiat-able shape — title, scope, AC, estim, deps, skills)
- Risk-accept log (every S0/S1 NOT included → explicit one-line justification)
- Budget total
- Cutover hypotheses (smoke tests, rollback, comms)

## Phase 3 — Adversarial meta-review

Spawn 2 meta-review agents **in parallel**. Each reads the 3 plan files **and** the 7 finding files, and produces an adversarial critique.

### Cynical meta-review

Attitude-driven, opinionated. Looks for:
- Over-engineering disguised as defense-in-depth
- Under-engineering disguised as YAGNI
- Estimates that smell of optimism
- Hidden dependencies between "parallel" stories
- Risk-accepts that aren't quantified
- Compliance gaps in regulated projects (LCB-FT, RGPD, HIPAA, PCI)
- Buffer absent or wildly inflated
- Sequencing wrong (e.g., "runbook" planned before "rollback test" it depends on)

### Edge-case meta-review

Method-driven, orthogonal to attitude. For each plan, applies 6 systematic angles:
1. **Operational scenarios** — 10 concrete incident scenarios; does this plan let you detect AND fix each?
2. **Boundary analysis** — what fails when a new endpoint / handler / source is added post-cutover?
3. **Cycles & ordering** — which "parallel" stories actually depend on each other?
4. **Done-criteria validity** — "X activated" vs "X tested in restore"; flag the ambiguous ones
5. **Regression introduced by the fix** — `safeGo` masks errors? CSP strict breaks dependency? new probe path breaks legacy LB?
6. **Compliance & legal** — 5-year audit, right-to-erasure, data breach notification, data residency

Both meta-reviews end with **cross-plan gaps** — items no plan addresses. These become the orchestrator's grafts in the final plan.

## Phase 4 — Final plan synthesis

The orchestrator session (not a sub-agent — synthesis requires holding all artefacts) writes `final/plan-final.md`:

- Pick the **least-wrong** plan as base (usually B, sometimes A or C — argue explicitly with citations from the meta-reviews)
- Promote cross-plan gaps the meta-reviews identified to the final must-fix list, even if the chosen plan didn't include them
- Introduce **non-negotiable gates** (3-5 max) that all plans missed — these are the test-of-reality items ("X tested in restore" vs "X activated")
- Update budget with explicit buffer (~25%)
- Document the diff vs the chosen base plan
- List explicit risk-accepts for everything else (with rationale)
- Sequence + parallelisation map
- Comms / go-no-go criteria for cutover

## After the audit — transcription to Kiat stories

The audit artefacts are **drafts**, not deliverables. The shippable form is a Kiat epic + stories.

The orchestrator session creates `delivery/epics/epic-NN-pre-prod-cutover-followup/` with:
- `_epic.md` (Business Context, slicing plan, epic-level AC, link back to `_bmad-output/ultra-review/`)
- One story file per remediation theme — Business Context + user-facing AC + Skills tag pre-filled, technical sections (AC technical / Specification / Testing Plan) **left empty** with a pointer to the relevant `plan-final.md` section.

This split is intentional: the audit produces high-bandwidth analysis; the story files re-enter the standard Kiat per-story flow (Team Lead → tech-spec-writer → coders → reviewers). Bypassing tech-spec-writer would skip its `kiat-validate-spec` gate.

## Worked example

The first complete run of this protocol was executed on the Robia project (May 2026) — see commit `430036c` on branch `chore/ultra-review-followup` for the epic + 6 story stubs produced from a 7-axis audit + 3 plans + 2 meta-reviews. The full set of artefacts is documented under `_bmad-output/ultra-review/` in that branch (gitignored — not visible after merge).

Key numbers from the worked example:
- 7 audits — ~1.5h cumulative agent time, ~750k tokens
- 3 plans — ~25 min cumulative, ~270k tokens
- 2 meta-reviews — ~12 min, ~200k tokens
- Final synthesis — orchestrator session, no sub-agent
- 6 stories produced (1 originale déjà mergée hors-protocole — pas re-spec'd)

## Anti-patterns

- **Don't load all 7 axes into one agent** — context blows up, every axis gets shallow attention. The whole point is parallel specialised attention.
- **Don't skip Phase 3 because "the 3 plans look good enough"** — meta-review consistently surfaces gaps both plans share, which is exactly the failure mode the protocol exists to catch.
- **Don't transcribe the plan-final into stories that already have the technical sections filled** — that bypasses tech-spec-writer and `kiat-validate-spec`. The stories should be Business-Context-only stubs.
- **Don't run this skill on every release** — it's a cutover / major-milestone tool. For per-PR review, use the diff-scoped review skills.
- **Don't merge a plan-final that has < 3 non-negotiable gates** — if you find < 3, you probably haven't found them yet. Re-read the meta-reviews.
