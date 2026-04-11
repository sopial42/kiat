# Framework Doc Index (`.claude/`)

This folder is **Kiat framework machinery only**. Project conventions live in `delivery/specs/`, not here.

If you're looking for project-level docs (React patterns, REST conventions, Tailwind tokens, etc.), go to [`delivery/specs/`](../delivery/specs/). If you're looking for universal coding rules that apply across all projects using Kiat, read [`CLAUDE.md`](../CLAUDE.md) at the project root — it's the ambient context auto-loaded by Claude Code.

---

## What's in `.claude/`

```
.claude/
├── README.md                      # This file (framework doc index)
├── settings.json                  # Permissions allowlist + SubagentStop hook wiring (Layer 7)
├── agents/                        # 6 kiat-* agent system prompts
│   ├── kiat-tech-spec-writer.md   # Default entry point: informal request → structured story
│   ├── kiat-team-lead.md          # Pipeline orchestrator
│   ├── kiat-backend-coder.md
│   ├── kiat-frontend-coder.md
│   ├── kiat-backend-reviewer.md
│   └── kiat-frontend-reviewer.md
├── skills/                        # 6 kiat-* skills (all folder-based per Agent Skills spec)
│   ├── kiat-validate-spec/
│   │   └── SKILL.md
│   ├── kiat-review-backend/
│   │   ├── SKILL.md
│   │   └── references/checklist.md
│   ├── kiat-review-frontend/
│   │   ├── SKILL.md
│   │   └── references/checklist.md
│   ├── kiat-clerk-auth-review/
│   │   ├── SKILL.md
│   │   └── references/checks.md
│   ├── kiat-test-patterns-check/   # Router + 9 selective blocks
│   │   ├── SKILL.md
│   │   └── references/             # block-a-forms.md … block-i-wizards.md
│   └── kiat-ui-ux-search/          # Wrapper for external ui-ux-pro-max
│       ├── SKILL.md
│       └── references/
├── specs/                         # 4 framework specs (machinery, not conventions)
│   ├── available-skills.md        # Contextual skill registry (read by tech-spec-writer)
│   ├── context-budgets.md         # Per-agent token budgets (Layer 5)
│   ├── metrics-events.md          # JSONL event log schema
│   └── failure-patterns.md        # Reactive failure pattern registry
└── tools/                         # Framework utilities
    ├── report.py                  # Weekly health report generator
    ├── doc-audit.py               # M1 (tokens) + M2 (structure) audit on delivery/specs/
    └── hooks/                     # SubagentStop hooks (Layer 7 enforcement)
        ├── check-test-patterns-ack.sh
        └── check-verdict-line.sh
```

**Note:** `CLAUDE.md` lives at the **project root**, not in `.claude/`. This is a deliberate exception to the "everything framework is in `.claude/`" rule — Claude Code auto-loads `CLAUDE.md` from the project root as ambient context for every session. Placing it elsewhere would break auto-loading.

**Rule:** nothing in `.claude/` should be project-specific. If you find yourself wanting to edit a file here for "your project", that file belongs in `delivery/` instead.

---

## Who Reads What

### All agents (ambient context)
- [`../CLAUDE.md`](../CLAUDE.md) — universal meta-rules auto-loaded by Claude Code from the project root (separation rule, load-on-demand rule, pointers to project conventions)

### `kiat-tech-spec-writer` reads
- [./specs/available-skills.md](./specs/available-skills.md) — to decide which contextual skills to list in a story's `## Skills` section
- [./skills/kiat-validate-spec/SKILL.md](./skills/kiat-validate-spec/SKILL.md) — self-validation before handoff
- Project conventions in `../delivery/specs/` + business docs in `../delivery/business/` (on-demand, only the ones relevant to the story scope)

### `kiat-team-lead` reads
- [./specs/context-budgets.md](./specs/context-budgets.md) — to run Phase 0b pre-flight check
- [./specs/metrics-events.md](./specs/metrics-events.md) — to emit JSONL events at phase transitions
- [./specs/failure-patterns.md](./specs/failure-patterns.md) — to consult before escalation
- [./skills/kiat-validate-spec/SKILL.md](./skills/kiat-validate-spec/SKILL.md) — invoked at Phase 0a (defense in depth)

### `kiat-backend-coder` / `kiat-frontend-coder` read
- [./skills/kiat-test-patterns-check/SKILL.md](./skills/kiat-test-patterns-check/SKILL.md) — invoked at Step 0.5
- [./specs/context-budgets.md](./specs/context-budgets.md) — for self-check at Step 0
- Any contextual skill listed in the story's `## Skills` section
- Plus project conventions in `../delivery/specs/` (backend-conventions, frontend-architecture, etc.)

### `kiat-backend-reviewer` / `kiat-frontend-reviewer` read
- [./skills/kiat-review-backend/SKILL.md](./skills/kiat-review-backend/SKILL.md) / [./skills/kiat-review-frontend/SKILL.md](./skills/kiat-review-frontend/SKILL.md) — REQUIRED
- [./skills/kiat-clerk-auth-review/SKILL.md](./skills/kiat-clerk-auth-review/SKILL.md) — CONDITIONAL (hard trigger rule)
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
