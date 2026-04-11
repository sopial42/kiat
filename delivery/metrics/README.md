# delivery/metrics/

Runtime data written by `kiat-team-lead`. Do not edit by hand.

## What lives here

- **`events.jsonl`** — append-only JSONL event log, one line per phase transition. Schema in [`.claude/specs/metrics-events.md`](../../.claude/specs/metrics-events.md). Team Lead is the single writer; everyone else is a reader.

The `.jsonl` file itself is **gitignored** (see root `.gitignore`) because the data is project-specific and ephemeral. It will be created automatically the first time Team Lead runs a story.

## Who reads it

- `python3 .claude/tools/report.py` — weekly health report generator
- Humans, occasionally, for ad-hoc grep debugging
