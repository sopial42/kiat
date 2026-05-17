# Team Lead — Stage 1: Intake

> Loaded on demand by Team Lead at the start of every story. Covers the **solo-mode fast path** (Phase -2), the **clean working tree gate** (Phase 0.1) and the **reconciliation pre-launch check** (Phase 0.2). All three run before any other work.

---

## Phase -2 — Solo-mode fast path (conditional, runs FIRST on every request)

For surgical, low-risk work, the full pipeline (spec writer → coders → reviewers → Phase 5c) is over-ceremony. Phase -2 is a fast path where **Team Lead does the work alone** — no spec writer, no coders, no reviewers, no Phase 5c companion at ship time. The trade-off: the human accepts that the type-checker, linter, and the test the story includes act as the reviewer proxy, and that reconciliation will happen post-hoc via `/bmad-correct-course` recover-mode.

Solo-mode has **two tracks**, gated by T-shirt size, plus a default-pipeline tier:

| Size | Track | Authorization model |
|---|---|---|
| **XS** | **Track A — XS solo (lightweight gate)** | Standing user authorization — once given, applies to every future XS story. Recorded in user memory. |
| **S** | **Track B — S solo (full 5-rule gate)** | Per-story explicit authorization required — user must say "solo this one" / "petit morceau, vas-y seul" / etc. for each S story. |
| **M, L, XL** | **Track C — full pipeline** | Solo-mode is REFUSED regardless of authorization. No exception. |

Team Lead **never self-elects solo-mode** — and never self-elects the size to fit a track. The size is determined by the spec or by Team Lead's honest sizing of the surface (file count + fix path complexity), not retro-fitted to qualify for solo.

### Track A — XS solo (lightweight gate)

XS is the size class where reviewer overhead has the worst ROI: the cycle cost (~10-15 min wall-clock + tokens) is comparable to the coding work itself. The standing authorization removes the per-story friction; the file-count + cross-cutting + spec-cleanliness gates remove the actual risk.

**Eligibility — ALL conditions must hold:**

| # | Condition | Examples / non-examples |
|---|---|---|
| XS-1 | Standing user authorization for XS solo | ✅ User has previously said "XS = solo par défaut" / "tu peux faire toutes les XS seul" / equivalent (recorded in `~/.claude/projects/.../memory/`). ❌ Never been authorized → REFUSE and ask once for the standing authz. |
| XS-2 | Size = XS, with explicit Team Lead justification | ✅ ≤5 files modified + ≤1 test file added/modified + ≤30 net lines outside the test. ❌ "Feels small" without counting. The justification line MUST appear in the audit log. |
| XS-3 | No cross-cutting file touched | ✅ Story scope is contained within a single feature surface. ❌ Any file in [`delivery/specs/cross-cutting-files.md`](../../../delivery/specs/cross-cutting-files.md) (registries, dispatchers, catalogs) — REFUSE regardless of size. |
| XS-4 | Spec is `CLEAR` per `kiat-validate-spec` | ✅ Story file passes the validator (run it before coding, even on XS). ❌ Spec is fuzzy → escalate to spec writer first, then come back to XS solo. |

That's it — **no E4 scope set, no E5 zero-behavior-change**. An XS bug fix or behavior change is allowed in Track A *because the file-count gate (XS-2) bounds the blast radius and the included test (≤1) IS the regression contract*. If the story doesn't include a test, it cannot be XS — by definition.

**Anti-inflation rule**: when sizing as XS, Team Lead MUST justify both the file count AND the absence of cross-cutting files in the audit log. Vague "small story" → REFUSE Track A and re-evaluate as S.

### Track B — S solo (full 5-rule gate, unchanged)

S is the size class where the reviewer cycle has middling ROI — sometimes overkill (mechanical refactor across 8 files), sometimes load-bearing (new behavior on existing surface). The 5-rule gate exists to discriminate: it admits only the cases where the type-checker + existing tests genuinely cover the change.

**Eligibility — ALL conditions must hold:**

| # | Condition | Examples / non-examples |
|---|---|---|
| S-1 | Explicit per-story user authorization | ✅ "petit morceau, tu peux le faire seul", "solo this one", `--solo`, "ship it directly". ❌ Silence, "go ahead", "do it" — those are launch authorizations, not solo authorizations. Standing XS authz does NOT extend to S. |
| S-2 | T-shirt size = S | ✅ S. ❌ M, L, XL — even with explicit authorization. (XS uses Track A, not this gate.) |
| S-3 | Surface chirurgicale | ✅ ≤ ~10 files touched, mostly mechanical. ❌ Cross-cutting registry edits (see [`delivery/specs/cross-cutting-files.md`](../../../delivery/specs/cross-cutting-files.md)). |
| S-4 | Scope ∈ {type-system widening, palette/CSS additions, doc-only, mechanical refactor} | ✅ Adding a value to a TypeScript union, adding a CSS token + palette mapping, dropping a deprecated literal across N test files. ❌ New endpoint, new component, new business rule, new migration, anything that changes user-observable behavior. |
| S-5 | Zero behavior change | ✅ The new code does not change runtime behavior for any code path that exists today. ❌ "Tiny new validation", "small new toast", "just one new flag". |

If a story is sized S **and** would change observable behavior **and** has user authorization, the right move is usually to rescope it as XS (tighter file count + 1 test) and use Track A — not to bend Track B.

### Track C — full pipeline (M and above)

For M, L, XL: solo-mode is REFUSED, no matter what the user says. The blast radius and the spec ambiguity surface are too large for type-checker-as-reviewer to cover. If the user insists, the right answer is to split the story into smaller pieces (each potentially solo-eligible), not to bypass the gate.

### Refusal messages

```
Solo-mode REFUSED (Track C): T-shirt size = M. Solo-mode is unavailable for M+ regardless of authorization. Either split into XS/S pieces, or proceed with full pipeline.
```
```
Solo-mode REFUSED (Track A → fallback to Track B): no standing XS authz on file. Asking once: "do you want to authorize XS = solo by default for this project? If yes, I'll record it and proceed; if no, I'll ask per-story."
```
```
Solo-mode REFUSED (Track B): Track B requires explicit per-story authorization. Standing XS authz does not extend to S. Either authorize this S story explicitly, or proceed with full pipeline.
```
```
Solo-mode REFUSED (Track A on size mismatch): story sized S (8 files + 1 test). XS requires ≤5 files + ≤1 test. Falling back to Track B 5-rule gate.
```
```
Solo-mode REFUSED (Track A on cross-cutting): story touches `frontend/src/components/features/searches/applies-to.ts` (cross-cutting registry). Cross-cutting edits forbid solo-mode regardless of size or authorization.
```

### Solo-mode procedure (replaces Phases -1 through 5d for this story — same for Track A and Track B)

When the gate passes (either Track):

1. **Author the story file directly** at `delivery/epics/epic-X/story-NN-<slug>.md`. Include a populated `## Implementation discipline` section that documents the solo-mode track + authorization (verbatim user authorization quote + date for Track B; cite the standing memory entry for Track A) and the eligibility check outcome. The story file is the audit trail — without it, the solo decision is invisible to future retros.
2. **Write the code directly**. No coder agent. Apply project conventions from `delivery/specs/` exactly as the coders would.
3. **Run the reviewer proxy**: `npm run lint`, `tsc --noEmit` (FE) or `go vet ./...` + `go build ./...` (BE), and the test the story includes (Track A: the single test required by XS-2 is mandatory; Track B: any existing E2E or unit suite that exercises the touched surface). The proxy MUST be green before commit.
4. **Commit** with an explicit `Story shipped solo (Track A | Track B) by Team Lead per <user-authorization-verbatim or memory entry> <date>` line in the commit body.
5. **Emit the rollup event** with `"mode": "solo"`, `"solo_track": "A" | "B"`, and the `business_deviations` count derived from the story file's `## What was deferred` + `## Implementation discipline` sections (typically 1-3 — at minimum a `PROCESS_SOLO_MODE` audit-only deviation).
6. **Skip Phase 5c at ship time**. The `.reconcile.md` companion file is NOT created here — it is produced post-hoc by `/bmad-correct-course` recover-mode (see [`bmad-reconcile-contract.md`](../../specs/bmad-reconcile-contract.md) §"Solo-mode recovery"). Until recover-mode runs, the story has no companion file.
7. **Emit Phase 5d notification** as `RECONCILIATION_NEEDED` exactly as the normal flow would — the recover-mode entry point is the same `/bmad-correct-course` skill. The skill auto-detects solo-mode (no Phase 5c upstream) and reconstitutes the companion from the story file + commit body.

### Audit lines (always emit, one of the variants below)

Track A pass:
```
Solo-mode eligibility: PASS Track A (XS-1 standing authz "XS = solo par défaut" 2026-05-02 / XS-2 size=XS justified 4 files + 1 test + 22 net lines / XS-3 no cross-cutting / XS-4 spec CLEAR) — proceeding solo
```

Track B pass:
```
Solo-mode eligibility: PASS Track B (S-1 user authz "petit morceau" 2026-05-02 / S-2 size=S / S-3 5 files chirurgical / S-4 scope=type-system+palette / S-5 zero behavior change) — proceeding solo
```

Track C refusal:
```
Solo-mode eligibility: REFUSED Track C — size=M, full pipeline mandatory
```

Track A refusal (size mismatch):
```
Solo-mode eligibility: FAIL Track A on XS-2 (story sized S = 8 files + 1 test, XS requires ≤5 files), trying Track B
```

No authorization at all (Track B + no standing XS authz):
```
Solo-mode: not authorized by user — proceeding to Phase -1 normal routing
```

### Why this two-track model exists

The original single-gate model (E1-E5 conjunctive) was too restrictive on XS — it forced a behavior-changing one-line bug fix through the same hoops as a feature ship, which broke the cost/value ratio. At the same time, simply removing E5 across the board would have reintroduced the failure mode that motivated the rule (silent behavior drift on ungated solo ships).

The two-track split (2026-05-02) resolves the tension: **size IS the gate**. XS bounds the blast radius mechanically (≤5 files + ≤1 test), so behavior change is acceptable as long as the test is the regression contract. S keeps the 5-rule gate because at S the file count alone is too generous (~10 files can hide subtle multi-file regressions). M+ keeps the absolute refusal because at that size the spec authoring itself is load-bearing — solo would skip the spec writer's decomposition value.

The standing XS authorization model (vs. per-story for S) reflects user intent: at XS size, the per-story authz prompt is just friction the user always answers "yes" to. Standing makes it a one-time setup. At S, the per-story prompt is the moment to actually think — is this story really mechanical? Is it really zero behavior change? — so per-story stays.

Anti-pattern to avoid: **Team Lead size-gaming**. If a story is genuinely S in scope (file count + complexity) and Team Lead downgrades to XS to fit Track A, that's the silent drift this whole gate was designed to prevent. The audit line MUST cite the file count + test count + net lines so the user can spot the gaming retroactively.

---

## Phase 0.1 — Clean working tree gate

Run `git status --porcelain`. If the output is non-empty, REFUSE to launch:

- Surface the dirty paths to the user
- Diagnose: a previous story's code that was never committed (most common), concurrent Team Lead session, or manual edits
- Escalate with: *"Working tree is dirty — N untracked + M modified paths. The previous story did not commit cleanly, OR another session is in flight, OR there are uncommitted manual edits. Refusing to launch story-NN until tree is clean."*
- Do NOT proceed to 0.2, do NOT touch the story file

This gate exists because the most catastrophic failure mode of the pipeline is two stories interfering on the same files via an uncommitted working tree. The 2026-05-01 incident (4 epic-09 stories rolled-up `passed` while their code lived only in a dirty tree, then was lost across 20+ resets) is exactly what this gate prevents.

**Audit line (always emit)**:
```
Working tree gate: clean ✓
```
or
```
Working tree gate: 27 modified + 12 untracked paths ❌ — REFUSED to launch story-NN
```

---

## Phase 0.2 — Reconciliation pre-launch check

Before doing ANY other work on a new story, scan `delivery/metrics/events.jsonl` for unresolved reconciliation blocks. The full protocol is in [`.claude/specs/reconciliation-protocol.md`](../../specs/reconciliation-protocol.md); short version:

1. Grep the last ~200 lines of `events.jsonl` for `"event":"epic_block"` entries whose `epic` matches the new story's epic.
2. For each match, look for a corresponding `"event":"epic_unblock"` entry that references it (via the `blocks_cleared` array). A block is "resolved" when an unblock cites its `(deviation_tag, ts)` pair.
3. **If any unresolved `epic_block` exists** for this epic, REFUSE to launch:
   - Set the story's `**Status**` line to `🛑 Blocked` (not `📝 Drafted`)
   - Update the epic aggregate the same way
   - Escalate to the user with the full block context (deviation tag, summary, the `.reconcile.md` it came from, the queue ID if applicable)
   - Do NOT proceed to Phase 0a, Phase 0b, or anything else
4. **If no unresolved blocks**, emit the audit line and proceed to Phase 0a.

**Audit line (always emit)**:
```
Reconciliation pre-launch: 0 unresolved epic_block events for epic-X ✓
```
or
```
Reconciliation pre-launch: 1 unresolved epic_block for epic-X (story-05 SPEC_GAP "RLS contract break") ❌ — REFUSED to launch story-NN
```

**Why this gate exists**: an L3 escalation from a previous story's reconcile means *this story or future stories may inherit broken assumptions*. The block exists specifically to force a human decision before more work piles on top. Skipping this check defeats the entire reconciliation protocol — it's the difference between "we caught the issue" and "we caught the issue and acted on it before silent drift occurred". This gate is non-negotiable.
