# 🚀 Kiat — Starter Kit Agent-First SaaS

> **The vision**: Humans interface with AI through natural conversation. BMAD Master writes specs. Agents code in parallel. Everyone debugs. Tests gate merges. Done.

This is a **generic, reusable starter kit** for building SaaS with:
- **Go + Gin + Bun ORM** backend (Clean Architecture)
- **Next.js App Router + Shadcn/UI + React Query** frontend
- **Clerk** authentication
- **Agent-first workflow**: BMAD for product decisions, parallel coder/reviewer/test agents, human approval gates

---

## 🎯 The Vision: Why Kiat?

### Problem We're Solving
1. **Spec fragmentation**: Specs live in 5 places, agents miss context → duplicate errors
2. **Agent coordination**: No clear "when do I use this skill?" → wasteful context, missed optimizations
3. **Infinite loops**: Reviewer finds issue → coder fixes → reviewer finds new issue (no convergence)
4. **Context explosion**: Agents loaded with entire codebase → token waste, slower thinking
5. **Test gates unclear**: "Is this tested enough?" → subjective, non-gated merges

### Our Solution
- **Single source of truth** per artifact (specs, architecture, testing patterns)
- **Smart context injection** (agent loads only what it needs via @file-context + @skills)
- **3-way review verdicts + time-budgeted retries** (no more "max 2 cycles" fairytale — see [Enforcement Model](#-enforcement-model-how-we-make-agents-actually-follow-rules))
- **Pre-coding validation gates** (spec ambiguity + kiat-test-patterns-check caught before any coder is launched)
- **Parallelizable workflow** (BMAD writes while coders wait; stories processed in parallel)
- **Automated test gates** (Playwright in CI blocks merge until ✅)
- **Observability from day one** (JSONL event log + markdown health reports — see [Monitoring & Reporting](#-monitoring--reporting))

---

## 🏗️ Architecture at a Glance

Two diagrams below: **Diagram A** shows the flow of a single story through the agents; **Diagram B** shows which skills each agent loads at which moment.

### Diagram A — Agentic Flow (per story)

```
┌──────────┐
│   USER   │
└────┬─────┘
     │ "I want feature X"
     ▼
┌─────────────────────────┐
│       BMAD MASTER       │  Métier / product agent (not part of Kiat — BYO)
│  Challenges, writes     │
│  story spec             │
└────┬────────────────────┘
     │ delivery/epic-X/story-NN.md
     ▼
╔══════════════════════════════════════════════════════════════════╗
║                     kiat-team-lead                                ║  ◄─── Entry point for Kiat
║  ┌────────────────────────────────────────────────────────────┐  ║
║  │ Phase 0a — run kiat-validate-spec                          │  ║
║  │ ├─ CLEAR ──────────────────────────────────┐               │  ║
║  │ ├─ NEEDS_CLARIFICATION ── ▶ back to BMAD ──┘ (≤ 2 rounds)  │  ║
║  │ └─ BLOCKED ─────────────▶ ESCALATE to user                 │  ║
║  │                                                             │  ║
║  │ Phase 0b — pre-flight context budget (wc -c / 4)           │  ║
║  │ ├─ pass ──────────────────────────────────┐                │  ║
║  │ └─ overflow ──────────▶ back to BMAD for split request     │  ║
║  └───────────────────────────────────────────┼────────────────┘  ║
║                                               │                    ║
║                    ┌──────────────────────────┴──┐                ║
║                    ▼                             ▼                ║
║  ┌──────────────────────────┐  ┌──────────────────────────┐      ║
║  │   kiat-backend-coder     │  │   kiat-frontend-coder    │      ║
║  │   (runs in parallel)     │  │   (runs in parallel)     │      ║
║  │ Step 0:   budget self-ck │  │ Step 0:   budget self-ck │      ║
║  │ Step 0.5: test-patterns  │  │ Step 0.5: test-patterns  │      ║
║  │ Step 1-5: plan, build,   │  │ Step 1-5: plan, build,   │      ║
║  │           test, handoff  │  │           test, handoff  │      ║
║  └───────────┬──────────────┘  └───────────┬──────────────┘      ║
║              │ "code ready"                │ "code ready"         ║
║              ▼                             ▼                      ║
║  ┌──────────────────────────┐  ┌──────────────────────────┐      ║
║  │  kiat-backend-reviewer   │  │  kiat-frontend-reviewer  │      ║
║  │ runs kiat-review-backend │  │ runs kiat-review-frontend│      ║
║  │ + conditional clerk-auth │  │ + conditional clerk-auth │      ║
║  │ verifies test-patterns   │  │ verifies test-patterns   │      ║
║  └───────────┬──────────────┘  └───────────┬──────────────┘      ║
║              │ VERDICT:                    │ VERDICT:             ║
║              ▼                             ▼                      ║
║   ┌──────────────────────────────────────────────────┐           ║
║   │  Team Lead parses first line of each verdict:    │           ║
║   │                                                   │           ║
║   │  APPROVED ─────────────▶ Phase 5/6/7             │           ║
║   │                                                   │           ║
║   │  BLOCKED  ─────▶ aggregate issues, send to       │           ║
║   │                  coder (45-min fix budget)       │           ║
║   │                  ◀── re-cycle until APPROVED     │           ║
║   │                                                   │           ║
║   │  NEEDS_DISCUSSION ──▶ Team Lead arbitrates        │           ║
║   │                       or escalates to BMAD/user  │           ║
║   │                       (never back to coder)      │           ║
║   └──────────────────────────┬───────────────────────┘           ║
║                              │                                    ║
║                              ▼                                    ║
║   ┌──────────────────────────────────────────────────┐           ║
║   │  Phase 7 — Emit ONE rollup event                 │           ║
║   │  • story_rollup (success)                        │           ║
║   │  • story_escalated (escalation)                  │           ║
║   │  → delivery/metrics/events.jsonl (append)        │           ║
║   └──────────────────────────┬───────────────────────┘           ║
╚══════════════════════════════╪═══════════════════════════════════╝
                               │
                               ▼
                  ┌────────────────────────┐
                  │  Story PASSED / Merge  │
                  └────────────────────────┘

                  ... weekly ...
                               │
                               ▼
                  ┌────────────────────────────┐
                  │  python3 report.py         │
                  │  → health report (md)      │
                  └────────────────────────────┘
```

**Reading the diagram:** solid lines = normal flow. Every dotted-line escalation path exits the Kiat boundary (the double-walled box) — those are the moments where humans or BMAD step in. The rollup event at Phase 7 is the ONE write Team Lead does per story, and it's the exit marker.

### Diagram B — Skill Loading Map (who loads what when)

```
KIAT AGENTS                          SKILLS (loaded on invocation)
───────────                          ──────────────────────────────

                                     ┌─ kiat-validate-spec         ◄─ Phase 0a
kiat-team-lead   ─── invokes ───▶    │
                                     └─ (no others — Team Lead has
                                        no skills of its own)

                                     ┌─ kiat-test-patterns-check   ◄─ Step 0.5
kiat-backend-coder   ─── invokes ──▶ │   ├─ SKILL.md (router)
                                     │   └─ blocks/block-*.md
                                     │       (selective: only the
                                     │        ones matching scope)
                                     │
                                     └─ (and community skills per
                                        story: sharp-edges, etc.)

                                     ┌─ kiat-test-patterns-check   ◄─ Step 0.5
kiat-frontend-coder   ─── invokes ─▶ │   ├─ SKILL.md (router)
                                     │   └─ blocks/block-*.md
                                     │       (selective)
                                     │
                                     └─ (community skills per
                                        story: react-best-practices,
                                        composition-patterns, etc.)

                                     ┌─ kiat-review-backend        ◄─ REQUIRED
                                     │   (runs on every review)
kiat-backend-reviewer ── invokes ──▶ │
                                     ├─ kiat-clerk-auth-review     ◄─ CONDITIONAL
                                     │   (runs IF diff touches
                                     │    auth-adjacent code —
                                     │    hard trigger rule)
                                     │
                                     └─ differential-review        ◄─ OPTIONAL
                                         (security-critical PRs)

                                     ┌─ kiat-review-frontend       ◄─ REQUIRED
                                     │   (runs on every review)
                                     │
                                     ├─ kiat-clerk-auth-review     ◄─ CONDITIONAL
kiat-frontend-reviewer── invokes ──▶ │   (same hard trigger rule)
                                     │
                                     ├─ react-best-practices       ◄─ OPTIONAL
                                     ├─ composition-patterns       ◄─ OPTIONAL
                                     └─ web-design-guidelines      ◄─ OPTIONAL


AMBIENT CONTEXT (loaded by EVERY agent, always)
───────────────────────────────────────────────
  CLAUDE.md              ◄─ Universal meta-rules for
                                         any Claude instance +
                                         framework/project separation
                                         rule + pointers


FRAMEWORK SPECS (loaded only by Team Lead)
──────────────────────────────────────────
  .claude/specs/context-budgets.md    ◄─ Consulted at Phase 0b
  .claude/specs/metrics-events.md     ◄─ Consulted at Phase 7
  .claude/specs/failure-patterns.md   ◄─ Consulted at escalation time


PROJECT CONVENTIONS (loaded on-demand per task)
───────────────────────────────────────────────
  delivery/specs/*.md                 ◄─ Coders + reviewers load the
                                         specific conventions they
                                         need for the current task.
                                         NOT all loaded — selective
                                         per story scope.
```

**Key rules captured by Diagram B:**

- **`kiat-team-lead` has zero skills of its own** — it's pure orchestration. It only invokes `kiat-validate-spec` at Phase 0a. Every other skill is owned by downstream agents.
- **`kiat-test-patterns-check` loads selectively** — the router (`SKILL.md`) is always loaded by coders, but the 9 pattern blocks are loaded individually based on story scope (usually 3-5 blocks per story, not all 9).
- **`kiat-clerk-auth-review` has a hard trigger rule** — reviewers MUST invoke it if the diff touches any auth-adjacent pattern (grep-based trigger list). This is the enforcement mechanism for cross-layer auth bugs.
- **Community skills are NOT Kiat-owned** — they're third-party expertise libraries (`react-best-practices`, `composition-patterns`, `differential-review`, etc.). Kiat agents can invoke them but doesn't guarantee their behavior.
- **CLAUDE.md is the only truly global ambient** — every Kiat agent has it in context, but it's minimal (88 lines) and contains only meta-rules + pointers, no project conventions.

---

**Key flows summary (in plain English):**

- **BMAD is outside Kiat.** Kiat starts at Team Lead and ends at the rollup event. BMAD is your métier agent — bring your own.
- **Team Lead is the only orchestrator.** Coders and reviewers are never launched directly by humans or by each other. Everything routes through Team Lead.
- **Pre-coding gates fire before any code.** `kiat-validate-spec` (Phase 0a) and pre-flight budget (Phase 0b) catch ambiguity and oversize stories **before** a coder is launched — the earliest possible failure point.
- **Parallel coding.** Backend and Frontend coders run simultaneously once Phase 0 passes. They never wait on each other.
- **3-way verdicts + 45-min fix budget.** Reviewers output `APPROVED / NEEDS_DISCUSSION / BLOCKED`. BLOCKED re-cycles within a time budget. NEEDS_DISCUSSION is arbitrated by Team Lead, never bounced back to the coder as "fix this".
- **One rollup event per story.** Team Lead emits exactly one write to `events.jsonl` at story completion — success or escalation. `report.py` reads this weekly for health metrics.

---

## 📚 Doc Structure: Who Reads What?

Kiat enforces a **strict framework / project separation** — and the doc structure reflects it:

### Framework docs (`.claude/`) — read by agents

| Doc | Audience | Purpose |
|-----|----------|---------|
| `CLAUDE.md` | All agents | Universal coding rules (no secrets, naming, error handling, testing, git) |
| `.claude/agents/kiat-*.md` | Themselves | Agent system prompts (team-lead, coders, reviewers) |
| `.claude/skills/kiat-*.md` | Agents invoking them | Structured skill checklists (review-backend, clerk-auth-review, validate-spec, etc.) |
| `.claude/specs/context-budgets.md` | Team Lead | Per-agent token budgets (Layer 5 enforcement) |
| `.claude/specs/metrics-events.md` | Team Lead, `report.py` | JSONL event log schema |
| `.claude/specs/failure-patterns.md` | Team Lead | Reactive failure pattern registry |
| `.claude/tools/report.py` | Humans (weekly) | Weekly health report generator |

### Project docs (`delivery/specs/`) — read by humans AND agents

| Doc | Audience | Purpose |
|-----|----------|---------|
| `delivery/specs/architecture-clean.md` | Backend devs + agents | Clean Architecture pattern (4 layers) |
| `delivery/specs/backend-conventions.md` | Backend devs + agents | Project structure, naming, error codes, logging |
| `delivery/specs/service-communication.md` | Backend devs + agents | DI patterns, service composition |
| `delivery/specs/frontend-architecture.md` | Frontend devs + agents | React patterns, hooks, RSC boundary |
| `delivery/specs/design-system.md` | Frontend devs + agents | Colors, spacing, typography, Tailwind v4 |
| `delivery/specs/api-conventions.md` | Backend devs + agents | REST design, error codes, status codes |
| `delivery/specs/database-conventions.md` | Backend devs + agents | Migrations, RLS, timestamps, naming |
| `delivery/specs/security-checklist.md` | Reviewers + agents | OWASP, RLS testing, input validation |
| `delivery/specs/clerk-patterns.md` | Frontend + backend agents | Auth flows, test mode, token handling |
| `delivery/specs/testing.md` | All agents + CI | Anti-flakiness rules, Playwright + Venom patterns, CI gate |
| `delivery/specs/git-conventions.md` | Coders + reviewers | Branch names, commit messages, PR discipline, immutability rules |
| `delivery/specs/deployment.md` | Team Lead + agents | Env vars, dev modes (`make dev` / `make dev-test`), production safety guards |
| **`delivery/specs/project-memory.md`** | **Tech spec writer + humans** | **Living file of emergent cross-story patterns. Only cross-story coherence mechanism in Kiat.** |
| `delivery/epic-X/story-NN.md` | All agents | **THE SPEC** — acceptance criteria, contracts, edge cases (written by BMAD) |
| `checklists/*.md` | Humans + agents | "Am I done?" templates (user-editable per project) |
| `patterns/*.md` | Humans | Architectural patterns (user-editable per project) |

**The separation test:** `find kiat/.claude/` lists framework files only; `find kiat/delivery/` lists project files only. Neither contains the other.

---

## 🛡️ Enforcement Model: How We Make Agents Actually Follow Rules

> The honest truth: **skills and docs don't force agent compliance — they're just more text in the context window.** Kiat's enforcement model is designed around this reality. We don't pretend agents are deterministic. We make their shortcuts **auditable** instead.

### The 6 Enforcement Layers

Kiat layers six mechanisms, from cheapest to hardest, so that even if one fails, the others catch the drift.

#### Layer 1 — Machine-parseable verdicts (3-way outcome)

Reviewers (`kiat-backend-reviewer`, `kiat-frontend-reviewer`) run a review skill (`kiat-review-backend.md`, `kiat-review-frontend.md`) that **mandates** one of three verdicts on the first line of output:

```
VERDICT: APPROVED           ← merge-ready
VERDICT: NEEDS_DISCUSSION   ← judgment call, Team Lead arbitrates
VERDICT: BLOCKED            ← concrete fixes required, coder re-cycles
```

**Why 3-way and not binary?**
Binary (APPROVED / BLOCKED) forces reviewers to shoehorn nuance into "fix this" when the real answer is "a human needs to decide." That creates false blockers and sends coders chasing ambiguous feedback. `NEEDS_DISCUSSION` is the escape hatch for *"code is correct but I have a question for a human."*

**Team Lead handles each verdict deterministically** — no guessing:
- `APPROVED` → proceed to story validation
- `NEEDS_DISCUSSION` → Team Lead arbitrates (pattern, spec ambiguity, UX tradeoff) or escalates to BMAD/user. **Never bounced back to the coder as "fix this"** — that was the old bug.
- `BLOCKED` → aggregate all issues, send to coder once, restart the fix-budget clock

Full decision tree in [`.claude/agents/kiat-team-lead.md`](.claude/agents/kiat-team-lead.md) (Phase 4).

---

#### Layer 2 — Wall-clock retry budget (not cycle count)

The original design said "max 2 review cycles, then escalate." In practice, cycle 3 is usually a trivial typo-fix follow-up, not a failure signal. Hard cycle caps waste escalations on cheap iterations and let one 2-hour slog slip through untouched.

**Kiat uses a 45-minute wall-clock fix budget per story instead:**

| Situation | Old rule (cycle-based) | New rule (time-based) |
|---|---|---|
| 3 cycles, each 5 min (typo fixes) | ❌ Escalated (wasted escalation) | ✅ Allowed (elapsed < 45 min) |
| 1 cycle, 2 hours on one bug | ✅ Allowed (only cycle 1) | ❌ Escalated (elapsed > 45 min) |

The clock replaces Team Lead's subjective judgment of *"is this an obvious fix or a design issue?"* with a deterministic gate. Immediate escalation still exists for security issues, spec ambiguity, and `NEEDS_DISCUSSION` verdicts — the time budget only governs normal fix loops.

Full budget rules in [`.claude/agents/kiat-team-lead.md`](.claude/agents/kiat-team-lead.md) (Retry Budget section).

---

#### Layer 3 — Hard trigger rules for specialist skills

Some concerns are too **cross-layer** to catch with a general reviewer checklist. Clerk auth is the canonical example: a single auth bug can live in 5 files at once (frontend hook + middleware + backend JWT + Playwright fixture + env var), and the general `kiat-review-frontend` skill has 45 other things to check — Clerk gets skimmed.

**Solution: a dedicated [`kiat-clerk-auth-review`](.claude/skills/kiat-clerk-auth-review.md) skill with a hard trigger rule baked into both reviewer agents.**

The trigger is written as an imperative with an **explicit greppable pattern list**:
> **You MUST run this skill if the diff touches ANY of: `@clerk/nextjs`, `useAppAuth`, `<ClerkProvider>`, `middleware.ts`, `clerkSetup`, `signInAsUserB`, `NEXT_PUBLIC_CLERK_*`, `Authorization: Bearer`, `ClerkAuthMiddleware`, `ENABLE_TEST_AUTH`, ...**

Not "consider running." Not "if relevant." **MUST + explicit patterns** — because patterns are greppable, while "relevance" is subjective.

**Why isolate Clerk instead of adding it to the general checklist?** Clerk is the highest-density footgun surface in the stack (7+ documented gotchas have hit real production: cross-origin signOut, storageState expiry, User B session pollution, build-time publishableKey baking, ...). Bundling it into `kiat-review-frontend` dilutes attention across 45 unrelated items. Isolating it means **when it runs, it runs with full focus — or not at all**, never half-done.

The same pattern can be reused for any other cross-layer concern (e.g., a future `payments-review` skill for Stripe, a `migration-review` skill for destructive DDL).

---

#### Layer 4 — Mandatory audit lines (the real enforcement)

**This is the crux of Kiat's enforcement model.** Everything above still relies on agents choosing to follow instructions. The audit layer converts choice into **auditable evidence**.

Every reviewer output **must** contain a line like:
```
Clerk-auth skill: N/A (no triggers matched)
```
or
```
Clerk-auth skill: PASSED (ran kiat-clerk-auth-review)
```
or
```
Clerk-auth skill: BLOCKED (ran kiat-clerk-auth-review) — see details above
```

**Missing line = malformed review = rejected by Team Lead. No exceptions.**

This flips the failure mode:
- **Before:** "Did the reviewer run the skill?" → unanswerable, trust-based
- **After:** "Does the review contain the audit line?" → one grep, deterministic

Even if a reviewer *lies* and writes `N/A` when triggers actually matched in the diff, the lie becomes **retroactively detectable** by grepping reviewer outputs against the diff. Skipping the skill is no longer invisible — it's a protocol violation with a paper trail.

Combined with the **verdict-merging rule** (if `CLERK_VERDICT: BLOCKED`, the parent reviewer's top-line verdict must become `VERDICT: BLOCKED`), this makes it structurally impossible for a passing top-line verdict to hide a failing sub-skill result — *if the reviewer follows the protocol*, and *detectable after the fact* if they don't.

---

#### Layer 5 — Context Budgets (pre-flight gate)

The four layers above catch bad reviews and bad retries. **Layer 5 catches the problem one level earlier: bad *inputs*.**

**The failure mode it addresses:** a story spec that looks fine in isolation, but when combined with the coder's ambient docs (CLAUDE.md + architecture doc + testing rules + design system + code references), the total injected context pushes past the sweet spot where Claude reasons well. The coder starts with 80k tokens of input, has fewer tokens *and fewer clear thoughts* left to do the actual work, and ships degraded code **silently** — no error, no blocker, just subtle correctness issues that tests may or may not catch.

**The fix:** hard per-agent token budgets, checked pre-flight by Team Lead before any coder is launched.

| Agent | Input budget |
|---|---|
| Team Lead | 10k tokens |
| Backend-Coder / Frontend-Coder | **25k tokens** |
| Backend-Reviewer / Frontend-Reviewer | 20k tokens |
| BMAD Master | unrestricted |

**How it's enforced:**
1. **Pre-flight check (Team Lead — Phase 0)**: before launching any coder, Team Lead runs `wc -c` on every file it plans to inject, divides by 4 (no tokenizer needed, ±20% is fine for gating), and compares to the target agent's budget. If over, **escalate to BMAD with a split request** — do NOT launch the coder "to see if it works."
2. **Self-check (coder — Step 0)**: defensively, each coder re-verifies on startup. If the budget is exceeded (Team Lead miscounted or a file grew between pre-flight and launch), the coder **stops before writing any code** and reports the overflow.
3. **Audit line**: Team Lead logs the result of the pre-flight check so it's visible:
   ```
   Pre-flight budget check: Backend-Coder 21k / 25k ✓  Frontend-Coder 19k / 25k ✓
   ```
   or on overflow:
   ```
   Pre-flight budget check: Backend-Coder 34k / 25k ❌ — ESCALATED to BMAD (story-NN too large)
   ```

**Why `bytes / 4` and not a real tokenizer?** Agents don't have a tokenizer tool at hand, and a cheap `wc -c | / 4` estimate is accurate to ±20% — which is more than enough to gate a 25k budget. The estimate slightly over-counts (safe direction).

**What happens when the budget blocks a story:** Team Lead escalates to BMAD with a concrete split request (*"suggested sub-stories: 27a, 27b, 27c, each ≤ 5k tokens of spec"*). The story doesn't ship broken — it gets resized before it's attempted. This is the earliest possible failure point in the pipeline, which makes it the cheapest to fix.

Full rules in [`.claude/specs/context-budgets.md`](.claude/specs/context-budgets.md): budget rationale, counting heuristic, per-agent anatomy, overflow protocol, gotchas.

---

#### Layer 6 — Pre-coding Validation Gates

Layers 1-5 catch problems at review time or via audit trails. **Layer 6 prevents two common failure modes from reaching coders at all** — both solved at Phase 0, before any code is written.

**6a — Spec ambiguity ([`kiat-validate-spec`](.claude/skills/kiat-validate-spec.md))**

The single highest-ROI check in Kiat. BMAD writes specs in prose; prose is ambiguous. A vague verb like "validate email" or "handle errors" hides behind well-written sentences, then explodes into a multi-cycle review ping-pong when the coder interprets it one way and the reviewer expects another.

Team Lead runs the `kiat-validate-spec` skill at **Phase 0a**, *before* the context budget check, *before* any coder is launched. The skill:
- Greps the spec for a curated list of vague verbs (*handle, validate, process, manage, support, optimize, ensure, proper, robust, efficient, reasonable*)
- Checks API/DB/UI contract completeness against the story scope
- Verifies cross-layer consistency (backend field names match frontend types)
- Enumerates missing edge cases (concurrency, empty states, network failure)
- Outputs `SPEC_VERDICT: CLEAR | NEEDS_CLARIFICATION | BLOCKED`

**Why this catches the most bugs:** BMAD is still in the conversation. A 5-minute clarification round is infinitely cheaper than a 45-minute fix-budget retry cycle on a story where the coder guessed wrong.

**6b — Test-patterns inheritance ([`kiat-test-patterns-check`](.claude/skills/kiat-test-patterns-check/SKILL.md))**

The general review skills (`kiat-review-frontend`, `kiat-review-backend`) have 45+ checklist items each. Test flakiness pitfalls get skimmed under that load. Meanwhile, `testing.md` has 26+ documented anti-flakiness rules from real incidents — but nothing forces the coder to read them, so they don't.

Coders run `kiat-test-patterns-check` at **Step 0.5** (right after context budget self-check, before writing any code). The skill:
- Runs a **scope-detection questionnaire** (does this story have forms? auto-save? Clerk auth? RLS? Playwright E2E? wizards?)
- For every "yes", **forces a verbatim acknowledgment** of the applicable rules — paraphrasing not allowed, the rule text is load-bearing
- Emits `TEST_PATTERNS: ACKNOWLEDGED` + the full block for every applicable pattern
- Reviewers then **verify the acknowledgment exists** in the handoff AND cross-check that actual code matches what was acknowledged (drift → `VERDICT: BLOCKED`)

This converts *"did you read testing.md?"* from a trust question into a textual evidence question. The acknowledgment is either in the output or it isn't.

Full rules in [`.claude/skills/kiat-validate-spec.md`](.claude/skills/kiat-validate-spec.md) and [`.claude/skills/kiat-test-patterns-check/SKILL.md`](.claude/skills/kiat-test-patterns-check/SKILL.md).

---

### Complementary Mechanism — Project Memory (cross-story coherence)

The 6 enforcement layers above all operate at **story scope**: they fire on one story at a time, catch problems within that story, and have no view of the project as a whole. That's intentional — agents are deliberately isolated to keep context budgets tight.

**But isolation has a cost: coherence drift.** Story 5 can invent a new pattern without knowing story 3 already solved the same problem differently. Over 15-20 stories, the project becomes a salad of inconsistent naming, duplicated components, and contradictory architectural choices. Each story is locally correct; the project is globally incoherent.

**[`delivery/specs/project-memory.md`](delivery/specs/project-memory.md) is Kiat's answer to this.** It's a living document that captures **emergent patterns** across stories:

- Naming conventions that emerged from real implementations
- Shared UI components that should be reused, not recreated
- API patterns by domain (how endpoints are structured per resource family)
- Architectural decisions that span multiple stories
- Known gotchas specific to this project

**It's the only cross-story coherence mechanism in Kiat.** Unlike the 6 enforcement layers (which are mechanical and scoped to one story), `project-memory.md` is a **shared memory** that the tech-spec-writer reads *before* writing a new story's technical spec, to ensure the new story aligns with what's already established.

**Maintenance:** manual, by humans, for now. An agent-driven maintenance mode may be added later once we know what patterns actually accumulate in practice.

**Complementary mechanism at epic scope:** the `_epic.md` template includes an "Epic Patterns" section that captures patterns specific to one epic (shorter-lived, bounded scope). Cross-epic patterns get promoted to `project-memory.md`.

---

### The philosophy in one sentence

> **Kiat doesn't try to force agent compliance — LLMs can always skim. Kiat makes non-compliance auditable, so drift is caught and corrected instead of silently shipped.**

This is why Kiat invests in:
1. **Deterministic output formats** (first-line verdicts) → parseable by Team Lead without LLM inference
2. **Time budgets instead of cycle counts** → clock decides, not judgment
3. **Specialist skills with pattern triggers** → reviewers can't claim "Clerk wasn't relevant"
4. **Mandatory audit lines** → every skill invocation leaves a trace
5. **Pre-flight context budgets** → oversized stories are split before they become silent failures
6. **Pre-coding validation gates** → ambiguous specs and unread testing rules are caught before any code is written

If compliance drifts in practice, the next enforcement lever is mechanical: have Team Lead automatically reject any review output missing the audit line and force a re-run. That's the final gate if trust erodes.

---

## 📊 Monitoring & Reporting

> **Philosophy:** You can't improve what you don't measure. Every enforcement layer above already emits structured audit lines — Kiat just needs a cheap way to collect and render them. No dashboards. No infra. Just a JSONL log, a Python script, and a markdown report you read once a week.

### What Gets Tracked

Five metrics that actually change your behavior when they drift:

| Metric | What it tells you |
|---|---|
| **Spec validation outcomes** | Is BMAD writing clear specs, or is clarification-rate climbing? |
| **Pre-flight overflow rate** | % of stories hitting the 25k context budget — drift ↑ = specs getting bloated |
| **Verdict distribution** | APPROVED / NEEDS_DISCUSSION / BLOCKED ratio per reviewer over time |
| **Fix-budget utilization** | Avg elapsed minutes + % of stories exhausting the 45-min budget |
| **Skill trigger consistency** | Was `kiat-clerk-auth-review` actually run on auth-touching diffs? Did coders' code match their `kiat-test-patterns-check` acknowledgments? |
| **Escalation reasons** | Histogram of *why* stories escalate — surfaces systemic bottlenecks |

### How It Works (Tier 1 — the only tier we've built)

**1. Single writer: Team Lead.** At every phase transition, Team Lead appends one JSON line to `delivery/metrics/events.jsonl`:

```jsonl
{"ts":"2026-04-10T14:02:11Z","story":"story-27","epic":"epic-3","event":"received","bmad_spec_bytes":18420}
{"ts":"2026-04-10T14:02:30Z","story":"story-27","event":"spec_validated","verdict":"CLEAR","clarifications_requested":0}
{"ts":"2026-04-10T14:03:00Z","story":"story-27","event":"preflight","agent":"kiat-backend-coder","estimated_tokens":21000,"budget":25000,"result":"pass"}
{"ts":"2026-04-10T14:18:42Z","story":"story-27","event":"review","agent":"kiat-backend-reviewer","cycle":1,"verdict":"APPROVED","clerk_skill_triggered":true,"clerk_verdict":"PASSED","test_patterns_consistent":true,"issues_count":0}
{"ts":"2026-04-10T14:19:00Z","story":"story-27","event":"passed","total_cycles":1,"total_elapsed_min":17,"backend_verdict":"APPROVED","frontend_verdict":"APPROVED"}
```

Full schema: [`.claude/specs/metrics-events.md`](.claude/specs/metrics-events.md).

**2. Reactive failure pattern registry.** When a story escalates, Team Lead checks [`.claude/specs/failure-patterns.md`](.claude/specs/failure-patterns.md) for a matching pattern. If found, increment recurrence. If new, create an `FP-NNN` file. When a pattern hits **3 recurrences without a structural fix**, that's the signal to change Kiat itself — not just document the failure.

**3. Markdown reports on demand.** Run the generator whenever you want a health pulse:

```bash
# All events, all time
python3 kiat/.claude/tools/report.py

# Filter by date
python3 kiat/.claude/tools/report.py --since 2026-04-01

# Filter by epic
python3 kiat/.claude/tools/report.py --epic epic-3

# Write to file
python3 kiat/.claude/tools/report.py --output health-report.md
```

Output includes: Summary, Spec validation, Pre-flight budget, Verdict distribution, Cycles per story histogram, Fix budget utilization, Clerk skill runs, Test-patterns drift, Escalations with reasons, and a per-story table. Zero dependencies beyond Python 3.9+ stdlib.

### Why Not a Dashboard?

Honest answer: **you don't have enough data yet.** A pretty chart with 3 data points is noise, and building observability infra for data that doesn't exist is procrastination dressed as work. Start with Tier 1. After 10-15 real stories, you'll know what's worth visualizing — and the JSONL schema is designed to be stable, so upgrading to Tier 2 (HTML dashboard) or Tier 3 (weekly auto-digest with GitHub Actions + Slack webhook) doesn't require re-instrumenting Team Lead.

### What to Look For in a Weekly Report

When you read the report each week, these are the signals to act on:

- **CLEAR rate < 70%** → BMAD specs are too ambiguous; tighten spec-writing guidance
- **Overflow rate > 20%** → stories are too big OR context budgets are too tight
- **Avg cycles > 2.5** → reviewers finding too many issues OR coders submitting prematurely
- **`test_patterns_consistent: false` recurring** → coders are acknowledging rules but not applying them; `kiat-test-patterns-check` needs teeth
- **Same failure pattern at recurrence ≥ 3** → stop documenting, start structurally fixing (new skill, new layer, new rule)
- **Clerk skill trigger rate suddenly drops** → reviewers are skipping the audit; grep historic reviews to find the drift

### When to Upgrade from Tier 1

Defer Tier 2 (HTML dashboard) and Tier 3 (cron auto-digest) until:
- You've run **≥ 15 stories** through Kiat (enough data for trend lines to mean something)
- The markdown report's recommendations have proven insufficient (can't know yet)
- The team has grown past the point where one person remembers to read the report

Until then, `python3 kiat/.claude/tools/report.py` once a week is more than enough.

---

## 🚦 Workflow: From Chat to Merge

### Phase 1: Spec Writing (BMAD Master)
```
User/Client: "I want to add 2FA to login"
    ↓
BMAD Master Agent:
  1. Challenge: "Is this feature for existing users or new signups? Security or UX?"
  2. Propose spec: "Feature: 2FA setup flow → acceptance criteria → API contracts → edge cases"
  3. If spec is big (XL tshirt): Launch adversarial review
  4. Output: `delivery/epic-X/story-NN-2fa-setup.md` (DONE, ready to code)
    ↓
Human verification: "Looks good?" ✅
```

**BMAD context**:
- ALL docs accessible (no restrictions)
- Can call skills: `bmad-editorial-review-prose`, `bmad-editorial-review-structure`
- Outputs to `delivery/` directory

---

### Phase 2: Code (Parallel)
```
Backend-Coder Agent:
  Context: CLAUDE.md + backend-architecture.md + testing-patterns.md + story-NN.md
  Load skills: @clerk, @api-design (dynamic)
  1. Read spec → extract: "Add POST /users/:id/2fa-enable"
  2. Write migration + handler + tests
  3. Output: PR-ready code + Playwright test
    ↓
Backend-Reviewer Agent:
  Context: story-NN.md (spec) + CLAUDE.md + checklist
  1. Check: "Does code match spec? Any security gaps?"
  2. If M+ tshirt issue: Send detailed feedback
  3. Output: List of issues (if any)
    ↓
[If issues] → Backend-Coder re-runs (reads reviewer output + fixes ALL in one session)
[If clean] → Test gate
```

**Frontend same flow (parallel)**

---

### Phase 3: Test Gate
```
Playwright tests (run in agent + CI):
  1. If FAIL: Test-Debugger agent (or Coder) reads error + fixes code + reruns
  2. Gated by the 45-min fix budget (see Enforcement Model) — not a hard cycle count
  3. If PASS: Unblock merge
```

---

### Phase 4: Merge (Human)
```
Human verifies:
  ✅ Specs written + approved
  ✅ Code reviewed (no major issues)
  ✅ Tests passing (Playwright + CI)
  → Merge
```

---

## 🤖 Agent Configuration: Quick Reference

| Agent | Triggered By | Context Size | Skills | Iteration Budget |
|-------|--------------|--------------|--------|----------------|
| **BMAD Master** | User chat | Unrestricted | bmad-editorial-*, brand-specific | N/A (orchestrator) |
| **Team Lead** | BMAD output | 8-10k tokens (spec + story context) | None (pure orchestration) | N/A (time-gated) |
| **Backend-Coder** | Team Lead | 12-15k tokens (story + arch) | clerk, next-best-practices, sharp-edges | 45-min fix budget |
| **Frontend-Coder** | Team Lead | 12-15k tokens (story + arch + design) | clerk, react-best-practices, composition-patterns | 45-min fix budget |
| **Backend-Reviewer** | After Backend-Coder | 10-12k tokens (story + checklist + code diff) | **kiat-review-backend** (REQUIRED), **kiat-clerk-auth-review** (conditional), differential-review | Verdict: APPROVED / NEEDS_DISCUSSION / BLOCKED |
| **Frontend-Reviewer** | After Frontend-Coder | 10-12k tokens (story + checklist + code diff) | **kiat-review-frontend** (REQUIRED), **kiat-clerk-auth-review** (conditional), react-best-practices, composition-patterns, web-design-guidelines | Verdict: APPROVED / NEEDS_DISCUSSION / BLOCKED |
| **Test-Debugger** (optional) | If tests fail | 8-10k tokens (test error + code) | None (pure debugging) | 45-min fix budget |

**Key principle**: **Smaller context = faster thinking = better decisions**. Agents don't see the entire codebase.

---

## 🔄 Preventing Infinite Loops

**Problem**: Reviewer says "issue X" → Coder fixes → Reviewer says "now issue Y" → repeat forever.

**Solution** (see full [Enforcement Model](#-enforcement-model-how-we-make-agents-actually-follow-rules) above):
1. **3-way verdicts**: `APPROVED / NEEDS_DISCUSSION / BLOCKED` — judgment calls escalate instead of looping
2. **Batch feedback**: Reviewer lists ALL issues at once; coder fixes them in one pass (no ping-pong)
3. **45-min fix budget**: Re-cycles allowed while elapsed time < 45 min; exhausted budget → escalate to user
4. **Convergence gate**: If reviewer finds 5+ issues in the same area → story is too ambitious → split into smaller story
5. **Audit lines**: Every review output carries skill-invocation evidence, so silent shortcuts are detectable

---

## 🎯 Context Injection: How Agents See Specs

**Goal**: Reviewer needs to know "what was the acceptance criteria?" without reading entire Kotai codebase.

**Solution**: File-centric injection
```
Reviewer prompt receives:
  @file-context: delivery/epic-X/story-NN.md (spec)
  @file-context: checklists/reviewer-checklist.md (role guide)
  @inline: code diff from PR (git show)
  @memory: MEMORY.md (if any prior context needed)
```

**Not included**:
- Backend codebase (coder reads it, reviewer doesn't need it)
- Full git history
- Other epics (only THIS story)

**Documented in**: `patterns/context-injection.md`

---

## ✅ Checklists: "Am I Done?"

Each agent has a checklist:
- **Backend-Coder**: migration, handler, middleware, logging, error handling, PASSED tests
- **Frontend-Coder**: component, hook, tests, accessibility, mobile responsive
- **Reviewer**: spec compliance, security, performance, maintainability
- **Tester**: E2E coverage, edge cases, offline behavior, a11y

**No ambiguity: Checklist is the contract.**

---

## 🛠️ Stack Details

- **Backend**: Go 1.23 + Gin + Bun ORM + PostgreSQL 16
- **Frontend**: Next.js 16 + App Router + React 19 + Shadcn/UI + Tailwind v4
- **Auth**: Clerk (real auth in dev, test auth available)
- **Database**: PostgreSQL (migrations tracked in `backend/migrations/`)
- **Testing**: Playwright E2E + Venom backend tests
- **Deployment**: Docker + Cloud Run (GCP)

---

## 📁 Folder Layout

The layout enforces a strict separation: **`.claude/` = IA/Kiat framework**, **`delivery/` = project-owned**. No mixing.

```
kiat/
├── README.md                          # This file — Kiat vision + enforcement model
├── INDEX.md                           # Navigation hub
├── GETTING_STARTED.md                 # New-user onboarding
├── structure.md                       # Architecture decision log
│
├── .claude/                           # ═══ IA / Kiat framework ONLY ═══
│   ├── agents/                        # Agent system prompts (all kiat- prefixed)
│   │   ├── kiat-team-lead.md          # Technical orchestrator
│   │   ├── kiat-backend-coder.md      # Go + Gin + Bun
│   │   ├── kiat-frontend-coder.md     # Next.js + React + Shadcn
│   │   ├── kiat-backend-reviewer.md   # Backend quality gate
│   │   └── kiat-frontend-reviewer.md  # Frontend quality gate
│   ├── skills/                        # Reusable agent skills (all kiat- prefixed)
│   │   ├── kiat-review-backend.md     # Structured backend review checklist
│   │   ├── kiat-review-frontend.md    # Structured frontend review checklist
│   │   ├── kiat-clerk-auth-review.md  # Clerk auth specialist (Layer 3)
│   │   ├── kiat-validate-spec.md      # Pre-coding spec validation (Layer 6a)
│   │   └── kiat-test-patterns-check/  # Forced-response test patterns (Layer 6b)
│   │       ├── SKILL.md               #   Router + scope detection
│   │       └── blocks/                #   9 pattern blocks loaded selectively
│   ├── specs/                         # Framework specs — machinery, not conventions
│   │   ├── context-budgets.md         # Per-agent token budgets (Layer 5)
│   │   ├── metrics-events.md          # JSONL event log schema
│   │   └── failure-patterns.md        # Reactive failure pattern registry
│   ├── tools/                         # Framework utilities
│   │   └── report.py                  # Weekly health report generator
│   └── docs/                          # Docs consumed by agents
│       ├── CLAUDE.md                  # Universal coding rules (all agents read this)
│       └── README.md                  # Framework doc index
│
├── delivery/                          # ═══ Project-owned ONLY ═══
│   ├── README.md                      # Delivery conventions (epics, stories)
│   ├── epic-X/                        # Per-epic folders with story specs
│   │   └── story-NN.md                # Written by BMAD, consumed by coders
│   ├── metrics/                       # Data written by Team Lead at runtime
│   │   └── events.jsonl               # (generated when stories run)
│   └── specs/                         # Project conventions — humans read these
│       ├── api-conventions.md         # REST design, error codes
│       ├── architecture-clean.md      # Clean Architecture 4 layers
│       ├── backend-conventions.md     # Project structure, naming, logging
│       ├── clerk-patterns.md          # Clerk auth flows
│       ├── database-conventions.md    # Migrations, RLS, timestamps
│       ├── deployment.md              # Env vars, dev modes, production guards
│       ├── design-system.md           # Colors, spacing, typography
│       ├── frontend-architecture.md   # React patterns, hooks, accessibility
│       ├── git-conventions.md         # Branches, commits, PR discipline
│       ├── project-memory.md          # Emergent cross-story patterns (coherence mechanism)
│       ├── security-checklist.md      # OWASP, RLS testing
│       ├── service-communication.md   # DI patterns, error handling
│       └── testing.md                 # Anti-flakiness rules + CI gate
│
├── checklists/                        # Project checklist templates (user-editable)
└── patterns/                          # Project architectural patterns (user-editable)
```

**The separation test:** `find kiat/.claude/` lists the exact framework files (Kiat IP). `find kiat/delivery/` lists the exact project-owned files (your project's code and conventions). Neither list contaminates the other.

---

## 🚀 Getting Started with Kiat

1. **Read this README** (you're here ✅)
2. **Read `structure.md`** (why each architectural decision)
3. **Read `CLAUDE.md`** (coding rules)
4. **Pick an epic to build** → copy `delivery/epic-template/` → edit
5. **Chat with BMAD Master** (agent in `.claude/agents/`) → get spec
6. **Trigger Backend-Coder + Frontend-Coder** (in parallel)
7. **Check reviewer output** → if issues, coder reruns
8. **Verify tests pass** → merge

---

## 📖 Further Reading

- **`structure.md`**: Architecture decision log (why did we choose this?)
- **`CLAUDE.md`**: Day-to-day coding rules
- **`patterns/context-injection.md`**: How context flows through agents
- **`patterns/infinite-loop-prevention.md`**: How we avoid reviewer ping-pong
- **`.claude/agents/*.md`**: Per-agent system prompts + instructions

---

## 🎓 Key Principles

1. **Spec-first**: Agents code from written specs, not vague requirements
2. **Single source of truth**: Each artifact (spec, arch, pattern) lives in ONE place
3. **Smart context**: Agents load only what they need (no full codebase in every prompt)
4. **Convergence**: Reviewer feedback → coder fixes ALL at once (no ping-pong)
5. **Gated by tests**: Code only merges if Playwright + CI ✅
6. **Human approval**: You decide when specs are good, when code is good, when to merge
7. **Parallelizable**: BMAD writes specs while you review prior epic; Backend + Frontend code simultaneously

---

**Let's ship. 🚀**
