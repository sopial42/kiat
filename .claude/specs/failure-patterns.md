# Failure Patterns (FP) Registry

> **Why this exists:** Every time Kiat fails in a new way, we document it ONCE and reuse the documentation forever. This file is the index; each pattern is a separate file under `kiat/delivery/specs/failure-patterns/`. When a pattern recurs, we increment its count — if a pattern hits 3+ recurrences, that's a signal to change Kiat itself, not just document the failure.

**Principle:** This document is **reactive, not preemptive**. Never try to
enumerate failures before they happen. Wait for a real incident, then write
it up. Preemptive failure docs become stale noise; reactive ones stay load-bearing.

**Owner:** Team Lead writes new patterns at escalation time. Anyone can
increment recurrence counts.

---

## How to Use This Registry

### When a story escalates or fails

1. **Team Lead searches this registry** for a matching pattern.
2. **If match found:** apply the documented "Prevention" action (if any), increment the `Recurrence count` in the matching file, note the new story ID.
3. **If no match:** create a new pattern file using the template below. Number it `FP-NNN` (next available). Add it to the index below.
4. **Emit an `escalated` metrics event** with the `failure_pattern_id` field pointing to the FP-NNN.

### When you want a weekly health pulse

- Read the `kiat/.claude/tools/report.py` output — it lists recent escalations by FP-NNN.
- Scan this index for patterns with growing recurrence counts (≥3 is a signal to act).
- For any pattern at ≥3 recurrences with no "Prevention" action defined: **that's the backlog item**. Build the prevention.

---

## Registry Index

| ID | Title | Discovered | Recurrences | Prevention status |
|---|---|---|---|---|
| _(empty — no failures documented yet)_ | | | | |

*This registry will grow organically as Kiat runs real stories. Don't pre-populate it.*

---

## Pattern File Template

Create new patterns as `kiat/delivery/specs/failure-patterns/FP-NNN-short-slug.md`:

```markdown
# FP-NNN: [Short descriptive title]

**Discovered:** story-XX, YYYY-MM-DD
**Category:** [spec-ambiguity | test-flakiness | context-overflow | clerk-auth | infra | other]
**Recurrence count:** 1
**Prevention status:** [none | documented | skill-enforced | structural]

---

## Symptom

What the reviewer, coder, or CI actually saw. Be concrete — paste the error
message or verdict line. Future Team Lead will grep this field.

Example:
> Backend-reviewer returned `VERDICT: BLOCKED` on cycle 3 with "Handler leaks
> internal error string in 500 response". Fix budget exhausted at 52 min.

## Root cause

What actually broke. Go one level deeper than the symptom. If the symptom is
"RLS test failed", the root cause might be "migration ran but RLS policy was
not created because the SQL was in a comment block".

## Detection path

Which Kiat layer should have caught this earlier? (spec-validate,
preflight, kiat-test-patterns-check, reviewer checklist, kiat-clerk-auth-review, ...)
If no layer exists yet, note that.

## Fix applied (this instance)

What resolved this specific story. One or two lines.

## Prevention

Three possible values:

- **none** — watch for recurrence, don't act yet
- **documented** — added rule to an existing doc (testing.md, CLAUDE.md, etc.)
- **skill-enforced** — new rule added to an existing skill or a new skill created
- **structural** — Kiat framework itself changed (new phase, new budget, new agent rule)

Include a link to the change (commit, PR, file).

## Recurrence log

| Date | Story | Notes |
|---|---|---|
| YYYY-MM-DD | story-XX | Initial incident |
| YYYY-MM-DD | story-YY | Same symptom, different data |
```

---

## Rules for Growing This Registry

1. **One pattern per root cause, not per symptom.** If two stories hit the
   same root cause with slightly different symptoms, they're the SAME
   pattern — increment recurrence on the existing one.
2. **Patterns are small.** If a pattern file exceeds ~100 lines, you're
   probably writing a tutorial. Keep it to what Team Lead needs to match and act.
3. **Recurrence ≥ 3 triggers action.** When a pattern hits 3 recurrences:
   - If "Prevention" is "none" → STOP ignoring, escalate to user for structural fix
   - If "Prevention" is "documented" → promote to "skill-enforced" (docs aren't working)
   - If "Prevention" is "skill-enforced" and still recurring → promote to "structural"
4. **Don't retire patterns.** Even if a pattern is structurally fixed, keep
   the file — it's a historical record. Mark the file header with
   `Prevention status: structural (resolved YYYY-MM-DD)` instead of deleting.
5. **Team Lead, not coders, writes patterns.** Coders report symptoms;
   Team Lead decides if it's a new pattern or a recurrence. This keeps the
   registry consistent.

---

## Why Reactive Instead of Preemptive?

Preemptive failure docs have two failure modes:
- **Too generic**: "Handle all edge cases" — useless, not actionable
- **Too specific**: 200 listed pitfalls nobody reads, because 95% don't apply

Reactive docs have two properties preemptive docs don't:
- **Every entry was paid for** — someone lost time to it, so it's real
- **Recurrence counts surface priorities automatically** — the highest-count patterns are obviously the highest-priority fixes

The Kiat enforcement model (layers 1-5) already catches the common, well-understood failures. This registry exists to catch the **long tail** — the weird, infrequent ones that slip through. Build it slowly, trust the count.

---

## Related

- **Metrics events** ([`metrics-events.md`](metrics-events.md)) — every escalation can reference a `failure_pattern_id`, which lets reports correlate metrics with patterns.
- **Enforcement model** ([`../../README.md`](../../README.md)) — when a pattern is promoted to "structural", the fix usually lands as a new enforcement layer or a rule added to an existing skill.
