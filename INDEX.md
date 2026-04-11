# Kiat Starter Kit — Complete Index

Everything in Kiat, grouped by whether it's **framework IA** (`.claude/`) or **project-owned** (`delivery/`).

---

## 📖 Quick Start (Read These First)

1. **[README.md](README.md)** — Vision, two-layer story model, enforcement model (7 layers), monitoring
2. **[GETTING_STARTED.md](GETTING_STARTED.md)** — New-user onboarding (BMad bootstrap → first story → first run)
3. **[CLAUDE.md](CLAUDE.md)** — Universal meta-rules (ambient context)
4. **[delivery/business/README.md](delivery/business/README.md)** — Business layer folder contract + BMad writing protocol
5. **[delivery/epics/README.md](delivery/epics/README.md)** — Two-layer story model + BMad Plan-mode protocol

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
| **Validate Spec** | [.claude/skills/kiat-validate-spec/SKILL.md](.claude/skills/kiat-validate-spec/SKILL.md) | Pre-coding spec ambiguity detector (Layer 6a, used by tech-spec-writer + Team Lead) |
| **Review Backend** | [.claude/skills/kiat-review-backend/SKILL.md](.claude/skills/kiat-review-backend/SKILL.md) | Structured backend review (Clean Arch, security, Venom) — detailed checklist in `references/checklist.md` |
| **Review Frontend** | [.claude/skills/kiat-review-frontend/SKILL.md](.claude/skills/kiat-review-frontend/SKILL.md) | Structured frontend review (styling, a11y, hooks, E2E) — detailed checklist in `references/checklist.md` |
| **Clerk Auth Review** | [.claude/skills/kiat-clerk-auth-review/SKILL.md](.claude/skills/kiat-clerk-auth-review/SKILL.md) | Specialist for any auth-touching diff (Layer 3, hard trigger rule) |
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

## 📋 Project (`delivery/` — user-editable per project)

### Business layer (`delivery/business/` + `delivery/epics/`)

Business knowledge written by **BMad** (upstream product agent), governed by folder-level contracts:

| File | Role |
|---|---|
| [delivery/business/README.md](delivery/business/README.md) | Folder contract: BMad's 4 input modes, Capture decision tree, sizing discipline, boundaries |
| [delivery/epics/README.md](delivery/epics/README.md) | Two-layer story model + BMad's Plan-mode protocol (`## Business Context` boundary) + handoff to tech-spec-writer |
| delivery/business/{glossary,personas,business-rules,domain-model,user-journeys}.md | Evergreen domain knowledge, created on demand |
| delivery/epics/epic-template/ | Story + epic templates (both layers pre-scaffolded) |

### Project technical conventions (`delivery/specs/`)

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

### Epics & stories (`delivery/epics/epic-X/`)

- **[delivery/README.md](delivery/README.md)** — How to structure epics, stories, reviews
- `delivery/epics/epic-X/story-NN.md` — Story specs written by `kiat-tech-spec-writer`, consumed by Team Lead → coders

### Runtime data (`delivery/metrics/`)

- `delivery/metrics/events.jsonl` — Written by Team Lead at each phase transition. Read by `.claude/tools/report.py`. Created when stories start running; the `.jsonl` file itself is gitignored.

---

## 📁 Folder Structure

```
kiat/
├── CLAUDE.md                          # Ambient meta-rules (auto-loaded by Claude Code)
├── README.md                          # Vision + 7-layer enforcement model
├── INDEX.md                           # This file
├── GETTING_STARTED.md                 # Onboarding
│
├── .claude/                           # ═══ IA / Kiat framework ONLY ═══
│   ├── README.md                      # Framework doc index
│   ├── settings.json                  # Permissions + SubagentStop hook wiring (Layer 7)
│   ├── agents/                        # 6 kiat-* agent system prompts
│   ├── skills/                        # 6 kiat-* skills (folder-based)
│   ├── specs/                         # 4 framework specs (available-skills / context-budgets / metrics-events / failure-patterns)
│   └── tools/                         # report.py, doc-audit.py, hooks/
│
└── delivery/                          # ═══ Project-owned ONLY ═══
    ├── README.md                      # Delivery conventions
    ├── business/                      # BMAD-compatible business / domain docs
    ├── specs/                         # Project technical conventions (architecture, testing, design system, …)
    ├── epics/                         # epic-template/ + epic-N-name/story-NN.md
    └── metrics/                       # events.jsonl (runtime data, gitignored)
```

**The separation test:** `find kiat/.claude/` gives framework files only. `find kiat/delivery/` gives project files only. Neither contains the other.

---

## 🎯 Workflow at a Glance

Kiat stories are written by **two authors into the same file** — BMad owns the business layer, the tech-spec-writer owns the technical layer. See [`delivery/business/README.md`](delivery/business/README.md) and [`delivery/epics/README.md`](delivery/epics/README.md) for the folder-level contracts.

```
User: informal product thinking ("I want X", "users struggle with Y")
    ↓
BMad (external product agent, governed by folder contracts)
    • Capture mode → evergreen domain facts land in delivery/business/
    • Plan mode    → ## Business Context section of delivery/epics/epic-X/story-NN.md
    ↓
kiat-tech-spec-writer (enrichment mode — default when Business Context exists)
    • Reads ## Business Context intact, never rewrites it
    • Reads linked delivery/business/ + delivery/specs/ on demand
    • Appends Skills, Backend, Frontend, Database, Edge cases, Tests
    • Self-validates via kiat-validate-spec
    ↓
Team Lead — runs:
    Phase 0a: kiat-validate-spec  (ambiguity check on both layers)
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
    Escalates NEEDS_DISCUSSION to tech-spec-writer / BMad / user
    Emits rollup event at Phase 7
    ↓
Story PASSED → Human merges
```

**Fast path for pure technical work** (refactors, bug fixes): skip BMad, go straight to `kiat-tech-spec-writer` which runs in **greenfield mode** and produces both layers itself.

Each phase emits a JSONL event → `delivery/metrics/events.jsonl` → `report.py` generates weekly health reports.

---

## 🎓 Key Concepts

| Term | Meaning | Reference |
|------|---------|-----------|
| **Two-layer story model** | Every story file has a `## Business Context` (written by BMad, business language) and technical sections (written by `kiat-tech-spec-writer`, English). One file, two authors, two hard contracts. | [delivery/epics/README.md](delivery/epics/README.md) |
| **BMad's 4 input modes** | Explore / Capture / Plan / Review. Capture lands in `delivery/business/`, Plan lands in `## Business Context` of an epic or story. | [delivery/business/README.md](delivery/business/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad) |
| **Enrichment mode vs greenfield mode** | Tech-spec-writer detects whether a story already has a BMad-written `## Business Context`. If yes → enrichment mode (preserves it, appends tech). If no → greenfield (writes both layers). | [.claude/agents/kiat-tech-spec-writer.md](.claude/agents/kiat-tech-spec-writer.md) |
| **7 Enforcement Layers** | Kiat's core design (verdicts, time budgets, specialist skills, audit lines, context budgets, pre-coding gates, SubagentStop hooks) | [README.md](README.md#️-enforcement-model-how-we-make-agents-actually-follow-rules) |
| **3-way verdict** | APPROVED / NEEDS_DISCUSSION / BLOCKED (Layer 1) | [.claude/agents/kiat-team-lead.md](.claude/agents/kiat-team-lead.md) Phase 4 |
| **45-min fix budget** | Wall-clock retry budget (Layer 2) | [.claude/agents/kiat-team-lead.md](.claude/agents/kiat-team-lead.md) Retry Budget |
| **Audit lines** | Mandatory traces of skill invocations (Layer 4) | agent definitions |
| **Context budget** | 25k token hard limit per coder (Layer 5) | [.claude/specs/context-budgets.md](.claude/specs/context-budgets.md) |
| **Pre-coding gates** | Spec validation + test patterns (Layer 6) | [.claude/skills/kiat-validate-spec/SKILL.md](.claude/skills/kiat-validate-spec/SKILL.md), [.claude/skills/kiat-test-patterns-check/SKILL.md](.claude/skills/kiat-test-patterns-check/SKILL.md) |
| **Failure pattern (FP-NNN)** | Reactive incident registry | [.claude/specs/failure-patterns.md](.claude/specs/failure-patterns.md) |
| **Metrics event** | JSONL log entry at phase transitions | [.claude/specs/metrics-events.md](.claude/specs/metrics-events.md) |
| **Project Memory** | Cross-story technical coherence (emergent patterns, shared components, architectural decisions — project-owned, not BMad's territory) | [delivery/specs/project-memory.md](delivery/specs/project-memory.md) |

---

**Let's ship. 🚀**
