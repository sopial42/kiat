# Getting Started with Kiat

You have a complete agent-first SaaS starter kit. Here's how to get from zero to shipping.

---

## 📊 What You Have (Already Wired Up ✅)

### Framework (`.claude/` — Kiat IP, don't edit unless you're changing Kiat itself)

- ✅ **5 agents** with baked-in critical rules ([.claude/agents/](./.claude/agents/))
  - `kiat-team-lead` — orchestrator with 45-min fix budget, metrics emission
  - `kiat-backend-coder`, `kiat-frontend-coder` — with Step 0.5 test patterns self-check
  - `kiat-backend-reviewer`, `kiat-frontend-reviewer` — with 3-way verdicts
- ✅ **5 skills** enforcing quality gates ([.claude/skills/](./.claude/skills/))
  - `kiat-review-backend`, `kiat-review-frontend` — structured review checklists
  - `kiat-clerk-auth-review` — specialist for any auth-touching diff
  - `kiat-validate-spec` — pre-coding ambiguity detector
  - `kiat-test-patterns-check` — forced acknowledgment of testing rules
- ✅ **3 framework specs** ([.claude/specs/](./.claude/specs/))
  - `context-budgets.md` — per-agent 25k token hard limits
  - `metrics-events.md` — JSONL event log schema
  - `failure-patterns.md` — reactive FP registry
- ✅ **1 tool** ([.claude/tools/report.py](./.claude/tools/report.py)) — weekly health reports
- ✅ **CLAUDE.md** ([CLAUDE.md](./CLAUDE.md)) — universal coding rules

### Project templates (`delivery/`, `checklists/`, `patterns/` — edit these per project)

- ✅ 10 convention templates in [delivery/specs/](./delivery/specs/)
- ✅ Delivery conventions in [delivery/README.md](./delivery/README.md)
- ✅ Checklists and patterns (user-editable)

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

Review the 10 files in `delivery/specs/` and edit anything that doesn't fit your stack. The framework files in `.claude/` are generally **not touched** — they're Kiat machinery.

### Phase 2: Create Your First Epic (30 minutes)

```bash
mkdir delivery/epic-1-landing
# Write _epic.md with scope + objectives
# Write story-01-<slug>.md with acceptance criteria
```

### Phase 3: Run Your First Story

1. **You chat with BMAD Master** (BMAD is separate from Kiat — it's your product/metier agent). BMAD writes `delivery/epic-1-landing/story-01-<slug>.md`.

2. **Team Lead picks up the story** and runs:
   - **Phase 0a**: `kiat-validate-spec` — checks for ambiguity. If `NEEDS_CLARIFICATION`, bounces questions back to BMAD before any coder runs.
   - **Phase 0b**: pre-flight context budget check (25k hard limit). If overflow, escalates to BMAD with split request.

3. **Coders launch** in parallel (backend + frontend). Each runs `kiat-test-patterns-check` at Step 0.5 before writing any code.

4. **Reviewers review** with 3-way verdict:
   - `APPROVED` → proceed to story validation
   - `NEEDS_DISCUSSION` → Team Lead arbitrates or escalates (never bounced back to coder as "fix this")
   - `BLOCKED` → aggregated issues sent to coder; 45-min fix budget starts

5. **Team Lead emits metrics events** at every phase transition → `delivery/metrics/events.jsonl`.

6. **Story PASSED** → human merges.

### Phase 4: Monitor Health

After each story (or weekly):

```bash
python3 kiat/.claude/tools/report.py
python3 kiat/.claude/tools/report.py --epic epic-1
python3 kiat/.claude/tools/report.py --since 2026-04-01
```

Look for:
- **CLEAR rate < 70%** → BMAD specs too ambiguous
- **Overflow rate > 20%** → stories too big or budget too tight
- **`test_patterns_consistent: false`** → coders skimming test-patterns-check
- **Same failure pattern recurrence ≥ 3** → stop documenting, structurally fix

---

## 📋 Pre-Launch Checklist

- [ ] **Project specs customized** (the 10 files in `delivery/specs/`)
- [ ] **Framework untouched** (unless you're changing Kiat itself)
- [ ] **First epic planned** (`delivery/epic-1/_epic.md`)
- [ ] **First story written** (`delivery/epic-1/story-01.md`)
- [ ] **BMAD agent available** (not part of Kiat — bring your own)
- [ ] **Ready to run Team Lead on story 1**

---

## 💡 Key Principles

1. **Framework / project separation is strict.** `.claude/` is IA; `delivery/` is project. Don't mix. If you edit framework files to adapt to your project, you're doing it wrong — extract it to `delivery/` instead.
2. **Specs first.** A story never starts coding until `kiat-validate-spec` returns `CLEAR`.
3. **Batch feedback, not ping-pong.** Reviewers list all issues once; coders fix all in one pass.
4. **Time-budgeted retries, not cycle counts.** 45-minute wall-clock budget per story for fix cycles. Exhausted budget → escalate.
5. **Audit lines over trust.** Every skill invocation leaves a trace in agent output. Missing trace = protocol violation.
6. **Reactive failure patterns.** Don't pre-enumerate failures. Document incidents as they happen; recurrence ≥ 3 triggers structural fix.

---

## 🎓 Learning Path

Read in this order:

1. **[README.md](README.md)** — Vision + the 6 enforcement layers + monitoring
2. **[structure.md](structure.md)** — Why each decision
3. **[CLAUDE.md](CLAUDE.md)** — Universal coding rules
4. **[.claude/agents/kiat-team-lead.md](.claude/agents/kiat-team-lead.md)** — How orchestration actually works
5. **[.claude/skills/kiat-validate-spec/SKILL.md](.claude/skills/kiat-validate-spec/SKILL.md)** — How Phase 0 prevents bad specs from shipping
6. **[.claude/specs/failure-patterns.md](.claude/specs/failure-patterns.md)** — How to learn from real failures

---

## 🆘 Troubleshooting

**Q: "Team Lead keeps escalating on budget overflow"**
A: Your story specs are too large. Check `delivery/specs/` — if conventions are bloated, trim them. If the spec itself is oversized, split it.

**Q: "Reviewer keeps returning NEEDS_DISCUSSION"**
A: Your BMAD specs are ambiguous. Strengthen the pre-coding step — `kiat-validate-spec` should have caught it at Phase 0a.

**Q: "Context window exploding"**
A: The 25k budget is the hard gate. If you're bypassing it, you're circumventing Layer 5. Instead: split the story with BMAD.

**Q: "Same failure keeps happening"**
A: Check [.claude/specs/failure-patterns.md](.claude/specs/failure-patterns.md). If recurrence ≥ 3, stop documenting and structurally fix.

**Q: "Test is flaking in CI but passing locally"**
A: See [delivery/specs/testing.md](./delivery/specs/testing.md) — 26+ documented pitfalls with fixes.

**Q: "How do I know the system is working?"**
A: Run `python3 kiat/.claude/tools/report.py` weekly. You're looking for: no overflow spikes, CLEAR rate > 70%, no test-pattern drift, escalation reasons that match real blockers.

---

## 📞 When to Reach Out (To Humans)

**Escalate if:**
- Pre-flight budget check fails repeatedly → specs too large (ask BMAD to split)
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
- ✅ Complete framework with 6 enforcement layers
- ✅ Metrics + failure pattern tracking from day one
- ✅ 10 project convention templates
- ✅ Strict framework / project separation

**Next:** customize `delivery/specs/`, write your first epic, let Team Lead orchestrate.

Let's ship. 🚀
