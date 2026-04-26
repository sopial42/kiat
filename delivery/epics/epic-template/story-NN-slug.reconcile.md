# Deviations & Reconciliation: story-NN-<slug>

> Companion to [story-NN-<slug>.md](./story-NN-<slug>.md). Created by
> Team Lead at Phase 5c (writes the Deviations section). Updated by
> `/bmad-correct-course` (writes the Reconciliation section, ending
> with the `RECONCILE_DONE` marker).
>
> **The story spec file itself is never modified by reconciliation.**
> All deviations and triage outcomes live here.
>
> This file exists ONLY when at least one coder reported a deviation —
> stories that ship as specified do NOT get a `.reconcile.md`.
>
> Schema and protocol authoritative source:
> [`../../../.claude/specs/reconciliation-protocol.md`](../../../.claude/specs/reconciliation-protocol.md).
>
> Created at: <ISO-8601 UTC timestamp>

---

## Deviations

> Aggregated by Team Lead at Phase 5c from each coder's `Business
> Deviations:` handoff block. Validated by
> `.claude/tools/hooks/check-post-delivery-schema.sh` on Team Lead
> SubagentStop.

<!-- POST_DELIVERY_BLOCK_BEGIN -->
### Backend deviations

- **Tag**: AC-N | **Severity**: L1
  **Summary**: <one-line, non-jargon, readable by a non-coder>
  **File**: <path:line — what was changed>
  **SpecRef**: <story-NN.md:line for AC-N tags, or "none" for gaps>
  **Status**: RESOLVED | NEEDS_PROMOTION | BLOCKING
  **Why**: <one or two sentences — the business or technical reason>

### Frontend deviations

- _(none)_
<!-- POST_DELIVERY_BLOCK_END -->

---

## Reconciliation

> Filled by `/bmad-correct-course` when the human invokes it on this
> story. Until filled, this section contains the placeholder
> `_(awaiting reconciliation — run /bmad-correct-course on this
> story)_`.

_(awaiting reconciliation — run `/bmad-correct-course` on this story)_

<!--
When /bmad-correct-course runs, it REPLACES the placeholder above with
the four sub-sections below and the RECONCILE_DONE marker:

### L1 — Auto-applied

| Tag | Action | Target | Verified |
|---|---|---|---|
| AC-N | <what changed> | <file:line> | ✓ |
| ... | ... | ... | ... |

_(or `_(no L1 entries)_` if reconcile applied nothing automatically)_

### L2 — Queued for human triage

| Queue ID | Tag | Proposal (one-liner) | Affects | Status |
|---|---|---|---|---|
| Q-NNN | <tag> | <short proposal> | <doc path or files> | OPEN |
| ... | ... | ... | ... | ... |

→ Full proposals in [`../../_queue/needs-human-review.md`](../../_queue/needs-human-review.md)

_(or `_(no L2 entries)_` if no proposals queued)_

### L3 — Escalated, blocking

| Tag | Reason | Event reference | Resolution required |
|---|---|---|---|
| <tag> | <why this blocks the next story> | `epic_block` line N of `delivery/metrics/events.jsonl` | <what the human must do> |
| ... | ... | ... | ... |

_(or `_(no L3 entries)_` if reconcile produced no blockers)_

### Outcome

- **Applied (L1)**: <count> changes
- **Queued (L2)**: <count> proposals
- **Blocked (L3)**: <count> escalations
- **Story-(NN+1) launchable**: <yes | no — see L3 above>

<!- - RECONCILE_DONE: <ISO-8601 UTC timestamp> - ->
-->
