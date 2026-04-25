# Reconciliation Queue

Asynchronous human-triage queue for L2 reconciliation proposals raised
by `bmad-reconcile`. The full protocol — including who writes, who
reads, and when entries get force-closed — lives in
[`../../.claude/specs/reconciliation-protocol.md`](../../.claude/specs/reconciliation-protocol.md).

This README is the **folder-level contract** — a quick orientation for
humans, not a duplicate of the protocol.

---

## What lives here

- **`needs-human-review.md`** — the single, append-only queue file. One
  file (not one-per-entry) so the whole queue is greppable in one read
  and so `bmad-retrospective` can close everything in one pass.

That's it. Don't add other files here without updating the protocol
first — the directory's structure is part of the contract.

---

## How entries flow

1. **Append** — `bmad-reconcile` writes a new `## Q-NNN — [OPEN]` entry
   when it triages an L2 deviation that needs a human judgment call.
2. **Scope-overlap check** — every new story's tech-spec-writer scans
   this file at Phase -1. An OPEN entry whose `Affects` overlaps the
   new story's scope auto-promotes from L2 to L3 (status becomes
   `PROMOTED`, an `epic_block` event is written, the new story handoff
   fails until the human resolves).
3. **Human triage** — humans read open entries asynchronously, decide
   ACCEPT / REJECT, edit the entry's status from `OPEN` to `RESOLVED` or
   `REJECTED` and fill the `Decision` field. Entries are **never
   deleted** — closed entries are the audit trail.
4. **Epic-close force-flush** — `bmad-retrospective` reads every
   remaining `OPEN` entry from the closing epic and forces a decision
   (with the human in the loop) before the epic can flip to `✅ Done`.

---

## When to read the queue

| Role | When | What you're looking for |
|---|---|---|
| Human (PO / Tech Lead) | Anytime, on push notification, or weekly | OPEN entries; triage them |
| `bmad-reconcile` | Never reads — only appends | n/a |
| Tech-spec-writer | Phase -1 of every new story | OPEN entries whose `Affects` overlaps the new story |
| `bmad-retrospective` | Once per epic, at retro | OPEN entries from this epic, to force-close |
| Team Lead | Never reads the queue directly — reads `events.jsonl` for L3 escalations instead | n/a |

---

## What goes here vs. elsewhere

| If your need is… | Where it goes |
|---|---|
| Async proposal (judgment call, multiple landing spots) | here, as L2 |
| Blocking issue (contradicts existing rule, breaks shipped work) | `delivery/metrics/events.jsonl` as `epic_block` event — NOT here |
| Already-applied change (low-risk, obvious target) | already landed in `delivery/business/` or `delivery/specs/` — recorded in the story's `.reconcile.md`, not here |
| Process improvement (template change, agent prompt tweak) | `_epic.reconcile.md` "Process lessons" section, not here |

---

## Don't

- ❌ **Don't delete entries**, even REJECTED or PROMOTED ones — they're
  the audit trail.
- ❌ **Don't reuse `Q-NNN` IDs**. New entries always increment.
- ❌ **Don't write entries by hand** under normal flow — let
  `bmad-reconcile` do it. Manual entries break the auto-promotion check
  unless they follow the schema exactly.
- ❌ **Don't put L3 escalations here**. L3 goes to `events.jsonl` so
  Team Lead's pre-launch check can find it.
