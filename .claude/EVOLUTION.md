# Kiat Evolution Log

> **Purpose**: append-only journal of framework decisions. Every change to a Kiat protocol, agent, skill, or spec gets one entry here. Future agents (and humans) read this file to understand *why* the framework is the way it is — not just *what* it does.

---

## How to read this file

This file is **machine-parseable**. Each entry has a YAML frontmatter block followed by free-form markdown sections. The combination supports both automated analytics and human reading.

### File contract

1. **Append-only.** Never edit an existing entry retroactively. If a past decision changes, append a new entry with `type: reversal` that cites the old one in `superseded_by:`.
2. **IDs are stable and never reused.** Format: `EV-NNNN` (4-digit zero-padded).
3. **Two ID streams to avoid collision.**
   - `EV-0001` to `EV-0099` — forward-going decisions (changes made from 2026-05-16 onward, as they happen).
   - `EV-0100` to `EV-0199` — retroactive backfill (decisions made before the log existed, documented after the fact).
4. **Entries are sorted by ID ascending.** Newest entry goes at the bottom of its range. The retroactive block (EV-0100+) lives below the forward block.

### Entry schema

Every entry follows this exact structure:

````markdown
## EV-NNNN — <short-slug>

```yaml
id: EV-NNNN
date: YYYY-MM-DD
type: protocol_change | retirement | addition | calibration | observation | reversal
status: active | pending | superseded_by:EV-NNNN | reverted:YYYY-MM-DD
touches:
  - <path/to/file>:<optional-section-anchor>
triggered_by:
  - <kind>:<path-or-ref>
key_metrics:
  - "<verbatim metric string>"
decided_by: <agent or person>
```

### Context
1-3 sentences — what was observed that motivated this change.

### Decision
What changed, where, and how. Concrete.

### Alternatives rejected
- **A — <name>**: <reason in one line>
- **B — <name>**: <reason in one line>

### Re-evaluate if
- <condition that should trigger a re-examination, measurable when possible>
- <another condition>

### Links
- [Audit findings](relative/path)
- [Story or epic](relative/path)
- [Related EV-NNNN](#ev-nnnn)
````

### Field semantics

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Must equal the heading ID. Never reused. |
| `date` | ISO date | yes | The date the entry was written, not the date of the underlying change. |
| `type` | enum | yes | One of the six values listed above. |
| `status` | string | yes | `active` (in force), `pending` (entry exists but the corresponding change hasn't landed yet — typical for forward entries authored alongside a story spec), `superseded_by:EV-NNNN` (a later entry supersedes this one), `reverted:YYYY-MM-DD` (rolled back). |
| `touches` | list of paths | yes | Every file or doc section this decision modifies. Greppable: an agent editing file X can grep `touches:.*X` to find every decision that has touched X. |
| `triggered_by` | list of kind:path | yes | What artifact motivated the change. `audit:<path>`, `story:<path>`, `bug-report:<id>`, `user-request:<short-quote>`. Replayability anchor. |
| `key_metrics` | list of strings | yes | Verbatim chiffres or facts that motivated the decision. *Verbatim* means "copy-paste from the source artifact, do not paraphrase". A future agent uses these to test whether the decision still holds — e.g., if the metric was "0 escalations in 80 stories" and today it's "5 escalations in 200 stories", the decision deserves re-examination. |
| `decided_by` | string | yes | The agent or person that took the call. `kiat-team-lead + Boss` is typical when interactive. |

### What this file is NOT

- **Not a changelog.** A changelog logs *what changed*; this log captures *why*, with replayable chiffres.
- **Not a design doc.** Design docs explain how the system should work; this log records why each design choice was made.
- **Not a retrospective.** Retrospectives synthesize over a period; this log records single discrete decisions.
- **Not a tutorial.** New contributors should read `README.md`, `INDEX.md`, and the agent files. This log is for understanding non-obvious choices after the basics are clear.

### Discoverability

This file is referenced from:
- `CLAUDE.md` (project ambient context) — under "Where to Find Framework Rules"
- `.claude/agents/kiat-team-lead.md` (under protocol header)
- `.claude/agents/kiat-tech-spec-writer.md` (under protocol header)
- `.claude/agents/kiat-backend-coder.md` (under protocol header)
- `.claude/agents/kiat-frontend-coder.md` (under protocol header)

When you make a protocol change, you MUST append an entry here. The agent files remind you to do so.

---

## Forward entries (EV-0001..EV-0099)

> Decisions made from 2026-05-16 onward. Each entry is paired with a story in `delivery/epics/` that implements the change. Entries authored at spec time carry `status: pending` and are flipped to `status: active` by the corresponding story at its Phase 5c.

---

## EV-0001 — Officialize the producer-pays gate

```yaml
id: EV-0001
date: 2026-05-16
type: addition
status: active
touches:
  - .claude/specs/reconciliation-protocol.md
  - .claude/agents/kiat-team-lead.md:phase-5c
triggered_by:
  - audit:delivery/_audit/axis-B-failure-patterns.md
  - audit:delivery/_audit/SYNTHESE-kiat-runtime-audit-2026-05-16.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-01-officialize-producer-pays-gate.md
key_metrics:
  - "'producer-pays' appears in 15/44 reconcile_complete notes (34%) over 2026-04-27..2026-05-14"
  - "0 reconciliation-protocol.md mention of the gate as of 2026-05-16"
decided_by: kiat-team-lead + Boss
```

### Context
The "producer-pays gate" — coders auto-resolving their own L1 deviations at handoff time before `/bmad-correct-course` — is used 34 % of the time but documented nowhere. New contributors reading `reconciliation-protocol.md` would either over-route deviations to humans (workload overload) or under-route them (risk of sneaking-past).

### Decision
Add an explicit `## Resolution-at-handoff (the "producer-pays gate")` section to `reconciliation-protocol.md` documenting (a) when a coder may set `Status: RESOLVED` inline, (b) the allowed L1 categories, (c) the FORBIDDEN categories (RLS, auth, business rules, schema, cross-cutting files, upstream API contracts). Cross-reference from `kiat-team-lead.md` Phase 5c.

### Alternatives rejected
- **A — Leave it implicit**: rejected because invisible to new contributors and to a future bootstrap.
- **B — Forbid the pattern, route everything through `/bmad-correct-course`**: rejected because would overwhelm human triage; the pattern is healthy and load-bearing.

### Re-evaluate if
- Any reviewer cycle is BLOCKED with reason "L1 auto-resolve that should have been L2" — means the FORBIDDEN list is incomplete.
- The pattern frequency drops below 10 % of reconcile notes over a 30-day window — means coders are over-routing to humans, the documentation is too strict.

### Links
- <!-- [Audit axis B](../delivery/_audit/axis-B-failure-patterns.md) -->
- <!-- [Story 01](../delivery/epics/epic-16-kiat-framework-improvements/story-01-officialize-producer-pays-gate.md) -->

---

## EV-0002 — Phase 0c supersession (explicit declaration)

```yaml
id: EV-0002
date: 2026-05-16
type: protocol_change
status: active
touches:
  - .claude/agents/kiat-team-lead.md:phase-0c
  - .claude/agents/kiat-tech-spec-writer.md
  - .claude/specs/metrics-events.md
  - .claude/skills/kiat-validate-spec/
triggered_by:
  - audit:delivery/_audit/axis-D-queue-health.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-02-phase-0c-supersession-declaration.md
key_metrics:
  - "Phase 0c false-positive rate: 3/4 (75%) over 2026-05-01..2026-05-02"
  - "Genuine conflicts in same period: 1/4 (Q-057 Trivy/deploy.yml)"
decided_by: kiat-team-lead + Boss
```

### Context
Phase 0c auto-promoted 4 Q-IDs to L3 (`epic_block`) in 3 weeks. Three of them (Q-056, Q-058, Q-061) were supersessions — the new story explicitly resolved the open Q-ID, not conflicted with it. Phase 0c blocked all four equally, requiring unnecessary human signoff on the 3 false positives.

### Decision
Require tech-spec-writer to declare `## Supersedes: Q-XXX, Q-YYY` near the top of a story when applicable. Phase 0c reads that field — if the overlapping Q-ID is declared as superseded, mark it `[SUPERSEDED]` and emit a new `queue_supersede` event (not `epic_block`). Otherwise proceed with the existing auto-promotion path.

### Alternatives rejected
- **A — Heuristic auto-detection** (compare Q-ID tag to story AC list, guess supersession): rejected because false negatives are asymmetrically bad — missing a real conflict is worse than asking for one extra human signoff.
- **B — Status quo (block all overlaps)**: rejected, 75 % FP rate is unacceptable.

### Re-evaluate if
- Any `queue_supersede` event is later reverted by a human — means the writer's declaration was wrong.
- A story declares `## Supersedes: Q-XXX` but actually conflicts with Q-XXX scope — silent corruption risk.

### Links
- <!-- [Audit axis D §5](../delivery/_audit/axis-D-queue-health.md) -->
- <!-- [Story 02](../delivery/epics/epic-16-kiat-framework-improvements/story-02-phase-0c-supersession-declaration.md) -->

---

## EV-0003 — Retire `fix_budget=45min`

```yaml
id: EV-0003
date: 2026-05-16
type: retirement
status: active
touches:
  - .claude/agents/kiat-team-lead.md:phase-3
  - .claude/agents/kiat-team-lead.md:phase-4
  - .claude/specs/metrics-events.md
  - .claude/tools/report.py
triggered_by:
  - audit:delivery/_audit/axis-A-quantitative.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-03-retire-fix-budget-45min.md
key_metrics:
  - "fix_budget_used_min: max=35, p90=35, escalations=0 over 80 stories (2026-04-27..2026-05-14)"
  - "Stories that touched the 45-min threshold: 0/80"
  - "Stories that started the fix-budget clock: 16/80"
decided_by: kiat-team-lead + Boss
```

### Context
The 45-min fix-budget gate has fired zero times in 80 stories. Maximum observed: 35 min, p90: 35 min. The gate is decorative — it provides no signal — while occupying protocol space and creating an illusion of an escalation path that has never been used.

### Decision
Remove the 45-min threshold and the associated escalation logic from `kiat-team-lead.md` Phase 3 and Phase 4. Remove the "Fix budget: ~N min / 45 min limit" prefix from retry prompts. Keep the `fix_budget_used_min` field in rollup events as a retrospective metric (still useful for retro analysis), but it's no longer a trigger. Escalation now relies only on qualitative signals (spec ambiguity, security issue, ≥ 3 BLOCKED cycles).

### Alternatives rejected
- **A — Lower threshold to 30 min**: rejected because creates an incentive for Team Lead to underestimate fix duration; moves the problem rather than solving it.
- **B — Keep 45 min indefinitely**: rejected because decorative for 3+ weeks of operation; adds noise to prompts for no gain.

### Re-evaluate if
- Any rollup event shows `fix_budget_used_min >= 45` in the new v2 schema (post-EV-0005) — means the underlying phenomenon exists, the gate could matter.
- A story escalates for time-related reasons even without the gate — means the gate's logic was load-bearing in ways we didn't see.
- The team explicitly asks for re-introduction.

### Links
- <!-- [Audit axis A §3](../delivery/_audit/axis-A-quantitative.md) -->
- <!-- [Story 03](../delivery/epics/epic-16-kiat-framework-improvements/story-03-retire-fix-budget-45min.md) -->

---

## EV-0004 — Extend Phase -1 prompt-hygiene (5 new categories)

```yaml
id: EV-0004
date: 2026-05-16
type: addition
status: active
touches:
  - .claude/agents/kiat-team-lead.md:phase-minus-1
triggered_by:
  - audit:delivery/_audit/axis-C-business-deviations.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-04-extend-phase-minus1-prompt-hygiene.md
key_metrics:
  - "SIGNINASUSERA_HELPER_NONEXISTENT recurrence: 3 stories (epic-09 A/B/C) + 1 (epic-11) = 4 incidents"
  - "TOKEN_SUBSTITUTION_NEW_PILLS + SPEC_PROSE_DEPT_COUNT_MISMATCH: 3 incidents in 2 stories (BE+FE mirror)"
  - "SENTRY-SDK-V8-NO-ROUTER-TRANSITION-OR-LOGS: 1 incident, full AC rewrite cost"
  - "OpenSanctions topic-buckets misunderstanding: 13 deviations in 1 story"
  - "SPEC_PROSE_DEPT_COUNT_MISMATCH: 99 vs 107 INSEE codes — 2 mirrors in 1 story"
decided_by: kiat-team-lead + Boss
```

### Context
Five categories of tech-spec-writer hallucinations or stale assertions recur across the audit: phantom test helpers, non-existent CSS tokens, outdated library versions, misunderstood upstream API shapes, and made-up counter values (region/department counts, etc.). The existing Phase -1 prompt-hygiene rule covers CI / runtime / env vars but not these.

### Decision
Add 5 new rows to the `Fact you want to assert / Source of truth (verify BEFORE asserting)` table in Phase -1: test helpers (grep frontend/e2e/, backend/venom/), CSS tokens (grep globals.css), lib versions (package.json/go.mod), upstream API shape (sample JSON requirement), counter values (wc -l/grep -c on canonical source). Each row has a 1-paragraph rationale citing the audit incidents.

### Alternatives rejected
- **A — Add automation (hooks that grep these things)**: deferred — start with documentation, automate later if violations persist.
- **B — Cover everything (exhaustive 30-row table)**: rejected — would lose load-bearing focus; 13 rows total is the sweet spot.

### Re-evaluate if
- Any of the 5 new categories produces 3+ recurrences in the next 60 days — means the rule is read but not followed; escalate to a hook.

### Links
- <!-- [Audit axis C](../delivery/_audit/axis-C-business-deviations.md) -->
- <!-- [Story 04](../delivery/epics/epic-16-kiat-framework-improvements/story-04-extend-phase-minus1-prompt-hygiene.md) -->

---

## EV-0005 — events.jsonl v2 schema (archive + restart)

```yaml
id: EV-0005
date: 2026-05-16
type: protocol_change
status: active
touches:
  - delivery/metrics/events.jsonl
  - .claude/specs/metrics-events.md
  - .claude/tools/report.py
  - .claude/agents/kiat-team-lead.md:phase-6
  - .claude/agents/kiat-tech-spec-writer.md:spec-handoff-block
triggered_by:
  - audit:delivery/_audit/axis-A-quantitative.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-05-archive-events-and-clean-schema.md
key_metrics:
  - "business_deviations: 22/80 stories (28%) used object form, 58/80 used int form — silent coercion in report.py"
  - "mode field: 7 distinct values observed in the wild, no documented enum"
  - "spec block missing in 48/80 rollups (60%) — pre-v1.1 stories"
  - "clarification_rounds: 0 across 27/27 stories that have the field — root cause Branch A: SPEC_HANDOFF block never included clarification_rounds, so Team Lead always defaulted to 0; fixed by adding clarification_rounds field to SPEC_HANDOFF in kiat-tech-spec-writer.md"
decided_by: kiat-team-lead + Boss
```

### Context
The current `events.jsonl` has accumulated three schema drifts in 3 weeks: `business_deviations` exists as both `int` and `{count, backend[], frontend[]}` object across stories; the `mode` field has 7 different values without a documented enum; the `spec` block is missing in 60 % of rollups. `report.py` silently compensates, making analytics partially fictional.

### Decision
1. Move `delivery/metrics/events.jsonl` to `events.archive-2026-05-16.jsonl` (read-only by convention).
2. Define a canonical v2 schema in `metrics-events.md`: `business_deviations` always object, `mode` enum-restricted to `{normal, solo, team_lead_authored}` with `solo_track: A|B` when applicable, `spec` block required on every rollup.
3. Add new field `deviations_declared_explicitly: bool` to distinguish "zero deviations because perfect" from "zero deviations because not declared".
4. Update `report.py` to drop legacy coercion code, normalize archive events at load when scoped to all-time.
5. Investigate the `clarification_rounds: 0` pattern as part of this story (fix or document the cause).

### Alternatives rejected
- **A — Incremental migration of the 22 drift events**: rejected because the user explicitly chose "archiver et recommencer" — cleaner, the team has many stories incoming, the cut cost is acceptable.
- **B — Keep dual-schema support indefinitely**: rejected because `report.py` complexity grows; observability quality degrades.

### Re-evaluate if
- Any v2 event is rejected by the hook for schema reasons — schema is too rigid or hook regex is wrong.
- The 0-clarification-rounds pattern persists with the AC-T06 fix applied — means the writer is genuinely too aggressive at filling gaps, separate story needed.
- A second drift accumulates in v2 within 60 days — means the schema discipline isn't being enforced.

### Links
- <!-- [Audit axis A §2](../delivery/_audit/axis-A-quantitative.md) -->
- <!-- [Story 05](../delivery/epics/epic-16-kiat-framework-improvements/story-05-archive-events-and-clean-schema.md) -->

---

## EV-0006 — FP registry revival

```yaml
id: EV-0006
date: 2026-05-16
type: protocol_change
status: active
touches:
  - .claude/specs/failure-patterns.md
  - .claude/tools/report.py
triggered_by:
  - audit:delivery/_audit/axis-B-failure-patterns.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-06-fp-registry-revival.md
key_metrics:
  - "0 failure_pattern_id references in 80 rollups"
  - "5 FPs frozen at recurrence=1 since creation date 2026-04-27"
  - "2 stories spontaneously invented non-canonical IDs (PROCESS_*_NEW) instead of using the registry"
  - "3+ shadow patterns identified in audit (signInAsUserA, RLS L1, token drift) never promoted"
decided_by: kiat-team-lead + Boss
```

### Context
The FP registry was designed to be populated at escalation time. Zero escalations in 80 stories means zero entries created in 3 weeks. The registry is alive in form but dead in substance — Team Leads either bypass it (invent IDs like `PROCESS_*_NEW`) or don't engage with it at all.

### Decision
Expand the trigger conditions for FP creation beyond `outcome=escalated`:
- **Trigger B** (NEW): rollup shows `fix_budget_used_min >= 30` AND the cause is novel.
- **Trigger C** (NEW): same `**Tag**` prefix appears across ≥ 3 distinct stories within a 30-day window.
- **Trigger D** (NEW): manual identification during epic retro, runtime audit, or via `report.py` candidate detection.

Add a `## FP Candidates (passive detection)` section to `report.py` that automatically scans for Trigger C using only `SPEC_*` and `PROCESS_*` tag prefixes (to avoid noise from `AC-T*`, `DECISION`, `BOY_*`). The new section surfaces candidates without auto-creating files.

Format of FP entries stays unchanged (10+ lines) — the issue was the trigger, not the format.

### Alternatives rejected
- **A — Shorten FP format to 5 lines**: rejected (user feedback) — the 10-line format is already concise; the friction is creating files at all, not their length.
- **B — Auto-create FP files from Trigger C**: rejected — would balloon the registry with false positives; let humans/agents review candidates first.
- **C — Loosen trigger to ANY tag with ≥ 3 recurrences**: rejected — `AC-T01`, `DECISION` recur trivially and would noise the candidates list.

### Re-evaluate if
- The new triggers produce 0 new FPs in 60 days — triggers still too narrow OR no patterns recur at scale.
- The new triggers produce >5 new FPs/month — triggers too loose, registry will balloon.

### Links
- <!-- [Audit axis B](../delivery/_audit/axis-B-failure-patterns.md) -->
- <!-- [Story 06](../delivery/epics/epic-16-kiat-framework-improvements/story-06-fp-registry-revival.md) -->

---

## EV-0007 — Retire Phase 7 (prod_validation)

```yaml
id: EV-0007
date: 2026-05-16
type: retirement
status: active
touches:
  - .claude/agents/kiat-team-lead.md:phase-7
  - .claude/specs/metrics-events.md
  - .claude/tools/report.py
triggered_by:
  - audit:delivery/_audit/axis-A-quantitative.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-07-retire-phase-7.md
key_metrics:
  - "prod_validation across 80 rollups: 67 deferred (84%), 12 null (15%), 1 partial (1%), 0 confirmed_true (0%), 0 confirmed_false (0%)"
decided_by: kiat-team-lead + Boss
```

### Context
Phase 7 (post-Done prod validation) was designed as a best-effort agent-driven smoke test against prod after each deploy. In 3 weeks it was deferred 84 % of the time and never confirmed a fix. The phase occupies ~80 lines of the Team Lead protocol while providing zero signal — it has become a fantôme phase.

### Decision
Remove Phase 7 entirely from `kiat-team-lead.md`. Remove the `prod_validation` field from the v2 event schema. Add a short paragraph at the top of `kiat-team-lead.md` stating explicitly: **prod validation is OUT of the Team Lead protocol — Team Lead stops at Phase 6, prod-side verification is performed by the user manually post-merge**.

Legacy archive events keep their `prod_validation` field untouched.

### Alternatives rejected
- **A — Activate Phase 7 (mandatory smoke after each deploy)**: rejected — would generate ~5 notifications/day Boss would ignore, same outcome.
- **B — Leave as optional**: rejected — "optional" became "never" in practice, the zone grise is toxic for protocol discipline.

### Re-evaluate if
- The user reports ≥ 2 prod regressions per month that a Phase-7 smoke would have caught.
- Cloud Run deploys gain a programmatic post-deploy gate (Sentry release health, etc.) that an agent could plug into without requiring Boss interactivity.

### Links
- <!-- [Audit axis A §6/F6](../delivery/_audit/axis-A-quantitative.md) -->
- <!-- [Story 07](../delivery/epics/epic-16-kiat-framework-improvements/story-07-retire-phase-7.md) -->

---

## EV-0008 — Tag enum restriction (8 values + free suffix)

```yaml
id: EV-0008
date: 2026-05-16
type: protocol_change
status: active
touches:
  - .claude/specs/reconciliation-protocol.md
  - .claude/tools/hooks/check-post-delivery-schema.sh
  - .claude/agents/kiat-team-lead.md:phase-5c
  - .claude/agents/kiat-backend-coder.md
  - .claude/agents/kiat-frontend-coder.md
  - .claude/tools/report.py
triggered_by:
  - audit:delivery/_audit/axis-C-business-deviations.md
  - story:delivery/epics/epic-16-kiat-framework-improvements/story-08-tag-enum-restriction.md
key_metrics:
  - "363 deviation bullets in 67 .reconcile.md files"
  - "122 distinct first-segment tag prefixes used in practice"
  - "Canonical prefixes (SPEC_GAP, SCOPE_CUT, DOMAIN_NEW, PROCESS_*, SCHEMA_DRIFT) cover only 2% of bullets"
  - "Top free-form prefixes: DECISION (33%), AC-T## (20%), SPEC_* (14%)"
decided_by: kiat-team-lead + Boss
```

### Context
Tag prefixes are free-form today, which makes cross-story analytics impossible. The 8 canonical values defined by reconciliation-protocol cover 2 % of actual usage; the remaining 98 % invent ad-hoc prefixes. No agent can answer "how many SPEC_GAP across the project" without manual reclassification.

### Decision
Restrict `**Tag**:` to an 8-value enum: `SPEC_GAP | DECISION | SCOPE_CUT | BOY_SCOUT | DOMAIN_NEW | PROCESS | TEST_DRIFT | UPSTREAM_MISMATCH`. Allow free-form UPPER_SNAKE_CASE suffix after the first `_` (e.g., `SPEC_GAP_DEPT_COUNT_MISMATCH`). Update `check-post-delivery-schema.sh` to validate the prefix; reject `.reconcile.md` files with invalid prefixes.

Historical files are NOT migrated — the hook only runs on `SubagentStop`, which means new files only. Old `.reconcile.md` files keep their free-form tags.

The 8 prefixes were chosen empirically from the audit's top-of-distribution, not invented theoretically.

### Alternatives rejected
- **A — Keep free-form**: rejected — analytics impossible at scale; the cost of restricting is small, the benefit grows over time.
- **B — Full enum of 30+ values**: rejected — too rigid, just moves the problem to "which of the 30 fits", and inflates protocol surface.

### Re-evaluate if
- A category recurs ≥ 5 times across distinct stories that doesn't fit any of the 8 prefixes — means we need a 9th.
- The hook rejects > 10 % of new files for prefix violations — enum too restrictive OR coders don't know it.

### Links
- <!-- [Audit axis C §2](../delivery/_audit/axis-C-business-deviations.md) -->
- <!-- [Story 08](../delivery/epics/epic-16-kiat-framework-improvements/story-08-tag-enum-restriction.md) -->

---

## EV-0009 — Bridge BMad architecture into `project-memory.md`

```yaml
id: EV-0009
date: 2026-05-17
type: addition
status: active
touches:
  - .claude/skills/kiat-seed-project-memory/SKILL.md
  - .claude/skills/bmad-create-architecture/steps/step-08-complete.md
  - .claude/specs/available-skills.md
  - CLAUDE.md:bmad-role-section
  - delivery/specs/project-memory.md:entry-template
  - delivery/specs/project-memory.md:cap-and-promotion-mechanics
triggered_by:
  - pilot:nova-notariat/lgt (greenfield project using BMad + Kiat)
  - gap:cross-story technical decisions in _bmad-output/planning-artifacts/architecture.md never reach Kiat agents
key_metrics:
  - "LGT pilot architecture.md: 838 lines, ~15 cross-story technical decisions identified for seeding"
  - "project-memory.md template default size: 65 lines (empty of project content)"
  - "Adversarial review: 4 agents (architect / tech-writer / cynical / dev), unanimous rejection of distributed-overrides design (Proposal B)"
decided_by: claude-sonnet-4-6 + Boss
```

### Context
Greenfield projects using both BMad (product/architecture planning) and Kiat (implementation pipeline) hit a structural handoff gap. BMad produces a comprehensive `architecture.md` at `_bmad-output/planning-artifacts/`, full of cross-story technical decisions (calc engine choice, data regime separation, auth posture at M1, integration adapters, canonical endpoint names). But Kiat agents — `kiat-tech-spec-writer`, `kiat-backend-coder`, `kiat-frontend-coder` — never read `_bmad-output/`. Without a deliberate bridge: coders rediscover decisions story by story (badly), implementations drift, `/bmad-correct-course` is invoked repeatedly to mop up cross-story inconsistencies. The framework's "BMad never writes to `delivery/specs/`" rule (CLAUDE.md §40-42) is sound but leaves the gap unaddressed — closing it requires a human-invoked bridge, not a relaxation of the rule.

### Decision
Introduce a human-invoked skill `kiat-seed-project-memory` that extracts cross-story technical decisions from a BMad architecture document and proposes **structured entries** (`PM-NNN` stable IDs, `Status`, `Touches:` topic index, `Canonical ref`, `Rationale`, `Deviations allowed when`) for `delivery/specs/project-memory.md`. The skill defaults to dry-run; writing requires explicit `--apply` confirmation. The human writes — BMad does not — so the existing "BMad never writes to `delivery/specs/`" rule stands.

Update `project-memory.md` template (`delivery/specs/project-memory.md`) with:
- Structured entry schema (PM-NNN IDs, Status, Touches, etc.)
- Hard cap of **25 single-topic entries OR 400 lines** as forcing function
- Promotion mechanics: when cap is hit, single-topic clusters (≥3 entries sharing one `Touches:` topic) move to **new project-owned `delivery/specs/<topic>.md` files** (never edits to framework-owned files)
- Cross-topic entries (`Touches:` lists ≥2 topics) are exempt from the cap and stay in `project-memory.md` indefinitely — splitting them would fragment the rule

Update `CLAUDE.md` BMad section with a paragraph documenting the bridge. Update `bmad-create-architecture/steps/step-08-complete.md` to suggest running the bridge after architecture completes (Kiat-conditional, detected by presence of `delivery/specs/project-memory.md`). Register the skill in `.claude/specs/available-skills.md`.

### Alternatives rejected
- **A — Distributed overrides into framework-owned files** (`## Project-specific overrides` section appended to `backend-conventions.md`, `clerk-patterns.md`, etc.): rejected unanimously by 4 adversarial reviewers. Concrete reasons: (a) **merge hell** when upstream Kiat pushes a new version of a framework file with reorganized sections, (b) **routing ambiguity** — a decision like "PDF stream-and-forget" has 2+ plausible homes (`backend-conventions.md` / `database-conventions.md` / `deployment.md` / a new `pdf-generation.md`); search cost becomes N× instead of 1×, (c) **cross-topic decisions silently fragment** — "three-regime RLS data isolation" touches database + auth + security, whichever file you write it in, the other two coders miss it, (d) **tech-spec-writer routing table doubles** — every "load `backend-conventions.md`" becomes "load `backend-conventions.md` AND `backend-conventions.project.md` if exists".
- **B — Sibling `.project.md` files** (e.g., `backend-conventions.project.md` next to the framework file): rejected — recreates the same routing complexity as A. Requires conditional loading by the tech-spec-writer on every story.
- **C — Status quo (no bridge)**: rejected — leaves the gap that motivated this entry. Boss observed in the LGT pilot that without a bridge, the coders needed `project-memory.md` seeding before story 1 to avoid wasting cycles on architectural rediscovery.
- **D — Autonomous BMad seeding directly into `delivery/specs/`**: rejected — violates the "BMad never writes to `delivery/specs/`" rule and removes the human-in-the-loop check that catches mis-extractions (the dry-run + `--apply` flow).
- **E — Skill writes directly to `delivery/specs/` on every invocation without dry-run**: rejected — Cynical Reviewer flagged this as a loophole; any autonomous BMad session could run the skill end-to-end and bypass the human. The dry-run default closes the loophole.

### Re-evaluate if
- After 10 shipped stories on a pilot project, the load-rate of `project-memory.md` by `kiat-tech-spec-writer` is **<30 % per story** (instrument it via the agent's read events) — means the file is dead weight and the one-file design needs reconsideration. **This is the empirical validation criterion from the Cynical Reviewer; it must be answered with data, not debate.**
- The load-rate is ≥50 % — means the design is validated; consider documenting it as a Kiat default for greenfield projects.
- A single-topic cluster of ≥3 entries forms before the cap is reached on any project — means the cap threshold (25/400) is too lax; tighten it.
- A merge conflict on `project-memory.md` recurs across ≥3 PRs within a 30-day window on the same project — means the file is becoming a coordination hotspot; promotion to topical files should be accelerated rather than gated by the cap.
- A new project chooses NOT to invoke the skill but later complains of coder drift on architectural decisions — means the skill is insufficiently discoverable or its onboarding is missing. Promote its mention from a paragraph in CLAUDE.md to a Phase 0 check in `kiat-team-lead`.
- An autonomous BMad session is observed to run the skill without `--apply` confirmation actually happening — means the dry-run default was bypassable; the contract needs hardening (e.g., enforce the gate in the tool, not just in the prose).

### Links
- PR #4 on `github.com/sopial42/kiat` — full design rationale and adversarial review transcript in the PR comment
- <!-- [LGT pilot architecture.md](../../../nova-notariat/bmad_thinking/_bmad-output/planning-artifacts/architecture.md) -->
- Planned follow-up: `kiat-promote-project-memory` (cap-triggered promotion skill), `kiat-validate-project-memory` CI check (cap / staleness / ref rot), LGT pilot instrumentation

---

## Retroactive entries (EV-0100..EV-0199)

> Decisions or observations from before this log existed, documented retroactively on 2026-05-16. These entries preserve wisdom that lived only in commit messages, reconcile notes, or contributors' memory.

---

## EV-0100 — Producer-pays gate convention (pre-formalization)

```yaml
id: EV-0100
date: 2026-05-16
type: observation
status: superseded_by:EV-0001
touches:
  - .claude/specs/reconciliation-protocol.md
triggered_by:
  - audit:delivery/_audit/axis-B-failure-patterns.md
key_metrics:
  - "'producer-pays' appears in 15/44 reconcile_complete notes (34%) over 2026-04-27..2026-05-14"
decided_by: emergent convention (no explicit decision)
```

### Context
For the first 3 weeks of Kiat operation, coders developed a tacit pattern: at handoff time, resolve L1-severity deviations inline rather than routing them to `/bmad-correct-course`. The notes call it the "producer-pays gate" because the producer (coder) pays the cost of resolution rather than externalizing it. This convention was never documented in the framework.

### Decision
This entry documents the convention's existence retroactively. It is **superseded** by EV-0001 (epic-16 story-01) which officializes the gate in `reconciliation-protocol.md`.

### Links
- <!-- [Axis B §4 shadow patterns](../delivery/_audit/axis-B-failure-patterns.md) -->
- [EV-0001](#ev-0001--officialize-the-producer-pays-gate)

---

## EV-0101 — FP-001..FP-005 batch creation (epic-01 Clerk cutover)

```yaml
id: EV-0101
date: 2026-05-16
type: observation
status: active
touches:
  - .claude/specs/failure-patterns.md
  - delivery/specs/failure-patterns/FP-001-*.md
  - delivery/specs/failure-patterns/FP-002-*.md
  - delivery/specs/failure-patterns/FP-003-*.md
  - delivery/specs/failure-patterns/FP-004-*.md
  - delivery/specs/failure-patterns/FP-005-*.md
triggered_by:
  - audit:delivery/_audit/axis-B-failure-patterns.md
key_metrics:
  - "All 5 FPs created on the same day: 2026-04-27 (epic-01 Phase 7)"
  - "Cascade discovery: each FP surfaced as a fix-induced revelation of the next (Next.js rewrite → middleware double-gate → useAppFetch race → JWKS no-cache → AbortController missing)"
  - "All 5 patterns related to Clerk + Next.js auth flow"
decided_by: kiat-team-lead (during epic-01 incident response)
```

### Context
The first major framework stress test was epic-01 Phase 7 (Clerk authentication cutover on 2026-04-27). Five distinct failure patterns surfaced in a single day, each revealing the next as it was fixed. They share a theme: client-side fetch + Clerk session + Next.js dev-mode quirks compound in ways that the layers 1-5 enforcement couldn't predict.

### Decision
The 5 FPs were created in the same session as the incident. Each documents a specific symptom + structural fix. As of 2026-05-16, recurrence count is 1 for all 5 — either the documented preventions work, OR the conditions (Clerk dev FAPI redirect-loop, dev-mode double-mount, no JWKS cache) don't reproduce post-cutover.

This entry records the batch nature of the creation so a future analyst doesn't misread "all FPs same date" as a flaw in the registry.

### Re-evaluate if
- Any FP-001..FP-005 increments recurrence ≥ 2 — means the prevention wasn't structural enough.
- A new Clerk-related FP surfaces with a symptom similar to one of these 5 — may indicate insufficient generalization.

### Links
- <!-- [Axis B §1 inventory](../delivery/_audit/axis-B-failure-patterns.md) -->

---

## EV-0102 — Coder context budget calibration (25k → 35k)

```yaml
id: EV-0102
date: 2026-05-16
type: calibration
status: active
touches:
  - .claude/specs/context-budgets.md
triggered_by:
  - story:delivery/epics/epic-00/story-01a-backend-skeleton-and-guards (calibration event verbatim)
  - story:delivery/epics/epic-00/story-02-frontend-skeleton
key_metrics:
  - "calibration event story-01a: 'backend-coder budget raised 25k→35k on this story (Phase 0b ambient-dominated)'"
  - "calibration event story-02-frontend-skeleton: 'frontend-coder budget raised 25k→35k (mirroring backend calibration)'"
  - "context-budget overflows since calibration: 0/80 stories"
decided_by: kiat-team-lead (Phase 0b feedback during epic-00)
```

### Context
During the first stories of epic-00, the backend-coder and frontend-coder budgets at 25 k tokens were dominated by ambient docs (CLAUDE.md + per-layer convention docs + testing.md). The story spec + per-story specs only fit if the coder accepted a tight pre-flight margin. Two consecutive Phase 0b runs raised the ceiling to 35 k, which has held since with zero overflow.

### Decision
35 k is now the standing ceiling for both kiat-backend-coder and kiat-frontend-coder. Phase 0b pre-flight checks against 35 k. Reviewers stay at 20 k (their input is the diff, not the full codebase).

### Alternatives rejected
- **A — Keep 25 k and force on-demand loading of all docs**: rejected after 2 calibrations — the friction was real, not phantom.
- **B — Raise higher to 50 k**: rejected — would defeat the purpose of context-discipline. 35 k still requires the coder to load on demand for testing-pitfalls and similar.

### Re-evaluate if
- Any new ambient doc grows to push the 35 k ceiling — refactor before raising again.
- A new agent type is added with different ambient needs — calibrate independently.

### Links
- <!-- [Axis A §5 calibration events](../delivery/_audit/axis-A-quantitative.md) -->

---

## EV-0103 — Observation: mode field has accumulated 7 distinct values

```yaml
id: EV-0103
date: 2026-05-16
type: observation
status: superseded_by:EV-0005
touches:
  - delivery/metrics/events.jsonl
triggered_by:
  - audit:delivery/_audit/axis-A-quantitative.md
key_metrics:
  - "Mode values observed in 80 rollups: normal (68), team_lead_full (4), informal_request_to_done (3), solo (2), full_pipeline (1), team_lead_direct (1), team_lead_direct_light (1)"
decided_by: emergent (no taxonomy was ever defined)
```

### Context
The `mode` field in story_rollup events was never enum-restricted in `metrics-events.md`. Different Team Lead sessions added new values opportunistically — `informal_request_to_done`, `full_pipeline`, `team_lead_direct_light` are all variants invented at write time. Result: 7 distinct values, none documented, analytics non-comparable.

### Decision
This entry is observational. It is **superseded** by EV-0005 (epic-16 story-05) which enum-restricts `mode` to `{normal, solo, team_lead_authored}` in the v2 schema.

### Links
- <!-- [Axis A §2](../delivery/_audit/axis-A-quantitative.md) -->
- [EV-0005](#ev-0005--eventsjsonl-v2-schema-archive--restart)

---

## EV-0104 — Observation: Team Lead invented non-canonical `failure_pattern_id` strings

```yaml
id: EV-0104
date: 2026-05-16
type: observation
status: superseded_by:EV-0006
touches:
  - .claude/specs/failure-patterns.md
triggered_by:
  - audit:delivery/_audit/axis-B-failure-patterns.md
key_metrics:
  - "Stories with failure_pattern_id populated: 2/80"
  - "Both values are non-canonical: PROCESS_PARALLEL_CODER_INTERFERENCE_NEW, PROCESS_BE_CODER_RETRY_NEW"
  - "Canonical format FP-NNN: 0 occurrences in events.jsonl"
decided_by: emergent (Team Lead wanted to classify but didn't create FP files)
```

### Context
Two Team Lead sessions populated `failure_pattern_id` with spontaneous strings (`PROCESS_PARALLEL_CODER_INTERFERENCE_NEW`, `PROCESS_BE_CODER_RETRY_NEW`) instead of the canonical `FP-NNN` format. Reading the registry workflow, they wanted to classify the failure but found the per-FP file creation too heavyweight, so they invented inline IDs instead.

### Decision
This entry is observational and signals friction in the FP creation process. It is **superseded** by EV-0006 (epic-16 story-06) which expands FP creation triggers and adds passive detection via `report.py`, lowering the activation cost.

### Links
- <!-- [Axis B §5](../delivery/_audit/axis-B-failure-patterns.md) -->
- [EV-0006](#ev-0006--fp-registry-revival)

---

_End of file. Append new entries at the bottom of the appropriate range (EV-NNNN forward block, EV-01NN retroactive block). Never edit existing entries._
