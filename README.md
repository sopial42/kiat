# 🚀 Kiat — Starter Kit Agent-First SaaS

> **The vision**: You describe your product idea in natural language. **BMad** captures the evergreen business knowledge and writes the `## Business Context` of each story (the *what* and the *why*). **`kiat-tech-spec-writer`** enriches the same story with the technical layer (the *how*). **`kiat-team-lead`** runs the pipeline: parallel coder and reviewer agents ship the code, SubagentStop hooks enforce the protocol. Done.

This is a **generic, reusable starter kit** for building SaaS with:
- **Go + Gin + Bun ORM** backend (Clean Architecture)
- **Next.js App Router + Shadcn/UI + React Query** frontend
- **Clerk** authentication
- **Two-layer agent workflow**: **BMad** (upstream product agent) writes the business layer — evergreen domain knowledge in [`delivery/business/`](delivery/business/README.md) and the `## Business Context` section of every story in [`delivery/epics/`](delivery/epics/README.md). **`kiat-tech-spec-writer`** then enriches the same story with the technical layer (Skills, API contracts, database, frontend, edge cases, tests). **`kiat-team-lead`** orchestrates the execution pipeline. BMad is **not** a Kiat agent — it's an external product agent (any Claude session acting as BMad works), but Kiat ships explicit folder-level contracts that govern what BMad is allowed to write where, so the integration is first-class rather than ad-hoc.

---

## 🎯 The Vision: Why Kiat?

### Problems we're solving
1. **Business intent vs technical spec have different owners, but usually live in one file owned by nobody.** The *what* (user needs, personas, business rules, domain model) and the *how* (API contracts, DB schemas, acceptance criteria) evolve on different clocks: the business layer is shaped by the product/métier voice and rarely changes once stable, while the technical layer is written just before a story ships and is often rewritten as the stack evolves. Smearing them into one document turns every edit into a merge conflict between two people who shouldn't be merging. Kiat splits them into **two layers living in the same story file**, each owned by a different author: **BMad** writes the `## Business Context` section at the top (user story, personas, user-facing acceptance criteria, links to `delivery/business/`), and **`kiat-tech-spec-writer`** appends all technical sections below. Each author has a hard contract saying what it's allowed to touch — see [`delivery/epics/README.md`](delivery/epics/README.md) and [`delivery/business/README.md`](delivery/business/README.md).
2. **Informal requests don't survive parallel execution.** "Add auto-save to the notes editor" is fine for a human. For two parallel coder agents building backend and frontend in isolation, it guarantees a contract mismatch. The tech-spec-writer is the single funnel that forces every new story through a structured spec before any code runs.
3. **Infinite review loops.** Reviewer finds issue → coder fixes → reviewer finds new issue → repeat forever. Kiat caps this with a 45-minute wall-clock fix budget + 3-way verdicts (`APPROVED / NEEDS_DISCUSSION / BLOCKED`) so judgment calls escalate instead of looping.
4. **Context explosion.** Agents loaded with the entire codebase waste tokens and think slower. Kiat enforces hard per-agent token budgets checked pre-flight, and skills load only what they need via progressive disclosure (`SKILL.md` + on-demand `references/`).
5. **Skills drift silently.** A skill that looks well-designed can behave identically to no skill at all — audit lines get emitted, acknowledgments get pasted, but the underlying output is unchanged. Kiat runs behavioral evals (`with_skill` vs baseline) to measure the real delta. See [Skill Evaluation](#-skill-evaluation-proving-the-skills-actually-work).

### Our solution
- **Two-layer story model, one file per story, two authors.** Business knowledge in [`delivery/business/`](delivery/business/README.md) (evergreen facts: glossary, personas, business-rules, domain-model, user-journeys) written by BMad. Story files in [`delivery/epics/`](delivery/epics/README.md) with a `## Business Context` section at the top written by BMad and everything-else-technical written by `kiat-tech-spec-writer` in enrichment mode. The tech-spec-writer **preserves the Business Context intact** and only appends below; BMad **never touches technical sections** or `delivery/specs/`. Each folder's README enforces its half of the contract.
- **BMad has 4 input modes** (Explore / Capture / Plan / Review). Capture lands in `delivery/business/`, Plan lands in the `## Business Context` of an epic or story, Explore is think-out-loud-no-writes, Review is audit-only. See the [BMad writing protocol](delivery/business/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad).
- **Single source of truth per artifact.** Conventions in `delivery/specs/`, framework machinery in `.claude/`, runtime data in `delivery/metrics/`, business knowledge in `delivery/business/`, stories in `delivery/epics/`. Never cross the streams.
- **Pre-coding validation gates.** `kiat-validate-spec` catches ambiguity and contract gaps before any coder is launched; the 25k context budget pre-flight catches oversized stories.
- **3-way review verdicts + time-budgeted retries** — see [Enforcement Model](#-enforcement-model-how-we-make-agents-actually-follow-rules).
- **SubagentStop hooks for hard enforcement.** Coders can't hand off without emitting `TEST_PATTERNS: ACKNOWLEDGED`; reviewers can't hand off without `VERDICT:` as line 1. Exit 2 on violation, re-run forced.
- **Observability from day one** — JSONL event log + markdown health reports. See [Monitoring & Reporting](#-monitoring--reporting).

---

## 🏗️ Architecture at a Glance

Two diagrams below: **Diagram A** shows the flow of a single story through the agents; **Diagram B** shows which skills each agent loads at which moment.

### Diagram A — Agentic Flow (per story)

```
┌──────────┐
│   USER   │
└────┬─────┘
     │ "I want feature X" / "users struggle with Y" (informal product thinking)
     ▼
┌──────────────────────────────────────────────────────────────────┐
│                          BMad                                     │  ◄─── Business layer author
│                    (external product agent)                       │      (upstream of Kiat)
│  Modes: Explore / Capture / Plan / Review                          │
│  • Capture → writes evergreen domain facts to delivery/business/   │
│    (glossary / personas / business-rules / domain-model /          │
│     user-journeys)                                                 │
│  • Plan    → creates / updates an epic or story, writing ONLY the  │
│    ## Business Context section (user story, personas,             │
│    user-facing acceptance criteria, business rationale, links      │
│    to delivery/business/)                                          │
│  • NEVER writes technical sections, never touches delivery/specs/  │
│    or .claude/ (enforced by folder-level contracts)                │
└────┬─────────────────────────────────────────────────────────────┘
     │ delivery/epics/epic-X/story-NN.md with ## Business Context
     │ (business layer complete; technical sections empty)
     ▼
┌──────────────────────────────────────────────────────────────────┐
│                     kiat-tech-spec-writer                         │  ◄─── Technical layer author
│                    (enrichment mode — default)                     │      (default entry point
│  • Reads ## Business Context (preserves it intact — never rewrites)│       for new technical work)
│  • Reads linked delivery/business/ files + relevant                │
│    delivery/specs/ conventions + delivery/specs/project-memory.md  │
│  • Asks clarifying questions if needed (≤ 2 rounds)                │
│  • Decides which contextual skills the coders will need            │
│    (consults .claude/specs/available-skills.md)                    │
│  • Appends technical sections: Skills, Backend / API contracts,    │
│    Frontend / Components, Database, Edge cases, Test scenarios,    │
│    Out of scope                                                    │
│  • Self-validates via kiat-validate-spec                           │
│                                                                    │
│  Greenfield mode (fallback — no prior BMad pass):                  │
│  • Writes BOTH layers itself, using the user's request verbatim    │
│    as the business intent                                          │
└────┬─────────────────────────────────────────────────────────────┘
     │ delivery/epics/epic-X/story-NN.md — both layers populated
     │ (SPEC_VERDICT: CLEAR)
     ▼
╔══════════════════════════════════════════════════════════════════╗
║                     kiat-team-lead                                ║  ◄─── Pipeline orchestrator
║  ┌────────────────────────────────────────────────────────────┐  ║
║  │ Phase 0a — re-run kiat-validate-spec (defense in depth)    │  ║
║  │ ├─ CLEAR ──────────────────────────────────┐               │  ║
║  │ ├─ NEEDS_CLARIFICATION ── ▶ back to writer ┘ (≤ 2 rounds)  │  ║
║  │ └─ BLOCKED ─────────────▶ ESCALATE to user                 │  ║
║  │                                                             │  ║
║  │ Phase 0b — pre-flight context budget (wc -c / 4)           │  ║
║  │ ├─ reads ## Skills section to estimate total cost          │  ║
║  │ ├─ pass ──────────────────────────────────┐                │  ║
║  │ └─ overflow ──────────▶ back to writer for split or trim   │  ║
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
║   │                       or escalates to writer /    │           ║
║   │                       BMad / user (never coder)   │           ║
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

**Reading the diagram:** solid lines = normal flow. Every escalation path exits the Kiat boundary (the double-walled box) — those are the moments where humans step in, or the flow bounces back to the tech-spec-writer / BMad. The rollup event at Phase 7 is the ONE write Team Lead does per story, and it's the exit marker.

**Three ways a story enters the pipeline:**

1. **BMad-first (recommended for product work).** User thinks out loud with BMad about a user need; BMad captures the stable facts into `delivery/business/` (Capture mode) and writes the `## Business Context` section of a story (Plan mode). The user then invokes `kiat-tech-spec-writer` on the story file — it detects the pre-existing Business Context, runs in **enrichment mode**, and appends the technical layers without touching the business layer. Team Lead executes.
2. **Tech-spec-writer-first (for pure technical work).** For refactors, bug fixes, or work with no new business intent, the user goes straight to `kiat-tech-spec-writer` with an informal request. The writer runs in **greenfield mode** and produces both layers itself (Business Context in the user's natural language, technical sections in English). Team Lead executes.
3. **Re-execute an existing story.** The story file already has both layers filled in (e.g., re-running a story that was previously escalated). The user invokes `kiat-team-lead` directly on the story path. The tech-spec-writer is skipped because the story is already complete.

**BMad is external to Kiat in the strict sense** — there is no `.claude/agents/bmad.md` shipped by Kiat. BMad is any Claude session you configure to act as the product voice. What Kiat provides instead are **folder-level contracts** that define exactly what BMad is allowed to write where: evergreen facts in [`delivery/business/`](delivery/business/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad), Business Context sections in [`delivery/epics/`](delivery/epics/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad). Every Kiat agent downstream (tech-spec-writer, team-lead, coders, reviewers) trusts these contracts — which is why the integration works without Kiat owning the BMad prompt.

### Diagram B — Skill Loading Map (who loads what when)

```
AGENTS                               SKILLS (loaded on invocation)
───────────                          ──────────────────────────────

                                     ┌─ (no Kiat skills)
                                     │    BMad is external to Kiat;
                                     │    its only "skill" is reading
                                     │    the two folder contracts
                                     │    and respecting their rules
BMad (upstream, external) ───────▶   │
                                     └─ READS AS AMBIENT:
                                        • delivery/business/README.md
                                          (BMad writing protocol:
                                           Explore / Capture / Plan
                                           / Review modes, decision
                                           tree, sizing discipline)
                                        • delivery/epics/README.md
                                          (two-layer story model,
                                           Plan-mode protocol,
                                           ## Business Context
                                           boundary, handoff rules)

                                     ┌─ kiat-validate-spec         ◄─ Self-check before handoff
kiat-tech-spec-writer ── invokes ──▶ │    (runs at Step 6 in both
                                     │     enrichment and greenfield
                                     │     modes; the skill checks
                                     │     both layers of the story)
                                     │
                                     └─ (consults
                                        .claude/specs/available-skills.md
                                        to decide which contextual
                                        skills to list in the story
                                        — does not load them itself)

                                     ┌─ kiat-validate-spec         ◄─ Phase 0a (defense in depth)
kiat-team-lead   ─── invokes ───▶    │
                                     └─ (no other skills — Team Lead
                                        is pure orchestration)

                                     ┌─ kiat-test-patterns-check   ◄─ Step 0.5 (always)
                                     │   ├─ SKILL.md (router)
                                     │   └─ blocks/block-*.md
                                     │       (selective: only the
                                     │        ones matching scope)
kiat-backend-coder   ─── invokes ──▶ │
                                     ├─ Skills listed in story
                                     │   ## Skills section
                                     │   (e.g., differential-review
                                     │    if auth/payments touched)
                                     │
                                     └─ (community skills per
                                        story: sharp-edges, etc.)

                                     ┌─ kiat-test-patterns-check   ◄─ Step 0.5 (always)
                                     │   ├─ SKILL.md (router)
                                     │   └─ blocks/block-*.md
                                     │
kiat-frontend-coder   ─── invokes ─▶ ├─ kiat-ui-ux-search          ◄─ CONTEXTUAL
                                     │   (if story ## Skills lists it
                                     │    — wraps external 85k-token
                                     │    skill via search-on-demand)
                                     │
                                     └─ (community skills per story:
                                        react-best-practices,
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


AMBIENT CONTEXT (loaded by EVERY Kiat agent, always)
────────────────────────────────────────────────────
  CLAUDE.md                           ◄─ Universal meta-rules for
                                         any Claude instance +
                                         framework/project separation
                                         rule + pointers
                                         (BMad sessions read this too
                                          if they run inside Claude Code)


FRAMEWORK SPECS (loaded by tech-spec-writer and Team Lead)
──────────────────────────────────────────────────────────
  .claude/specs/available-skills.md   ◄─ Consulted by tech-spec-writer
                                         when deciding which contextual
                                         skills a story needs
  .claude/specs/context-budgets.md    ◄─ Consulted by Team Lead at Phase 0b
  .claude/specs/metrics-events.md     ◄─ Consulted by Team Lead at Phase 7
  .claude/specs/failure-patterns.md   ◄─ Consulted by Team Lead at escalation


PROJECT BUSINESS LAYER (BMad-owned, read on demand by tech-spec-writer)
──────────────────────────────────────────────────────────────────────
  delivery/business/README.md         ◄─ BMad reads this as ambient;
                                         tech-spec-writer reads it to
                                         understand what's authoritative
                                         in the folder
  delivery/business/glossary.md       ◄─ Read by tech-spec-writer if the
  delivery/business/personas.md          story touches the corresponding
  delivery/business/business-rules.md    domain. NOT all loaded —
  delivery/business/domain-model.md      selective per story, based on
  delivery/business/user-journeys.md     links in the ## Business Context.

  delivery/epics/README.md            ◄─ BMad reads this for the
                                         Plan-mode protocol + ##
                                         Business Context boundary
  delivery/epics/epic-X/_epic.md      ◄─ Two-layer: ## Business Context
  delivery/epics/epic-X/story-NN.md      by BMad + technical sections
                                         by tech-spec-writer. Both
                                         layers read by Team Lead,
                                         coders, and reviewers.


PROJECT TECHNICAL CONVENTIONS (loaded on-demand per task)
─────────────────────────────────────────────────────────
  delivery/specs/*.md                 ◄─ Tech-spec-writer + coders + reviewers
                                         load the specific conventions they
                                         need for the current task.
                                         NOT all loaded — selective per story.
                                         BMad NEVER reads or writes here.
  delivery/specs/project-memory.md    ◄─ Cross-story technical coherence:
                                         emergent patterns across past
                                         stories. Read by tech-spec-writer.
```

**Key rules captured by Diagram B:**

- **`kiat-tech-spec-writer` is the Kiat-side entry point for new work.** It reads project conventions, decides which contextual skills the coders will need (from `available-skills.md`), and writes the technical layer of the story file. In enrichment mode (the common case once BMad is in the loop) it preserves the pre-existing `## Business Context` section intact and only appends technical sections below it. It does NOT load contextual skills itself — it just lists them in the story's `## Skills` section so the coders know what to load.
- **BMad sits upstream of the tech-spec-writer, outside the .claude/ namespace.** BMad is not a Kiat agent — it's any Claude session configured to act as the product voice. It writes exclusively inside `delivery/business/` (evergreen domain knowledge) and the `## Business Context` section of epics/stories. The two folders each own an explicit [BMad writing protocol](delivery/business/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad) that enforces the boundary.
- **`kiat-team-lead` has zero skills of its own** — it's pure orchestration. It only invokes `kiat-validate-spec` at Phase 0a (re-validation, defense in depth — the tech-spec-writer already validated). Every other skill is owned by downstream agents.
- **`kiat-test-patterns-check` loads selectively** — the router (`SKILL.md`) is always loaded by coders, but the 9 pattern blocks are loaded individually based on story scope (usually 3-5 blocks per story, not all 9).
- **`kiat-ui-ux-search` is a search-on-demand wrapper** — the underlying [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) is 85k tokens, so we never load it eagerly. The coder loads only the lightweight wrapper (~1k) and queries the underlying skill via `search.py` only when needed.
- **`kiat-clerk-auth-review` has a hard trigger rule** — reviewers MUST invoke it if the diff touches any auth-adjacent pattern (grep-based trigger list). This is the enforcement mechanism for cross-layer auth bugs.
- **Community skills are NOT Kiat-owned** — they're third-party expertise libraries (`react-best-practices`, `composition-patterns`, `differential-review`, etc.). Kiat agents can invoke them but doesn't guarantee their behavior.
- **CLAUDE.md is the only truly global ambient** — every Kiat agent has it in context, but it's minimal (~95 lines) and contains only meta-rules + pointers, no project conventions.

---

**Key flows summary (in plain English):**

- **Two-layer story model.** Every story file has a `## Business Context` section (written by BMad, in the project's business language) and technical sections below it (written by the tech-spec-writer, always in English). One file, two layers, two authors, explicit folder-level contracts stopping either author from writing in the other's territory.
- **BMad is the upstream product voice.** For new product work, start with BMad — Capture mode accumulates evergreen facts in `delivery/business/`, Plan mode creates/updates the `## Business Context` of a story. BMad lives outside `.claude/` because it's not a Kiat agent; the folder READMEs in `delivery/business/` and `delivery/epics/` are Kiat's integration contract.
- **Tech-spec-writer is the Kiat-side entry point.** It reads the Business Context (if present), loads the minimum project conventions, and appends Skills + API / DB / Frontend / Tests in the same file. For pure technical work (refactors, bug fixes) it also works in greenfield mode and writes both layers itself.
- **Team Lead is the orchestrator, not the entry point.** It receives stories that the tech-spec-writer has already filled in and runs the pipeline.
- **Pre-coding gates fire before any code.** `kiat-validate-spec` (Phase 0a) and pre-flight budget (Phase 0b, which reads the story's `## Skills` section to estimate cost) catch ambiguity and oversize stories **before** a coder is launched — the earliest possible failure point.
- **Parallel coding.** Backend and Frontend coders run simultaneously once Phase 0 passes. They never wait on each other.
- **3-way verdicts + 45-min fix budget.** Reviewers output `APPROVED / NEEDS_DISCUSSION / BLOCKED`. BLOCKED re-cycles within a time budget. NEEDS_DISCUSSION is arbitrated by Team Lead, never bounced back to the coder as "fix this".
- **Event log at phase transitions + rollup at the end.** Team Lead appends one JSON line per phase transition to `events.jsonl` (received, spec_validated, preflight, review, passed/escalated) and a final rollup at story completion. `report.py` reads these weekly for health metrics.

---

## 📚 Doc Structure: Who Reads What?

Kiat enforces a **strict framework / project separation** — and the doc structure reflects it:

### Framework docs (`.claude/`) — read by agents

| Doc | Audience | Purpose |
|-----|----------|---------|
| `CLAUDE.md` (project root) | All agents | Ambient context auto-loaded by Claude Code: meta-rules + framework/project separation + pointers |
| `.claude/agents/kiat-*.md` | Themselves | 6 agent system prompts (tech-spec-writer, team-lead, 2 coders, 2 reviewers) |
| `.claude/skills/kiat-*.md` | Agents invoking them | 6 structured skills (validate-spec, review-backend, review-frontend, clerk-auth-review, test-patterns-check, ui-ux-search) |
| `.claude/specs/available-skills.md` | tech-spec-writer | Registry of contextual skills with "when to use" criteria |
| `.claude/specs/context-budgets.md` | Team Lead | Per-agent token budgets (Layer 5 enforcement) |
| `.claude/specs/metrics-events.md` | Team Lead, `report.py` | JSONL event log schema (rollup-first v1.1) |
| `.claude/specs/failure-patterns.md` | Team Lead | Reactive failure pattern registry |
| `.claude/tools/report.py` | Humans (weekly) | Weekly health report generator |
| `.claude/tools/doc-audit.py` | Humans (anytime) | Audit `delivery/specs/` against M1 (tokens) + M2 (structure ratio) |

### Project technical conventions (`delivery/specs/`) — read by humans AND agents

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

### Project business layer (`delivery/business/` + `delivery/epics/`) — BMad-authored + tech-spec-writer-enriched

| Doc | Audience | Purpose |
|-----|----------|---------|
| [`delivery/business/README.md`](delivery/business/README.md) | BMad + humans | Folder contract: what goes here, BMad's 4 input modes, Capture-mode decision tree, sizing discipline, zones BMad never touches |
| `delivery/business/glossary.md` | BMad + tech-spec-writer | Evergreen domain terms (create on demand) |
| `delivery/business/personas.md` | BMad + tech-spec-writer | User personas (create on demand) |
| `delivery/business/business-rules.md` | BMad + tech-spec-writer | Compliance / invariants (create on demand) |
| `delivery/business/domain-model.md` | BMad + tech-spec-writer | Business-level entities + relations (create on demand) |
| `delivery/business/user-journeys.md` | BMad + tech-spec-writer | End-to-end flows (create on demand) |
| [`delivery/epics/README.md`](delivery/epics/README.md) | BMad + humans | Folder contract: two-layer story model, BMad's Plan-mode protocol, the one section BMad writes (`## Business Context`), handoff to the tech-spec-writer |
| `delivery/epics/epic-X/_epic.md` | All agents | Epic header. `## Business Context` written by BMad; rest written by humans or the tech-spec-writer |
| `delivery/epics/epic-X/story-NN.md` | All agents | **THE STORY**. `## Business Context` written by BMad; `## Skills` + technical sections written by `kiat-tech-spec-writer` in enrichment mode |

**The separation test:** `find kiat/.claude/` lists framework files only; `find kiat/delivery/` lists project files only. Neither contains the other. Inside `delivery/`, BMad writes exclusively in `business/` + the `## Business Context` section of `epics/`; the tech-spec-writer writes exclusively in the technical sections of `epics/`; neither touches `specs/` (technical conventions are human-owned).

---

## 🛡️ Enforcement Model: How We Make Agents Actually Follow Rules

> The honest truth: **skills and docs don't force agent compliance — they're just more text in the context window.** Kiat's enforcement model is designed around this reality. We don't pretend agents are deterministic. We make their shortcuts **auditable** instead.

### The 7 Enforcement Layers

Kiat layers seven mechanisms, from cheapest to hardest, so that even if one fails, the others catch the drift.

**Quick reference (scannable):**

1. **Machine-parseable verdicts** — reviewers emit `APPROVED / NEEDS_DISCUSSION / BLOCKED` on line 1
2. **Wall-clock retry budget** — 45-min fix budget per story instead of a cycle count
3. **Hard trigger rules for specialist skills** — greppable pattern list that *forces* the Clerk auth skill to run
4. **Mandatory audit lines** — skill invocations must leave a greppable trace in the output
5. **Context budgets** — hard per-agent token limit, pre-flight gate before launch
6. **Pre-coding validation gates** — `kiat-validate-spec` + `kiat-test-patterns-check` at Phase 0
7. **SubagentStop hooks** — runtime enforcement of audit lines via `.claude/settings.json`

The sections below explain each layer in detail.

#### Layer 1 — Machine-parseable verdicts (3-way outcome)

Reviewers (`kiat-backend-reviewer`, `kiat-frontend-reviewer`) run a review skill (`kiat-review-backend/SKILL.md`, `kiat-review-frontend/SKILL.md`) that **mandates** one of three verdicts on the first line of output:

```
VERDICT: APPROVED           ← merge-ready
VERDICT: NEEDS_DISCUSSION   ← judgment call, Team Lead arbitrates
VERDICT: BLOCKED            ← concrete fixes required, coder re-cycles
```

**Why 3-way and not binary?**
Binary (APPROVED / BLOCKED) forces reviewers to shoehorn nuance into "fix this" when the real answer is "a human needs to decide." That creates false blockers and sends coders chasing ambiguous feedback. `NEEDS_DISCUSSION` is the escape hatch for *"code is correct but I have a question for a human."*

**Team Lead handles each verdict deterministically** — no guessing:
- `APPROVED` → proceed to story validation
- `NEEDS_DISCUSSION` → Team Lead arbitrates (pattern, spec ambiguity, UX tradeoff) or escalates to the relevant author (`kiat-tech-spec-writer` for technical-layer gaps, BMad for `## Business Context` gaps, user for design / UX / architecture tradeoffs). **Never bounced back to the coder as "fix this"** — that was the old bug.
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

**Solution: a dedicated [`kiat-clerk-auth-review`](.claude/skills/kiat-clerk-auth-review/SKILL.md) skill with a hard trigger rule baked into both reviewer agents.**

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
| kiat-tech-spec-writer | unrestricted (reads business + specs on demand to write the story) |
| kiat-team-lead | 10k tokens |
| Backend-Coder / Frontend-Coder | **25k tokens** |
| Backend-Reviewer / Frontend-Reviewer | 20k tokens |

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

**6a — Spec ambiguity ([`kiat-validate-spec`](.claude/skills/kiat-validate-spec/SKILL.md))**

The single highest-ROI check in Kiat. Specs are written in prose; prose is ambiguous. A vague verb like "validate email" or "handle errors" hides behind well-written sentences, then explodes into a multi-cycle review ping-pong when the coder interprets it one way and the reviewer expects another. The two-layer story model doesn't fix this on its own — BMad's `## Business Context` can still be vague ("users should be able to manage their care plans"), and the tech-spec-writer's technical sections can still gap ("endpoint: `POST /patients` — validates input"). `kiat-validate-spec` runs against **both layers** and catches drift on either side.

Team Lead runs the `kiat-validate-spec` skill at **Phase 0a**, *before* the context budget check, *before* any coder is launched. The skill:
- Greps the spec for a curated list of vague verbs (*handle, validate, process, manage, support, optimize, ensure, proper, robust, efficient, reasonable*)
- Checks API/DB/UI contract completeness against the story scope
- Verifies cross-layer consistency (backend field names match frontend types)
- Verifies the **business/technical** cross-layer boundary too: if the Business Context mentions a persona, glossary term, or business rule, the technical sections must handle it (no orphan user-facing acceptance criteria without a matching technical check)
- Enumerates missing edge cases (concurrency, empty states, network failure)
- Outputs `SPEC_VERDICT: CLEAR | NEEDS_CLARIFICATION | BLOCKED`

**Why this catches the most bugs:** the tech-spec-writer is still in the conversation at Phase 0a, and BMad is one handoff away. A 5-minute clarification round (to either author, depending on which layer the gap is in) is infinitely cheaper than a 45-minute fix-budget retry cycle on a story where the coder guessed wrong.

**6b — Test-patterns inheritance ([`kiat-test-patterns-check`](.claude/skills/kiat-test-patterns-check/SKILL.md))**

The general review skills (`kiat-review-frontend`, `kiat-review-backend`) have 45+ checklist items each. Test flakiness pitfalls get skimmed under that load. Meanwhile, `testing.md` has 26+ documented anti-flakiness rules from real incidents — but nothing forces the coder to read them, so they don't.

Coders run `kiat-test-patterns-check` at **Step 0.5** (right after context budget self-check, before writing any code). The skill:
- Runs a **scope-detection questionnaire** (does this story have forms? auto-save? Clerk auth? RLS? Playwright E2E? wizards?)
- For every "yes", **forces a verbatim acknowledgment** of the applicable rules — paraphrasing not allowed, the rule text is load-bearing
- Emits `TEST_PATTERNS: ACKNOWLEDGED` + the full block for every applicable pattern
- Reviewers then **verify the acknowledgment exists** in the handoff AND cross-check that actual code matches what was acknowledged (drift → `VERDICT: BLOCKED`)

This converts *"did you read testing.md?"* from a trust question into a textual evidence question. The acknowledgment is either in the output or it isn't.

Full rules in [`.claude/skills/kiat-validate-spec/SKILL.md`](.claude/skills/kiat-validate-spec/SKILL.md) and [`.claude/skills/kiat-test-patterns-check/SKILL.md`](.claude/skills/kiat-test-patterns-check/SKILL.md).

---

#### Layer 7 — Hard runtime enforcement via SubagentStop hooks

Layers 1-6 are all **soft enforcement**: skills, prompts, audit lines. They work when the agent chooses to follow them, and they leave a paper trail when the agent doesn't. But a sufficiently rushed or confused agent can still hand off without emitting the load-bearing lines, and the downstream consumer only notices after the fact.

**Layer 7 makes two specific protocol lines non-negotiable at the runtime level**, via Claude Code's `SubagentStop` hook mechanism wired through [`.claude/settings.json`](.claude/settings.json):

| Hook | Agents matched | What it checks | Script |
|---|---|---|---|
| **Test-patterns acknowledgment** | `kiat-backend-coder`, `kiat-frontend-coder` | The session transcript must contain `TEST_PATTERNS: ACKNOWLEDGED` before the agent is allowed to finish | [`check-test-patterns-ack.sh`](.claude/tools/hooks/check-test-patterns-ack.sh) |
| **Reviewer verdict line** | `kiat-backend-reviewer`, `kiat-frontend-reviewer` | The transcript must contain a line matching `VERDICT: (APPROVED|NEEDS_DISCUSSION|BLOCKED)` | [`check-verdict-line.sh`](.claude/tools/hooks/check-verdict-line.sh) |

**Semantics:** each hook receives the transcript path on stdin, greps it for the required pattern, and exits `0` (pass) or `2` (block). On exit 2, Claude Code shows the hook's stderr message to the model and forces it to self-correct before actually handing off — it's a pre-commit hook, but for the agent's final output.

**Why this matters:** the 6 previous layers can all be fooled by a coder or reviewer that "forgets" to emit the audit line. Layer 7 closes that gap — you can't forget, because the hook refuses to let you finish. The hook is trivially scriptable (both files are ~30 lines of bash), runs locally with zero dependencies beyond `grep`, and emits a specific failure message telling the model exactly which line is missing and why.

**Combined with the skill eval loop** ([Skill Evaluation](#-skill-evaluation-proving-the-skills-actually-work)), this gives a two-layer quality gate: hooks catch protocol violations at runtime, evals catch skill design regressions before shipping.

---

### Complementary Mechanism — Project Memory (cross-story coherence)

The 7 enforcement layers above all operate at **story scope**: they fire on one story at a time, catch problems within that story, and have no view of the project as a whole. That's intentional — agents are deliberately isolated to keep context budgets tight.

**But isolation has a cost: coherence drift.** Story 5 can invent a new pattern without knowing story 3 already solved the same problem differently. Over 15-20 stories, the project becomes a salad of inconsistent naming, duplicated components, and contradictory architectural choices. Each story is locally correct; the project is globally incoherent.

**[`delivery/specs/project-memory.md`](delivery/specs/project-memory.md) is Kiat's answer to this.** It's a living document that captures **emergent patterns** across stories:

- Naming conventions that emerged from real implementations
- Shared UI components that should be reused, not recreated
- API patterns by domain (how endpoints are structured per resource family)
- Architectural decisions that span multiple stories
- Known gotchas specific to this project

**It's the only cross-story coherence mechanism in Kiat.** Unlike the 7 enforcement layers (which are mechanical and scoped to one story), `project-memory.md` is a **shared memory** that the tech-spec-writer reads *before* writing a new story's technical spec, to ensure the new story aligns with what's already established.

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
7. **SubagentStop hooks for hard runtime enforcement** → coders and reviewers physically can't hand off without the load-bearing protocol lines

---

## 🧪 Skill Evaluation: Proving the Skills Actually Work

Skills are prompts, and prompts don't have unit tests. Reading a SKILL.md ten times won't tell you whether Claude actually behaves the way the skill says it will. The only honest answer to *"does this skill pull its weight?"* is a **behavioral benchmark** — spawn two subagents on the same task, one with the skill loaded and one without, and measure the delta. If the delta is zero, the skill is ceremonial. If it's large, the skill is doing real work. Kiat uses the methodology from [`skill-creator`](https://github.com/anthropics/skills) verbatim: write fixtures, write assertions, spawn `with_skill` + `baseline` subagents in parallel, grade mechanically, aggregate into a `benchmark.json`, review in an HTML viewer, iterate.

**Iteration-1 example (2026-04-11)** — the two most foundational skills, the ones that run on every story in the pipeline. 3 fixtures per skill (a clean story, a vague-verbs story, a structurally broken story for `validate-spec`; rich / under-specified / narrow-scope backend-only for `test-patterns-check`), spawned in parallel with a baseline for each:

| Skill | with_skill pass | baseline pass | Δ pass | Δ time | Δ tokens |
|---|---|---|---|---|---|
| **kiat-validate-spec** | **100%** (17/17) | 63.3% (11/17) | **+37 pts** | ~0 s | +5k |
| **kiat-test-patterns-check** | **100%** (31/31) | 68.9% (22/31) | **+31 pts** | **−26 s** 🔥 | +7k |

Two findings worth keeping: (1) `kiat-test-patterns-check` is both **more accurate *and* faster** with the skill loaded — the router short-circuits to the relevant blocks (1 block on a narrow-scope backend-only fixture instead of 13 free-form concerns from the baseline), so the compact structured output wins on both axes. (2) The baseline on the "clean" fixture caught real cross-layer issues the skill missed (RFC3339Nano vs JS Date precision, RLS `WITH CHECK` omission) — useful signal that iteration-2 should add a deeper cross-layer consistency category to `validate-spec`. The extra ~5-7k tokens per run (to read the SKILL.md + applicable block files) is ~25% of the 25k coder context budget — modest price for a skill that demonstrably changes behavior.

Re-run the loop any time a skill is refactored, a new skill is shipped, or a production incident traces back to skill drift. Don't run it on a schedule. The full iteration-1 workspace (fixtures, eval_metadata, grading, benchmark, HTML viewer) is at `/tmp/kiat-skills-workspace/` during the session that produced it; see [`skill-creator`'s SKILL.md](https://github.com/anthropics/skills) for the canonical commands.

---

## 📊 Monitoring & Reporting

> **Philosophy:** You can't improve what you don't measure. Every enforcement layer above already emits structured audit lines — Kiat just needs a cheap way to collect and render them. No dashboards. No infra. Just a JSONL log, a Python script, and a markdown report you read once a week.

### What Gets Tracked

Five metrics that actually change your behavior when they drift:

| Metric | What it tells you |
|---|---|
| **Spec validation outcomes** | Are both layers (BMad `## Business Context` and tech-spec-writer technical sections) clear, or is the clarification rate climbing on one of them? |
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

- **CLEAR rate < 70%** → stories are shipping with ambiguities. Check which layer the gaps are in: if it's `## Business Context` drift, BMad's Capture/Plan discipline needs tightening (probably a persona or glossary term missing in `delivery/business/`); if it's technical-layer drift, the tech-spec-writer's clarification loop needs to be more aggressive.
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

## 📁 Folder Layout

The layout enforces a strict separation: **`.claude/` = IA/Kiat framework**, **`delivery/` = project-owned**. No mixing.

```
kiat/
├── CLAUDE.md                          # Ambient meta-rules (auto-loaded by Claude Code)
├── README.md                          # This file — Kiat vision + enforcement model
├── INDEX.md                           # Navigation hub
├── GETTING_STARTED.md                 # New-user onboarding
│
├── .claude/                           # ═══ IA / Kiat framework ONLY ═══
│   ├── README.md                      # Framework doc index
│   ├── settings.json                  # Permissions allowlist + SubagentStop hook wiring (Layer 7)
│   ├── agents/                        # 6 kiat-* agent system prompts
│   │   ├── kiat-tech-spec-writer.md   # Default entry point: writes story specs
│   │   ├── kiat-team-lead.md          # Technical orchestrator (runs the pipeline)
│   │   ├── kiat-backend-coder.md      # Go + Gin + Bun + Clean Architecture
│   │   ├── kiat-frontend-coder.md     # Next.js + React + Shadcn + Tailwind v4
│   │   ├── kiat-backend-reviewer.md   # Backend quality gate (3-way verdict)
│   │   └── kiat-frontend-reviewer.md  # Frontend quality gate (3-way verdict)
│   ├── skills/                        # 6 kiat-* skills (all folder-based per Agent Skills spec)
│   │   ├── kiat-validate-spec/        # Pre-coding spec validation (Layer 6a)
│   │   │   └── SKILL.md
│   │   ├── kiat-review-backend/       # Structured backend review
│   │   │   ├── SKILL.md               #   Protocol + verdict format
│   │   │   └── references/checklist.md
│   │   ├── kiat-review-frontend/      # Structured frontend review
│   │   │   ├── SKILL.md
│   │   │   └── references/checklist.md
│   │   ├── kiat-clerk-auth-review/    # Clerk auth specialist (Layer 3, conditional)
│   │   │   ├── SKILL.md
│   │   │   └── references/checks.md
│   │   ├── kiat-test-patterns-check/  # Forced-response test patterns (Layer 6b)
│   │   │   ├── SKILL.md               #   Router + scope detection
│   │   │   └── references/            #   9 pattern blocks loaded selectively
│   │   └── kiat-ui-ux-search/         # Wrapper for external ui-ux-pro-max skill
│   │       ├── SKILL.md               #   Lightweight router (~1k tokens)
│   │       └── references/            #   categories.md, when-to-use.md, invoke-patterns.md
│   ├── specs/                         # 4 framework specs — machinery, not conventions
│   │   ├── available-skills.md        # Skill registry (read by tech-spec-writer)
│   │   ├── context-budgets.md         # Per-agent token budgets (Layer 5)
│   │   ├── metrics-events.md          # JSONL event log schema (rollup-first v1.1)
│   │   └── failure-patterns.md        # Reactive failure pattern registry
│   └── tools/                         # Framework utilities
│       ├── report.py                  # Weekly health report generator
│       ├── doc-audit.py               # M1 (tokens) + M2 (structure) audit on delivery/specs/
│       └── hooks/                     # SubagentStop hooks (Layer 7 enforcement)
│           ├── check-test-patterns-ack.sh   # Blocks coder handoff if TEST_PATTERNS: ACKNOWLEDGED missing
│           └── check-verdict-line.sh        # Blocks reviewer handoff if VERDICT: line 1 missing
│
├── delivery/                          # ═══ Project-owned ONLY ═══
│   ├── README.md                      # Delivery conventions (epics, stories, common cmds)
│   ├── business/                      # Business layer — BMad writes here (Capture mode)
│   │   ├── README.md                  # Folder contract + BMad writing protocol (Explore/Capture/Plan/Review modes)
│   │   ├── glossary.md                # Domain terms (create on demand)
│   │   ├── personas.md                # User personas (create on demand)
│   │   ├── business-rules.md          # Compliance / invariants (create on demand)
│   │   ├── domain-model.md            # Entities + relations at business level (create on demand)
│   │   └── user-journeys.md           # End-to-end flows (create on demand)
│   ├── epics/                         # The backlog — two-layer story files (Jira-equivalent)
│   │   ├── README.md                  # Two-layer story model + BMad writing protocol (Plan mode → ## Business Context only)
│   │   ├── epic-template/             # Templates for new epics
│   │   │   ├── _epic.md               # Both layers: Business Context (BMad) + technical
│   │   │   └── story-NN-slug.md       # Both layers: Business Context (BMad) + Skills/API/DB/FE/tests (tech-spec-writer)
│   │   └── epic-N-name/               # Per-epic folders — two authors, two layers per file
│   │       ├── _epic.md               # BMad writes Business Context; tech-spec-writer + humans fill the rest
│   │       └── story-NN.md            # BMad writes Business Context; tech-spec-writer enriches in enrichment mode
│   ├── metrics/                       # Runtime data (Team Lead-written only)
│   │   ├── README.md                  # What lives here + writer/reader rules
│   │   └── events.jsonl               # (generated when stories run, gitignored)
│   └── specs/                         # Technical conventions — humans + agents read these
│       ├── api-conventions.md         # REST design, error codes
│       ├── architecture-clean.md      # Clean Architecture 4 layers
│       ├── ARCHITECTURE-OVERVIEW.md   # High-level project architecture
│       ├── backend-conventions.md     # Project structure, naming, logging
│       ├── clerk-patterns.md          # Clerk auth flows (project-side)
│       ├── database-conventions.md    # Migrations, RLS, timestamps
│       ├── deployment.md              # Env vars, dev modes, production guards
│       ├── design-system.md           # Colors, spacing, typography
│       ├── frontend-architecture.md   # React patterns, hooks, accessibility
│       ├── git-conventions.md         # Branches, commits, PR discipline
│       ├── project-memory.md          # Emergent cross-story patterns (coherence)
│       ├── security-checklist.md      # OWASP, RLS testing
│       ├── service-communication.md   # DI patterns, error handling
│       └── testing.md                 # Anti-flakiness rules + CI gate
```

**The separation test:** `find kiat/.claude/` lists the exact framework files (Kiat IP). `find kiat/delivery/` lists the exact project-owned files (your project's code and conventions). Neither list contaminates the other.

---

## 🚀 Getting Started with Kiat

The short version: read [`GETTING_STARTED.md`](GETTING_STARTED.md) for the canonical onboarding walkthrough. It covers customizing `delivery/specs/` to your stack, bootstrapping `delivery/business/` with BMad, creating the first epic, and running the first story through the pipeline.

The even shorter version, once you're set up:

1. **Talk to BMad** about the product need in natural language. BMad captures evergreen domain facts into `delivery/business/` (Capture mode), then drafts a story under `delivery/epics/epic-X/story-NN.md` with only the `## Business Context` section filled in (Plan mode).
2. **Invoke `kiat-tech-spec-writer`** on the story file. It detects the pre-existing Business Context, runs in enrichment mode, and appends Skills + API contracts + database + frontend + edge cases + tests. Self-validates.
3. **Invoke `kiat-team-lead`** on the enriched story as the **main session thread** (not via `@agent-kiat-team-lead`, because sub-agents can't spawn sub-agents in Claude Code). It runs Phase 0 → parallel coders → reviewers → rollup.
4. Watch the rollup event in `delivery/metrics/events.jsonl` and the PR it produces.
5. Run `python3 .claude/tools/report.py` once a week to check pipeline health.

**Pure technical work** (refactor, bug fix, no new business intent) — skip step 1 and go straight to the tech-spec-writer. It will operate in greenfield mode and produce both layers itself.

**BMad setup** — BMad is external to Kiat. Point any Claude session at [`delivery/business/README.md`](delivery/business/README.md) and [`delivery/epics/README.md`](delivery/epics/README.md) — these two folder READMEs define the full contract BMad must respect (4 input modes, Capture-mode decision tree, Plan-mode handoff, boundaries). No agent definition, no prompt engineering — just reading the folder contracts is enough.

---

## 📖 Further Reading

- [`CLAUDE.md`](CLAUDE.md) — Universal meta-rules auto-loaded into every Kiat agent (framework/project separation, load-on-demand rule, audit trail rule)
- [`GETTING_STARTED.md`](GETTING_STARTED.md) — Onboarding walkthrough for a new project
- [`INDEX.md`](INDEX.md) — Navigation hub (all docs at a glance)
- [`.claude/agents/`](.claude/agents/) — The 6 kiat-* agent system prompts
- [`.claude/skills/`](.claude/skills/) — The 6 kiat-* skills (SKILL.md + references/)
- [`.claude/specs/`](.claude/specs/) — Framework machinery (budgets, metrics schema, failure patterns, skill registry)
- [`delivery/specs/`](delivery/specs/) — Project technical conventions (architecture, security, testing, ...)
- [`delivery/business/README.md`](delivery/business/README.md) — Business layer folder contract + BMad writing protocol (Capture mode, 5 canonical files, sizing discipline)
- [`delivery/epics/README.md`](delivery/epics/README.md) — Two-layer story model + BMad writing protocol (Plan mode, `## Business Context` boundary, handoff to tech-spec-writer)
- Within this file: [Enforcement Model](#-enforcement-model-how-we-make-agents-actually-follow-rules), [Skill Evaluation](#-skill-evaluation-proving-the-skills-actually-work), [Monitoring & Reporting](#-monitoring--reporting)

---

## 🎓 Key Principles

1. **Two layers, two authors, one file.** Every story has a `## Business Context` (written by BMad, business language) and technical sections (written by `kiat-tech-spec-writer`, English). Each author has a hard contract forbidding them from writing in the other's territory.
2. **Spec-first.** Agents code from written specs, never from vague requirements. BMad is the upstream funnel for business intent; the tech-spec-writer is the Kiat-side funnel for technical execution.
3. **Single source of truth.** Each artifact (convention, spec, domain fact, story) lives in exactly one place. Never duplicate — link. Stories link to `delivery/business/` for persona/glossary/rule definitions; they never restate them.
4. **Load only what you need.** Agents load the minimum context for the specific task, not the full codebase. Skills follow progressive disclosure (SKILL.md → references/ on demand). BMad's 5 domain files are read selectively (glossary + domain-model for domain work, personas + user-journeys for user-facing work, business-rules for compliance work).
5. **Convergence, not ping-pong.** Reviewer feedback is batched — coder fixes everything in one pass. 3-way verdicts + 45-minute fix budget cap the loop.
6. **Gate at the protocol, not at the test suite.** Until there's real code and real CI, the SubagentStop hooks + the 3-way verdict + the reviewer's test-pattern drift check are the enforcement surface. Tests will come later, as a complement, not as the primary gate.
7. **Human approval.** You decide when specs are good, when code is ready to merge, and when to escalate. The pipeline runs autonomously within those bounds; the rollup event is the checkpoint.
8. **Parallelizable at every layer.** Backend and frontend coders run simultaneously. Reviewers run simultaneously. Multiple stories can be processed in parallel as long as their context budgets and `delivery/business/` reads don't collide.

---

**Let's ship. 🚀**
