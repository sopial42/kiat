# Getting Started with Kiat

You have a complete agent-first SaaS starter kit. Here's how to get from zero to shipping.

---

## 🧭 Why you start with BMad (not with code)

Kiat splits every story into **two layers** living in the same file:

| Layer | Who writes it | What it contains | Language |
|---|---|---|---|
| `## Business Context` (top of the file) | **BMad** (upstream product agent) | User story, personas, user-facing acceptance criteria, links to `delivery/business/`, business rationale | Project's business language (often French for FR-domain projects, English by default) |
| `## Skills` + technical sections (below) | **`kiat-tech-spec-writer`** (Kiat agent) | Contextual skills, API contracts, database schema, frontend components, edge cases, test scenarios | English (aligned with code + API conventions) |

**Why two layers instead of one?** The business layer and the technical layer have different authors, different cadences, and different audiences. The business layer is shaped by the product voice and rarely changes once stable; the technical layer is written just before a story ships and is often rewritten when the stack evolves. If you smear them together, every edit becomes a merge conflict between two people who shouldn't be merging. Splitting them gives each author a clean boundary and each reader a clean index.

**Why BMad first?** Because the business layer is the *input* for the technical layer. The tech-spec-writer's best output happens when it reads a BMad-written `## Business Context` (personas, user story, user-facing acceptance criteria, links to `delivery/business/` for terms and rules) and simply translates it into HTTP contracts, DB schemas, components, and tests. Skipping BMad works (greenfield mode) but puts more interpretation weight on the tech-spec-writer and on you.

**BMad is external to Kiat.** BMad is not a Kiat agent — it's any Claude session you configure to act as the product voice. What Kiat provides instead are **folder-level contracts** defining exactly what BMad is allowed to write where: evergreen facts in `delivery/business/`, `## Business Context` sections in `delivery/epics/`. Point your BMad session at [`delivery/business/README.md`](delivery/business/README.md) and [`delivery/epics/README.md`](delivery/epics/README.md) — those two READMEs are the full contract. No prompt engineering, no agent definition, just reading the folder rules.

**When you skip BMad.** For pure technical work (refactors, bug fixes, dependency updates, internal tooling, anything with no new business intent), skip BMad and go straight to `kiat-tech-spec-writer`. It works in **greenfield mode** and produces both layers itself from your informal request.

---

## 📊 What You Have (Already Wired Up ✅)

### Framework (`.claude/` — Kiat IP, don't edit unless you're changing Kiat itself)

- ✅ **6 agents** with baked-in critical rules ([.claude/agents/](./.claude/agents/))
  - `kiat-tech-spec-writer` — **default entry point**; translates informal requests into structured story files, decides contextual skills
  - `kiat-team-lead` — orchestrator with 45-min fix budget, metrics emission
  - `kiat-backend-coder`, `kiat-frontend-coder` — with Step 0.5 test patterns self-check
  - `kiat-backend-reviewer`, `kiat-frontend-reviewer` — with 3-way verdicts
- ✅ **6 skills** enforcing quality gates ([.claude/skills/](./.claude/skills/))
  - `kiat-validate-spec` — pre-coding ambiguity detector (Layer 6a)
  - `kiat-review-backend`, `kiat-review-frontend` — structured review checklists
  - `kiat-clerk-auth-review` — specialist for any auth-touching diff (Layer 3)
  - `kiat-test-patterns-check` — forced acknowledgment of testing rules (Layer 6b)
  - `kiat-ui-ux-search` — search-on-demand wrapper for external `ui-ux-pro-max` (~85k tokens, queried via script)
- ✅ **4 framework specs** ([.claude/specs/](./.claude/specs/))
  - `available-skills.md` — contextual skill registry (read by tech-spec-writer)
  - `context-budgets.md` — per-agent 25k token hard limits (Layer 5)
  - `metrics-events.md` — JSONL event log schema
  - `failure-patterns.md` — reactive FP registry
- ✅ **Tools** ([.claude/tools/](./.claude/tools/)) — `report.py`, `doc-audit.py`, SubagentStop hooks (Layer 7)
- ✅ **CLAUDE.md** ([CLAUDE.md](./CLAUDE.md)) — ambient meta-rules for any Claude instance in the project

### Project templates (`delivery/` — edit these per project)

- ✅ **Technical conventions** in [delivery/specs/](./delivery/specs/) (architecture, testing, design system, …) — human-owned, occasionally updated by the tech-spec-writer via `project-memory.md`
- ✅ **Business layer contract** in [delivery/business/README.md](./delivery/business/README.md) — the folder contract BMad reads. Defines the 4 input modes (Explore / Capture / Plan / Review), the Capture-mode decision tree (which of the 5 canonical files a fact lands in), sizing discipline, and the zones BMad never touches.
- ✅ **Two-layer story contract** in [delivery/epics/README.md](./delivery/epics/README.md) — defines the `## Business Context` section BMad writes in Plan mode and the technical sections the tech-spec-writer owns. Explicit boundary enforcement.
- ✅ **Epic + story templates** in [delivery/epics/epic-template/](./delivery/epics/epic-template/) — both layers pre-scaffolded with author attribution in HTML comments.
- ✅ **Delivery conventions** in [delivery/README.md](./delivery/README.md) — common commands + feedback-loop diagram with BMad wired in

---

## 🔨 What You Customize Per Project

The framework is done. What you edit for YOUR project:

### Tier 1 (Critical — Do First)

These templates have baseline content — review and adapt to your stack:

1. **[delivery/specs/backend-conventions.md](./delivery/specs/backend-conventions.md)** — project structure, naming, error codes
2. **[delivery/specs/frontend-architecture.md](./delivery/specs/frontend-architecture.md)** — React patterns, hooks, RSC boundary
3. **[delivery/specs/testing.md](./delivery/specs/testing.md)** — anti-flakiness rules (keep the 26+ pitfalls, add yours)
4. **[delivery/specs/design-system.md](./delivery/specs/design-system.md)** — colors, spacing, typography (from your Figma)

### Tier 2 (Convention Templates)

5. **[delivery/specs/api-conventions.md](./delivery/specs/api-conventions.md)** — REST design, error codes
6. **[delivery/specs/database-conventions.md](./delivery/specs/database-conventions.md)** — migrations, RLS templates
7. **[delivery/specs/security-checklist.md](./delivery/specs/security-checklist.md)** — OWASP, RLS testing
8. **[delivery/specs/clerk-patterns.md](./delivery/specs/clerk-patterns.md)** — if you use Clerk
9. **[delivery/specs/architecture-clean.md](./delivery/specs/architecture-clean.md)** — Clean Architecture walkthrough
10. **[delivery/specs/service-communication.md](./delivery/specs/service-communication.md)** — DI patterns

---

## 🚀 Launch Sequence

### Phase 1: Customize Project Specs (1-2 hours)

Review the files in `delivery/specs/` and edit anything that doesn't fit your stack. The framework files in `.claude/` are generally **not touched** — they're Kiat machinery.

### Phase 2: Bootstrap `delivery/business/` with BMad (30 minutes to ∞, evolves over time)

Open a Claude session in BMad mode — just tell it: *"You're acting as BMad. Read `delivery/business/README.md` and `delivery/epics/README.md` — those are your folder contracts. Don't write anything until you've read them."*

Then **Capture mode** — feed BMad a few facts about your project's domain and let it land them in the right file:

- First personas → `delivery/business/personas.md`
- First domain terms → `delivery/business/glossary.md` (with code-identifier mapping if bilingual)
- First compliance / invariant rules → `delivery/business/business-rules.md`
- Business-level entity model → `delivery/business/domain-model.md`
- End-to-end user journeys → `delivery/business/user-journeys.md`

Don't try to fill these files exhaustively before starting — create them on demand. Each file should stay under ~5k tokens so the tech-spec-writer can read it without drowning.

BMad's workflow rule: **propose before writing**. It will announce the exact file and section it intends to touch and wait for your green light (or `direct` to skip confirmation). Read [`delivery/business/README.md`](./delivery/business/README.md#bmad-writing-protocol-rules-for-claude-sessions-acting-as-bmad) for the full 4-mode contract.

### Phase 3: Create Your First Epic (5 minutes)

Still in BMad, **Plan mode**: *"on va construire X, prépare l'epic"* (or equivalent). BMad proposes an epic number + name, copies the template, and fills in only the `## Business Context` section of `_epic.md`.

```
delivery/epics/
└── epic-1-landing/
    └── _epic.md       ← BMad fills the ## Business Context;
                        rest stays templated for now
```

### Phase 4: Write Your First Story (10 minutes, two agents)

**Still in BMad, Plan mode**: *"prépare la première story"*. BMad creates `story-01-<slug>.md` from the template and fills in only the `## Business Context` section (user story, personas, user-facing acceptance criteria, links to `delivery/business/`, rationale). Technical sections remain empty with placeholder comments.

**Switch to `kiat-tech-spec-writer`** (or open a fresh session as that agent): *"write the technical spec for `delivery/epics/epic-1-landing/story-01-<slug>.md`"*. The writer:
1. Reads the pre-existing `## Business Context` (detects enrichment mode, preserves the section intact)
2. Reads any `delivery/business/` files linked from the Business Context
3. Reads the relevant `delivery/specs/` conventions for the layers in scope
4. Reads `delivery/specs/project-memory.md` for cross-story patterns
5. Asks clarifying questions if needed (≤ 2 rounds)
6. Appends `## Skills`, `## Acceptance Criteria (technical)`, `## Technical Specification` (Database / API / Frontend), `## Edge Cases`, `## Testing Plan`
7. Self-validates via `kiat-validate-spec`

Once the writer reports `SPEC_VERDICT: CLEAR`, the story is ready to execute.

### Phase 5: Run the Story

**Launch `kiat-team-lead`** on the story file (as the main session thread, not via `@agent-kiat-team-lead`, because sub-agents can't spawn sub-agents in Claude Code):

```bash
claude --agent kiat-team-lead
# then: "run delivery/epics/epic-1-landing/story-01-<slug>.md"
```

Team Lead runs:
- **Phase 0a** — re-runs `kiat-validate-spec` (defense in depth). If `NEEDS_CLARIFICATION`, bounces questions back to the tech-spec-writer (or to BMad, if the gap is in the Business Context) before any coder runs.
- **Phase 0b** — pre-flight context budget check (25k hard limit, reads the story's `## Skills` section to estimate total cost). If overflow, escalates to the tech-spec-writer with a split request.
- **Phase 1-2** — launches backend + frontend coders in parallel. Each runs `kiat-test-patterns-check` at Step 0.5 before writing any code. SubagentStop hooks (Layer 7) refuse the handoff if `TEST_PATTERNS: ACKNOWLEDGED` is missing.
- **Phase 3-4** — launches the reviewers with 3-way verdict (hook-enforced `VERDICT:` on line 1):
  - `APPROVED` → proceed to story validation
  - `NEEDS_DISCUSSION` → Team Lead arbitrates or escalates (never bounced back to coder as "fix this")
  - `BLOCKED` → aggregated issues sent to coder; 45-min fix budget starts
- **Phase 7** — emits one rollup event → `delivery/metrics/events.jsonl`.

**Story PASSED** → human merges.

### Fast path: pure technical work (skip Phases 2-4 BMad steps)

For refactors, bug fixes, or anything with no new business intent, skip BMad entirely. Go straight to `kiat-tech-spec-writer` with your informal request — it will operate in **greenfield mode** and write both layers itself (Business Context in your natural language, technical sections in English). Then Phase 5.

### Phase 6: Monitor Health

After each story (or weekly):

```bash
python3 kiat/.claude/tools/report.py
python3 kiat/.claude/tools/report.py --epic epic-1
python3 kiat/.claude/tools/report.py --since 2026-04-01
```

Look for:
- **CLEAR rate < 70%** → specs shipping with ambiguities. The gap is either in the `## Business Context` (BMad's capture discipline) or in the technical sections (tech-spec-writer's clarification loop). The `kiat-validate-spec` output tells you which layer.
- **Overflow rate > 20%** → stories too big or budget too tight
- **`test_patterns_consistent: false`** → coders skimming test-patterns-check
- **Same failure pattern recurrence ≥ 3** → stop documenting, structurally fix

---

## 📋 Pre-Launch Checklist

- [ ] **Project technical specs customized** (the files in `delivery/specs/`)
- [ ] **Framework untouched** (unless you're changing Kiat itself)
- [ ] **BMad session briefed** on [`delivery/business/README.md`](./delivery/business/README.md) + [`delivery/epics/README.md`](./delivery/epics/README.md)
- [ ] **At least one domain fact captured** in `delivery/business/` (even if it's just a persona or a glossary term)
- [ ] **First epic** drafted by BMad in `delivery/epics/epic-1/_epic.md` (`## Business Context` filled)
- [ ] **First story** drafted by BMad in `delivery/epics/epic-1/story-01.md` (`## Business Context` filled, technical sections empty)
- [ ] **First story enriched** by `kiat-tech-spec-writer` in enrichment mode (technical sections filled, `SPEC_VERDICT: CLEAR`)
- [ ] **Ready to run `kiat-team-lead` on story 1**

---

## 💡 Key Principles

1. **Two layers, two authors, one file.** Every story has a `## Business Context` (written by BMad) and technical sections (written by `kiat-tech-spec-writer`). Neither author writes in the other's territory, and the contract is enforced by the folder READMEs.
2. **Framework / project separation is strict.** `.claude/` is framework machinery; `delivery/` is project-owned. Don't mix. If you edit framework files to adapt to your project, you're doing it wrong — extract it to `delivery/` instead.
3. **Specs first.** A story never starts coding until `kiat-validate-spec` returns `CLEAR` on both layers.
4. **Batch feedback, not ping-pong.** Reviewers list all issues once; coders fix all in one pass.
5. **Time-budgeted retries, not cycle counts.** 45-minute wall-clock budget per story for fix cycles. Exhausted budget → escalate.
6. **Audit lines over trust.** Every skill invocation leaves a trace in agent output. Missing trace = protocol violation.
7. **Reactive failure patterns.** Don't pre-enumerate failures. Document incidents as they happen; recurrence ≥ 3 triggers structural fix.

---

## 🎓 Learning Path

Read in this order:

1. **[README.md](README.md)** — Vision + the 7 enforcement layers + monitoring + two-layer story model
2. **[CLAUDE.md](CLAUDE.md)** — Ambient meta-rules for any Claude instance in the project
3. **[delivery/business/README.md](delivery/business/README.md)** — Business layer folder contract + the BMad writing protocol (Capture mode, 5 canonical files, 4 input modes)
4. **[delivery/epics/README.md](delivery/epics/README.md)** — Two-layer story model + the BMad Plan-mode protocol (`## Business Context` boundary) + handoff to the tech-spec-writer
5. **[.claude/agents/kiat-tech-spec-writer.md](.claude/agents/kiat-tech-spec-writer.md)** — Enrichment mode + greenfield mode + self-validation protocol
6. **[.claude/agents/kiat-team-lead.md](.claude/agents/kiat-team-lead.md)** — How orchestration actually works
7. **[.claude/skills/kiat-validate-spec/SKILL.md](.claude/skills/kiat-validate-spec/SKILL.md)** — How Phase 0 prevents bad specs from shipping (both layers)
8. **[.claude/specs/failure-patterns.md](.claude/specs/failure-patterns.md)** — How to learn from real failures

---

## 🆘 Troubleshooting

**Q: "Team Lead keeps escalating on budget overflow"**
A: Your story specs are too large. Check `delivery/specs/` — if conventions are bloated, trim them. If the spec itself is oversized, ask `kiat-tech-spec-writer` to split it.

**Q: "Reviewer keeps returning NEEDS_DISCUSSION"**
A: Stories are shipping with ambiguities. Strengthen the pre-coding step — `kiat-validate-spec` (invoked by the tech-spec-writer at Step 6 and by Team Lead at Phase 0a) should have caught it earlier.

**Q: "Context window exploding"**
A: The 25k budget is the hard gate. If you're bypassing it, you're circumventing Layer 5. Instead: ask `kiat-tech-spec-writer` to split the story.

**Q: "Same failure keeps happening"**
A: Check [.claude/specs/failure-patterns.md](.claude/specs/failure-patterns.md). If recurrence ≥ 3, stop documenting and structurally fix.

**Q: "Test is flaking in CI but passing locally"**
A: See [delivery/specs/testing.md](./delivery/specs/testing.md) — 26+ documented pitfalls with fixes.

**Q: "How do I know the system is working?"**
A: Run `python3 kiat/.claude/tools/report.py` weekly. You're looking for: no overflow spikes, CLEAR rate > 70%, no test-pattern drift, escalation reasons that match real blockers.

---

## 📞 When to Reach Out (To Humans)

**Escalate if:**
- Pre-flight budget check fails repeatedly → specs too large (ask `kiat-tech-spec-writer` to split)
- Reviewer returns `NEEDS_DISCUSSION` with a design tradeoff → human UX call
- 45-min fix budget exhausted → story is harder than expected
- Same failure pattern hits recurrence ≥ 3 → Kiat itself needs a structural fix

**Don't escalate for:**
- Normal `BLOCKED` verdicts within the fix budget (that's the system working)
- Minor test flakes → fix via testing.md pitfalls list
- Context budget near limit but not exceeded → trim code references

---

## ✨ You're Ready

You have:
- ✅ Complete framework with 7 enforcement layers
- ✅ Two-layer story model (BMad business layer + tech-spec-writer technical layer)
- ✅ Metrics + failure pattern tracking from day one
- ✅ Project technical convention templates in `delivery/specs/`
- ✅ Business layer + epic/story folder contracts for BMad
- ✅ Strict framework / project separation

**Next:**
1. Customize `delivery/specs/` to your stack
2. Brief BMad on the two folder contracts (`delivery/business/README.md` + `delivery/epics/README.md`)
3. Capture your first domain facts with BMad → `delivery/business/`
4. Plan your first epic + story with BMad → `_epic.md` + `story-01.md` with `## Business Context` filled
5. Enrich the story with `kiat-tech-spec-writer` → technical sections appended
6. Run it with `kiat-team-lead`

Let's ship. 🚀
