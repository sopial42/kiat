# Framework Doc Index (`.claude/`)

This folder is **Kiat framework machinery only**. Project conventions live in `delivery/specs/`, not here.

If you're looking for project-level docs (React patterns, REST conventions, Tailwind tokens, etc.), go to [`delivery/specs/`](../../delivery/specs/). If you're looking for universal coding rules that apply across all projects using Kiat, stay here and read [CLAUDE.md](CLAUDE.md).

---

## What's in `.claude/`

```
.claude/
├── agents/                        # 5 kiat-* agent system prompts
│   ├── kiat-team-lead.md
│   ├── kiat-backend-coder.md
│   ├── kiat-frontend-coder.md
│   ├── kiat-backend-reviewer.md
│   └── kiat-frontend-reviewer.md
├── skills/                        # 5 kiat-* skills (review checklists + specialists)
│   ├── kiat-review-backend.md
│   ├── kiat-review-frontend.md
│   ├── kiat-clerk-auth-review.md
│   ├── kiat-validate-spec.md
│   └── kiat-test-patterns-check/   # Router + 9 selective blocks
│       ├── SKILL.md
│       └── blocks/
├── specs/                         # 3 framework specs (machinery, not conventions)
│   ├── context-budgets.md         # Per-agent token budgets (Layer 5)
│   ├── metrics-events.md          # JSONL event log schema
│   └── failure-patterns.md        # Reactive failure pattern registry
├── tools/                         # Framework utilities
│   └── report.py                  # Weekly health report generator
└── docs/                          # Docs read by agents
    ├── CLAUDE.md                  # Universal coding rules (all agents read this)
    └── README.md                  # This file
```

**Rule:** nothing in `.claude/` should be project-specific. If you find yourself wanting to edit a file here for "your project", that file belongs in `delivery/` instead.

---

## Who Reads What

### All agents (ambient context)
- [CLAUDE.md](CLAUDE.md) — universal coding rules (secrets, naming, error handling, testing, git)

### `kiat-team-lead` reads
- [../specs/context-budgets.md](../specs/context-budgets.md) — to run Phase 0b pre-flight check
- [../specs/metrics-events.md](../specs/metrics-events.md) — to emit JSONL events at phase transitions
- [../specs/failure-patterns.md](../specs/failure-patterns.md) — to consult before escalation
- [../skills/kiat-validate-spec.md](../skills/kiat-validate-spec.md) — invoked at Phase 0a

### `kiat-backend-coder` / `kiat-frontend-coder` read
- [../skills/kiat-test-patterns-check/SKILL.md](../skills/kiat-test-patterns-check/SKILL.md) — invoked at Step 0.5
- [../specs/context-budgets.md](../specs/context-budgets.md) — for self-check at Step 0
- Plus project conventions in `delivery/specs/` (backend-conventions, frontend-architecture, etc.)

### `kiat-backend-reviewer` / `kiat-frontend-reviewer` read
- [../skills/kiat-review-backend.md](../skills/kiat-review-backend.md) / [../skills/kiat-review-frontend.md](../skills/kiat-review-frontend.md) — REQUIRED
- [../skills/kiat-clerk-auth-review.md](../skills/kiat-clerk-auth-review.md) — CONDITIONAL (hard trigger rule)
- Community skills (`differential-review`, `react-best-practices`, etc.) when applicable

### Humans read (weekly)
- `python3 .claude/tools/report.py` — to check system health after each epic

---

## How This Relates to Project Docs

**Framework docs** (`.claude/`) describe *how Kiat works*. They rarely change and are not project-specific.

**Project docs** (`delivery/specs/`) describe *your project's conventions* (REST design, React patterns, design tokens, Clerk flows, testing pitfalls). They evolve per project.

The clean separation means:
- Extract Kiat to a new project: copy `.claude/` → done. Your project-specific conventions in `delivery/specs/` stay behind OR get customized in the new project.
- Add a project-specific rule: update `delivery/specs/<relevant>.md`. Don't touch `.claude/`.
- Change how Kiat works: update `.claude/agents/`, `.claude/skills/`, or `.claude/specs/`. This is a framework change, not a project change.

---

## If You Break the Separation

If you find yourself editing a file in `.claude/` to add something like *"our project uses Tailwind v4"* or *"our error codes are X, Y, Z"*, **stop**. That content belongs in `delivery/specs/` (design-system, api-conventions, backend-conventions, etc.). Put it there instead.

The test: `find kiat/.claude/` should list Kiat framework files only. `find kiat/delivery/` should list project-owned files only. Neither list should contain the other.
