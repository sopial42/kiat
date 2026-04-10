# Kiat Starter Kit — Complete Index

Everything in Kiat, grouped by whether it's **framework IA** (`.claude/`) or **project-owned** (`delivery/`, `checklists/`, `patterns/`).

---

## 📖 Quick Start (Read These First)

1. **[README.md](README.md)** — Vision, architecture, enforcement model (6 layers), monitoring
2. **[GETTING_STARTED.md](GETTING_STARTED.md)** — New-user onboarding
3. **[structure.md](structure.md)** — Architecture decision log
4. **[CLAUDE.md](CLAUDE.md)** — Universal coding rules

---

## 🛡️ Framework (`.claude/` — IA/Kiat, do not mix with project)

### Agents (6 — all `kiat-` prefixed)

| Agent | File | Role |
|-------|------|------|
| **Tech Spec Writer** | [.claude/agents/kiat-tech-spec-writer.md](.claude/agents/kiat-tech-spec-writer.md) | **Default entry point** — translates user requests into structured story files, decides contextual skills |
| **Team Lead** | [.claude/agents/kiat-team-lead.md](.claude/agents/kiat-team-lead.md) | Technical orchestrator (retry loops, test gates, story validation, metrics emission) |
| **Backend-Coder** | [.claude/agents/kiat-backend-coder.md](.claude/agents/kiat-backend-coder.md) | Build Go API (Clean Arch, DI, Venom tests) |
| **Frontend-Coder** | [.claude/agents/kiat-frontend-coder.md](.claude/agents/kiat-frontend-coder.md) | Build React UI (Shadcn, hooks, Playwright tests) |
| **Backend-Reviewer** | [.claude/agents/kiat-backend-reviewer.md](.claude/agents/kiat-backend-reviewer.md) | Backend quality gate (3-way verdict) |
| **Frontend-Reviewer** | [.claude/agents/kiat-frontend-reviewer.md](.claude/agents/kiat-frontend-reviewer.md) | Frontend quality gate (3-way verdict) |

### Skills (6 — all `kiat-` prefixed)

| Skill | File | Purpose |
|-------|------|---------|
| **Validate Spec** | [.claude/skills/kiat-validate-spec.md](.claude/skills/kiat-validate-spec.md) | Pre-coding spec ambiguity detector (Layer 6a, used by tech-spec-writer + Team Lead) |
| **Review Backend** | [.claude/skills/kiat-review-backend.md](.claude/skills/kiat-review-backend.md) | Structured backend review checklist (Clean Arch, security, Venom) |
| **Review Frontend** | [.claude/skills/kiat-review-frontend.md](.claude/skills/kiat-review-frontend.md) | Structured frontend review checklist (styling, a11y, hooks, E2E) |
| **Clerk Auth Review** | [.claude/skills/kiat-clerk-auth-review.md](.claude/skills/kiat-clerk-auth-review.md) | Specialist for any auth-touching diff (Layer 3, hard trigger rule) |
| **Test Patterns Check** | [.claude/skills/kiat-test-patterns-check/SKILL.md](.claude/skills/kiat-test-patterns-check/SKILL.md) | Forced-response test pattern acknowledgment (Layer 6b, router + 9 selective blocks) |
| **UI/UX Search** | [.claude/skills/kiat-ui-ux-search/SKILL.md](.claude/skills/kiat-ui-ux-search/SKILL.md) | Search-on-demand wrapper for external [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (~85k tokens, queried via script) |

### Framework specs (not user-editable — Kiat machinery)

| Spec | File | Purpose |
|------|------|---------|
| **Available Skills** | [.claude/specs/available-skills.md](.claude/specs/available-skills.md) | Registry of contextual skills with "when to use" criteria, read by tech-spec-writer |
| **Context Budgets** | [.claude/specs/context-budgets.md](.claude/specs/context-budgets.md) | Per-agent token budgets (Layer 5) |
| **Metrics Events** | [.claude/specs/metrics-events.md](.claude/specs/metrics-events.md) | JSONL event log schema (rollup-first v1.1) |
| **Failure Patterns** | [.claude/specs/failure-patterns.md](.claude/specs/failure-patterns.md) | Reactive FP registry with recurrence counts |

### Framework tools

| Tool | File | Purpose |
|------|------|---------|
| **Health Report** | [.claude/tools/report.py](.claude/tools/report.py) | Weekly markdown report from `delivery/metrics/events.jsonl` |
| **Doc Audit** | [.claude/tools/doc-audit.py](.claude/tools/doc-audit.py) | Measures project docs against M1 (tokens) + M2 (structure ratio) |

Run with:
```bash
# Health report (after stories have run)
python3 kiat/.claude/tools/report.py
python3 kiat/.claude/tools/report.py --since 2026-04-01
python3 kiat/.claude/tools/report.py --epic epic-3
python3 kiat/.claude/tools/report.py --validate           # schema check the events file

# Doc audit (anytime — measure the health of delivery/specs/)
python3 kiat/.claude/tools/doc-audit.py
python3 kiat/.claude/tools/doc-audit.py --max-tokens 8000 --min-structure 0.6
python3 kiat/.claude/tools/doc-audit.py --strict          # exit 1 if any doc fails (CI-friendly)
```

### Framework docs (consumed by agents)

| Doc | File | Audience |
|-----|------|----------|
| **CLAUDE.md** | [CLAUDE.md](CLAUDE.md) | All agents — universal rules |
| **Docs README** | [.claude/README.md](.claude/README.md) | Framework doc index |

---

## 📋 Project (`delivery/`, `checklists/`, `patterns/` — user-editable per project)

### Project conventions (`delivery/specs/`)

These are **templates to customize per project**. Humans read them, agents reference them.

| Convention | File |
|------------|------|
| Architecture (Clean Arch) | [delivery/specs/architecture-clean.md](delivery/specs/architecture-clean.md) |
| Backend conventions | [delivery/specs/backend-conventions.md](delivery/specs/backend-conventions.md) |
| Service communication (DI) | [delivery/specs/service-communication.md](delivery/specs/service-communication.md) |
| Frontend architecture | [delivery/specs/frontend-architecture.md](delivery/specs/frontend-architecture.md) |
| Design system | [delivery/specs/design-system.md](delivery/specs/design-system.md) |
| API conventions | [delivery/specs/api-conventions.md](delivery/specs/api-conventions.md) |
| Database conventions | [delivery/specs/database-conventions.md](delivery/specs/database-conventions.md) |
| Security checklist | [delivery/specs/security-checklist.md](delivery/specs/security-checklist.md) |
| Clerk patterns | [delivery/specs/clerk-patterns.md](delivery/specs/clerk-patterns.md) |
| Testing (anti-flakiness + CI gate) | [delivery/specs/testing.md](delivery/specs/testing.md) |
| Git conventions (branches, commits, PR) | [delivery/specs/git-conventions.md](delivery/specs/git-conventions.md) |
| Deployment (env vars, production guards) | [delivery/specs/deployment.md](delivery/specs/deployment.md) |
| **Project Memory** (emergent patterns, cross-story coherence) | [delivery/specs/project-memory.md](delivery/specs/project-memory.md) |

### Epics & stories (`delivery/epic-X/`)

- **[delivery/README.md](delivery/README.md)** — How to structure epics, stories, reviews
- `delivery/epic-X/story-NN.md` — Story specs written by BMAD, consumed by Team Lead → coders

### Runtime data (`delivery/metrics/`)

- `delivery/metrics/events.jsonl` — Written by Team Lead at each phase transition. Read by `.claude/tools/report.py`. (Created when stories start running.)

### Project checklists

- [checklists/](checklists/) — "Am I done?" templates per role (user-editable)

### Project patterns

- [patterns/](patterns/) — Architectural patterns (context injection, skill orchestration, etc.) — user-editable

---

## 📁 Folder Structure

```
kiat/
├── README.md                          # Vision + enforcement model
├── INDEX.md                           # This file
├── GETTING_STARTED.md                 # Onboarding
├── structure.md                       # Architecture decisions
│
├── .claude/                           # ═══ IA / Kiat framework ONLY ═══
│   ├── agents/                        # 5 kiat-* agents
│   ├── skills/                        # 5 kiat-* skills
│   ├── specs/                         # 3 framework specs (context/metrics/patterns)
│   ├── tools/                         # report.py
│   └── docs/                          # CLAUDE.md + framework README
│
└── delivery/                          # ═══ Project-owned ONLY ═══
    ├── README.md                      # Delivery conventions
    ├── specs/                         # 10 project conventions (user-editable)
    ├── metrics/                       # events.jsonl (runtime data)
    └── epic-X/                        # Story specs (written by BMAD)

checklists/                            # User-editable templates
patterns/                              # User-editable templates
```

**The separation test:** `find kiat/.claude/` gives framework files only. `find kiat/delivery/` gives project files only. Neither contains the other.

---

## 🎯 Workflow at a Glance

```
User chat
    ↓
BMAD Master (métier) → writes delivery/epic-X/story-NN.md
    ↓
Team Lead (technique) — runs:
    Phase 0a: kiat-validate-spec  (ambiguity check)
    Phase 0b: pre-flight context budget (25k hard limit)
    ↓
Backend-Coder + Frontend-Coder (parallel)
    Step 0.5: kiat-test-patterns-check (forced acknowledgment)
    ↓
Backend-Reviewer + Frontend-Reviewer (parallel)
    Runs: kiat-review-backend / kiat-review-frontend
    Conditional: kiat-clerk-auth-review
    Outputs: VERDICT: APPROVED | NEEDS_DISCUSSION | BLOCKED
    ↓
Team Lead arbitrates per verdict
    45-min fix budget for BLOCKED retries
    Escalates NEEDS_DISCUSSION to BMAD/user
    Emits metrics events at every phase
    ↓
Story PASSED → Human merges
```

Each phase emits a JSONL event → `delivery/metrics/events.jsonl` → `report.py` generates weekly health reports.

---

## 🎓 Key Concepts

| Term | Meaning | Reference |
|------|---------|-----------|
| **6 Enforcement Layers** | Kiat's core design (verdicts, time budgets, specialist skills, audit lines, context budgets, pre-coding gates) | [README.md](README.md#️-enforcement-model-how-we-make-agents-actually-follow-rules) |
| **3-way verdict** | APPROVED / NEEDS_DISCUSSION / BLOCKED (Layer 1) | [.claude/agents/kiat-team-lead.md](.claude/agents/kiat-team-lead.md) Phase 4 |
| **45-min fix budget** | Wall-clock retry budget (Layer 2) | [.claude/agents/kiat-team-lead.md](.claude/agents/kiat-team-lead.md) Retry Budget |
| **Audit lines** | Mandatory traces of skill invocations (Layer 4) | agent definitions |
| **Context budget** | 25k token hard limit per coder (Layer 5) | [.claude/specs/context-budgets.md](.claude/specs/context-budgets.md) |
| **Pre-coding gates** | Spec validation + test patterns (Layer 6) | [.claude/skills/kiat-validate-spec.md](.claude/skills/kiat-validate-spec.md), [.claude/skills/kiat-test-patterns-check/SKILL.md](.claude/skills/kiat-test-patterns-check/SKILL.md) |
| **Failure pattern (FP-NNN)** | Reactive incident registry | [.claude/specs/failure-patterns.md](.claude/specs/failure-patterns.md) |
| **Metrics event** | JSONL log entry at phase transitions | [.claude/specs/metrics-events.md](.claude/specs/metrics-events.md) |
| **Project Memory** | Cross-story coherence (emergent patterns, shared components, architectural decisions) | [delivery/specs/project-memory.md](delivery/specs/project-memory.md) |

---

**Let's ship. 🚀**
