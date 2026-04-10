# CLAUDE.md — Ambient Context (Kiat Framework)

You are an instance of Claude operating in a project that uses the **Kiat framework**. This file is your entry contract: read it once, then work from the pointers below.

**This file contains no project rules.** Project rules live in `delivery/specs/`. This file only contains meta-rules about how any Claude instance should behave, plus pointers to the right doc at the right time.

---

## Kiat's Core Rule: Framework / Project Separation

**Do not mix framework and project code.**

- **`.claude/`** → Kiat framework machinery (agents, skills, framework specs, tools). Touch this only when you are changing Kiat itself, never to adapt it to "your project".
- **`delivery/`** → Project-owned (conventions, epics, stories, runtime metrics). This is where project-specific edits belong.

**Test before editing anything in `.claude/`:** if the content you want to add is about *your specific project* (your stack, your REST contracts, your design tokens, your git workflow), it belongs in `delivery/specs/` instead. No exceptions.

---

## Meta-Rules for Any Claude Instance in This Project

These are the only rules that live in ambient context because they're about *how a LLM should behave*, not about project conventions:

1. **Spec first.** Never code from a vague requirement. Read the spec; ask for clarification if unclear. Guessing is a bug.
2. **Verify before asserting.** Don't claim a function exists — Grep for it. Don't claim a file is at path X — Read it to confirm. Don't reason about code you haven't read.
3. **One source of truth per artifact.** If a rule exists in `delivery/specs/X.md`, do not restate it here, in another doc, or in an agent prompt. Link instead.
4. **Context budget is finite. Do NOT chase references.**
   - Load only what you need *for the current specific task*, not what looks interesting.
   - **A link in a doc is NOT an instruction to Read that file.** Seeing `[design-system.md](...)` in a spec means "this file exists if you need it", not "open it now".
   - Before you Read any file beyond the ones explicitly listed in your agent definition's "Context You Have" section, ask yourself: *"do I need this for the specific thing the user asked me to do right now?"* If the answer is not a clear yes, don't load it.
   - Never recursively load files just because they're mentioned. If `backend-conventions.md` references `architecture-clean.md`, you only load `architecture-clean.md` if your current task needs the 4-layer pattern specifically — not because the link exists.
   - When in doubt, delegate to the Kiat agent whose role fits the task instead of trying to do everything yourself.
5. **Audit trail over trust.** If a skill must be invoked, invoke it and leave the audit line in your output. Skipping silently is a protocol violation — even if you're confident the skill's check passes.

---

## How to Work in a Kiat Project (By Role)

### If you are the Tech Spec Writer (entry point for new work)

Your full protocol is in [`.claude/agents/kiat-tech-spec-writer.md`](.claude/agents/kiat-tech-spec-writer.md). You translate informal user requests into structured story files in `delivery/epics/epic-X/story-NN.md`, decide which contextual skills the coders will need (consulting [`.claude/specs/available-skills.md`](.claude/specs/available-skills.md)), self-validate via `kiat-validate-spec`, and hand off to Team Lead. **You are the default entry point** for any user request that becomes a story — never let coders start without going through you first, except when an existing story file is being re-executed.

### If you are Team Lead (orchestrator)

Your full protocol is in [`.claude/agents/kiat-team-lead.md`](.claude/agents/kiat-team-lead.md). Key phases: 0a spec validation, 0b context budget check (reads the story's `## Skills` section to validate budget), parallel coder launch, 3-way verdict handling, 45-min fix budget, metrics emission, failure pattern consultation at escalation. You receive stories that the tech spec writer has already written and validated.

**Invocation requirement**: Team Lead uses the `Agent` tool to spawn coders and reviewers, which only works when Team Lead runs as the **main session thread** — sub-agents cannot spawn other sub-agents in Claude Code. Launch Team Lead via `claude --agent kiat-team-lead`, or set `"agent": "kiat-team-lead"` as the project default in `.claude/settings.json`. Invoking Team Lead via `@agent-kiat-team-lead` from an ordinary Claude session will fail silently when it tries to spawn coders.

### If you are a Coder (backend or frontend)

Your agent definition ([kiat-backend-coder.md](.claude/agents/kiat-backend-coder.md) or [kiat-frontend-coder.md](.claude/agents/kiat-frontend-coder.md)) contains all critical rules baked in: Step 0 context budget self-check, Step 0.5 test patterns acknowledgment, spec reading, planning, building, test running, handoff. Read the story's `## Skills` section at Step 1 to know which contextual skills to load (in addition to the always-loaded `kiat-test-patterns-check`).

### If you are a Reviewer

Your agent definition ([kiat-backend-reviewer.md](.claude/agents/kiat-backend-reviewer.md) or [kiat-frontend-reviewer.md](.claude/agents/kiat-frontend-reviewer.md)) enforces the required review skill, the conditional Clerk auth skill (with hard trigger rule), and the `TEST_PATTERNS: ACKNOWLEDGED` verification. Output format is machine-parseable: first line must be `VERDICT: APPROVED | NEEDS_DISCUSSION | BLOCKED`.

---

## Where to Find Project Rules

When you need project-specific information, go directly to the right file under `delivery/specs/`. Load on demand, not preemptively.

| What you need | Where to look |
|---|---|
| Clean Architecture, 4 layers | [`delivery/specs/architecture-clean.md`](delivery/specs/architecture-clean.md) |
| Backend project structure, naming, error codes, logging | [`delivery/specs/backend-conventions.md`](delivery/specs/backend-conventions.md) |
| Service communication, dependency injection | [`delivery/specs/service-communication.md`](delivery/specs/service-communication.md) |
| Frontend patterns, hooks, RSC boundary | [`delivery/specs/frontend-architecture.md`](delivery/specs/frontend-architecture.md) |
| Design system, colors, spacing, Tailwind tokens | [`delivery/specs/design-system.md`](delivery/specs/design-system.md) |
| REST design, error codes, status codes | [`delivery/specs/api-conventions.md`](delivery/specs/api-conventions.md) |
| Database migrations, RLS, timestamps | [`delivery/specs/database-conventions.md`](delivery/specs/database-conventions.md) |
| Security checklist, OWASP, secrets, RLS testing | [`delivery/specs/security-checklist.md`](delivery/specs/security-checklist.md) |
| Clerk auth flows, test mode, token handling | [`delivery/specs/clerk-patterns.md`](delivery/specs/clerk-patterns.md) |
| Testing anti-flakiness, CI gate, Playwright + Venom | [`delivery/specs/testing.md`](delivery/specs/testing.md) |
| Git branches, commits, PR discipline | [`delivery/specs/git-conventions.md`](delivery/specs/git-conventions.md) |
| Environment vars, production guards, deployment | [`delivery/specs/deployment.md`](delivery/specs/deployment.md) |
| Common dev commands (`make dev`, `npm run`, etc.) | [`delivery/README.md`](delivery/README.md) |
| Business / domain documentation (glossary, personas, rules, domain model, user journeys) | [`delivery/business/`](delivery/business/) |
| Epic and story technical specs (written by kiat-tech-spec-writer) | `delivery/epics/epic-X/story-NN.md` |
| Epic / story templates | [`delivery/epics/epic-template/`](delivery/epics/epic-template/) |

---

## Where to Find Framework Rules

Framework machinery — **not project-specific**, do not edit per project:

| What you need | Where to look |
|---|---|
| 6 enforcement layers, monitoring philosophy, vision | [`README.md`](README.md) |
| Navigation hub | [`INDEX.md`](INDEX.md) |
| Agent definitions (6 kiat-* agents) | [`.claude/agents/`](.claude/agents/) |
| Skill definitions (6 kiat-* skills) | [`.claude/skills/`](.claude/skills/) |
| Context budgets spec (Layer 5) | [`.claude/specs/context-budgets.md`](.claude/specs/context-budgets.md) |
| Metrics event schema (JSONL) | [`.claude/specs/metrics-events.md`](.claude/specs/metrics-events.md) |
| Failure patterns registry | [`.claude/specs/failure-patterns.md`](.claude/specs/failure-patterns.md) |
| Available skills registry (read by tech-spec-writer) | [`.claude/specs/available-skills.md`](.claude/specs/available-skills.md) |
| Weekly health report tool | `python3 kiat/.claude/tools/report.py` |
| Doc audit tool (M1 size + M2 structure) | `python3 kiat/.claude/tools/doc-audit.py` |

---

**That's it.** Everything else is a pointer, not a rule. If you catch yourself duplicating content from `delivery/specs/` into this file or into any other `.claude/` file, stop — you're violating the "one source of truth" rule.
