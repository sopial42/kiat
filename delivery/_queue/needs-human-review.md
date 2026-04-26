# Needs Human Review

> Append-only queue of L2 reconciliation proposals from `/bmad-correct-course`.
> Schema, lifecycle, and consumer rules:
> [`../../.claude/specs/reconciliation-protocol.md`](../../.claude/specs/reconciliation-protocol.md).
> Folder contract: [`README.md`](README.md).
>
> **Each entry has one of four statuses**: `OPEN` (fresh, awaits human),
> `RESOLVED` (human accepted, action taken), `REJECTED` (human
> declined), `PROMOTED` (auto-escalated to L3 by tech-spec-writer Phase
> -1 scope-overlap check).
>
> **Never delete entries.** Closed entries are the audit trail.
> **Never reuse `Q-NNN` IDs.** Always increment.

<!-- QUEUE_BLOCK_BEGIN -->

_(no entries yet — this file is fresh)_

<!-- QUEUE_BLOCK_END -->
