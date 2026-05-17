#!/usr/bin/env python3
"""
Kiat health report generator.

Reads delivery/metrics/events.jsonl (append-only JSONL event log written by
Team Lead) and emits a markdown health report to stdout.

Usage:
    python3 .claude/tools/report.py                              # active file (v2 events)
    python3 .claude/tools/report.py --scope all-time             # active + archive (legacy normalized)
    python3 .claude/tools/report.py --since 2026-04-01           # filter by date
    python3 .claude/tools/report.py --epic epic-3                # filter by epic
    python3 .claude/tools/report.py --events <path>              # custom input path
    python3 .claude/tools/report.py --output report.md           # write to file

Schema: see .claude/specs/metrics-events.md (v2)
No external dependencies — stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_EVENTS_PATH = Path("delivery/metrics/events.jsonl")
DEFAULT_ARCHIVE_PATH = Path("delivery/metrics/events.archive-2026-05-16.jsonl")


@dataclass
class Story:
    """Per-story rollup computed from raw events."""
    story_id: str
    epic: str | None = None
    received_at: datetime | None = None
    passed_at: datetime | None = None
    escalated_at: datetime | None = None
    escalation_reason: str | None = None
    escalation_fp: str | None = None
    spec_verdict: str | None = None
    spec_clarification_rounds: int = 0
    preflight_overflow: bool = False
    preflight_estimates: dict[str, int] = field(default_factory=dict)  # agent -> tokens
    backend_cycles: int = 0
    frontend_cycles: int = 0
    backend_final_verdict: str | None = None
    frontend_final_verdict: str | None = None
    clerk_skill_runs: int = 0
    clerk_verdicts: list[str] = field(default_factory=list)
    test_patterns_inconsistencies: int = 0
    total_issues: int = 0
    fix_budget_min: int | None = None
    fix_budget_started_at: datetime | None = None
    fix_budget_exhausted: bool = False

    @property
    def total_cycles(self) -> int:
        return self.backend_cycles + self.frontend_cycles

    @property
    def total_elapsed_min(self) -> int | None:
        end = self.passed_at or self.escalated_at
        if self.received_at and end:
            delta = end - self.received_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def status(self) -> str:
        if self.passed_at:
            return "PASSED"
        if self.escalated_at:
            return "ESCALATED"
        return "IN_PROGRESS"


def parse_ts(raw: str) -> datetime:
    """Parse ISO 8601 UTC timestamp. Accepts Z or +00:00 suffix."""
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def load_events(path: Path) -> list[dict[str, Any]]:
    """Read JSONL file, skipping malformed lines with a warning."""
    events: list[dict[str, Any]] = []
    if not path.exists():
        print(f"# No metrics file at {path}", file=sys.stderr)
        print(f"# (This is expected before the first story runs.)", file=sys.stderr)
        return events

    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(
                    f"# Warning: malformed JSONL at {path}:{lineno} — {exc}",
                    file=sys.stderr,
                )
    return events


def normalize_legacy_event(evt: dict[str, Any]) -> dict[str, Any]:
    """Normalize a legacy (v1/v1.1/v1.2) story_rollup to v2 shape in-memory.

    Does not mutate the input — returns a shallow-merged copy. Only applies
    when schema field is absent (legacy). v2 events pass through unchanged.
    """
    if evt.get("schema") == "v2":
        return evt
    if evt.get("event") != "story_rollup":
        return evt

    out = dict(evt)

    # business_deviations: int → object
    bd = out.get("business_deviations")
    if isinstance(bd, int):
        out["business_deviations"] = {"count": bd, "backend": [], "frontend": []}
    elif bd is None:
        out["business_deviations"] = {"count": 0, "backend": [], "frontend": []}

    # spec: flat fields → block (preserve original fields for audit)
    if "spec" not in out:
        out["spec"] = {
            "verdict": out.get("spec_verdict"),
            "byte_count": out.get("bmad_spec_bytes"),
            "clarification_rounds": out.get("spec_clarification_rounds", 0),
            "writer_mode": "unknown",
        }

    # reviews (dict) → review_cycles (list)
    if "review_cycles" not in out and "reviews" in out:
        reviews = out.get("reviews") or {}
        cycles_list = []
        if isinstance(reviews, dict):
            for domain, data in reviews.items():
                if not isinstance(data, dict):
                    continue
                cycles_list.append({
                    "domain": domain,
                    "cycles": data.get("cycles", 0),
                    "final_verdict": data.get("final_verdict"),
                    "clerk_skill_triggered": data.get("clerk_skill_triggered", False),
                    "clerk_verdict": data.get("clerk_verdict"),
                    "test_patterns_consistent": data.get("test_patterns_consistent", True),
                    "total_issues_across_cycles": data.get("total_issues_across_cycles", 0),
                })
        out["review_cycles"] = cycles_list

    # prod_validation: drop silently
    out.pop("prod_validation", None)

    return out


def filter_events(
    events: list[dict[str, Any]],
    since: datetime | None,
    epic: str | None,
) -> list[dict[str, Any]]:
    """Apply --since and --epic filters."""
    out = []
    for evt in events:
        ts_raw = evt.get("ts")
        if since and ts_raw:
            try:
                if parse_ts(ts_raw) < since:
                    continue
            except ValueError:
                continue
        if epic and evt.get("epic") != epic:
            continue
        out.append(evt)
    return out


def _as_bool(value: Any) -> bool | None:
    """Defensively coerce a value to bool, handling common LLM mis-writes."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "1"):
            return True
        if lowered in ("false", "no", "0", ""):
            return False
    return None


def _as_int(value: Any) -> int | None:
    """Defensively coerce a value to int, handling common LLM mis-writes."""
    if value is None:
        return None
    if isinstance(value, bool):  # bool is a subclass of int in Python — exclude
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return None
    return None


def _apply_rollup(
    story: Story,
    evt: dict[str, Any],
    ts: datetime | None,
    escalated: bool,
) -> None:
    """Apply a v1.1 rollup event (story_rollup or story_escalated) to a Story.

    This is authoritative: if a rollup is present, it overwrites any prior
    partial state computed from legacy events. Fields are parsed defensively
    to handle common LLM mis-writes (type drift, null as string, etc.).
    """
    # Timestamp: completion time (rollup) or escalation time
    if escalated:
        story.escalated_at = ts
        story.escalation_reason = evt.get("reason")
        story.escalation_fp = evt.get("failure_pattern_id")
        if story.escalation_reason == "fix_budget_exhausted":
            story.fix_budget_exhausted = True
    else:
        story.passed_at = ts

    # Spec validation — v2 uses `spec` block; legacy uses flat fields
    spec_block = evt.get("spec")
    if isinstance(spec_block, dict):
        spec_verdict = spec_block.get("verdict")
        if spec_verdict:
            story.spec_verdict = spec_verdict
        rounds = _as_int(spec_block.get("clarification_rounds"))
        if rounds is not None:
            story.spec_clarification_rounds = rounds
    else:
        # legacy flat fields
        spec_verdict = evt.get("spec_verdict")
        if spec_verdict:
            story.spec_verdict = spec_verdict
        rounds = _as_int(evt.get("spec_clarification_rounds"))
        if rounds is not None:
            story.spec_clarification_rounds = rounds

    # Pre-flight estimates (per agent)
    preflight = evt.get("preflight") or {}
    if isinstance(preflight, dict):
        for agent_name, data in preflight.items():
            if not isinstance(data, dict):
                continue
            est = _as_int(data.get("estimated_tokens")) or 0
            story.preflight_estimates[agent_name] = est
            if data.get("result") == "overflow":
                story.preflight_overflow = True

    def _apply_review_entry(domain: str, data: dict[str, Any]) -> None:
        cycles = _as_int(data.get("cycles")) or 0
        final_verdict = data.get("final_verdict")
        clerk_triggered = _as_bool(data.get("clerk_skill_triggered"))
        clerk_verdict = data.get("clerk_verdict")
        patterns_ok = _as_bool(data.get("test_patterns_consistent"))
        issues = _as_int(data.get("total_issues_across_cycles")) or 0

        if domain == "backend":
            story.backend_cycles = cycles
            story.backend_final_verdict = final_verdict
        elif domain == "frontend":
            story.frontend_cycles = cycles
            story.frontend_final_verdict = final_verdict

        story.total_issues += issues
        if clerk_triggered:
            story.clerk_skill_runs += 1
            if clerk_verdict:
                story.clerk_verdicts.append(clerk_verdict)
        if patterns_ok is False:
            story.test_patterns_inconsistencies += 1

    # Reviews — v2 uses `review_cycles` array; legacy uses `reviews` dict
    review_cycles = evt.get("review_cycles")
    if isinstance(review_cycles, list):
        for entry in review_cycles:
            if not isinstance(entry, dict):
                continue
            domain = entry.get("domain", "")
            _apply_review_entry(domain, entry)
    else:
        reviews = evt.get("reviews") or {}
        if isinstance(reviews, dict):
            for domain, data in reviews.items():
                if not isinstance(data, dict):
                    continue
                _apply_review_entry(domain, data)

    # Best-effort elapsed times (may be null — that's fine)
    fix_used = _as_int(evt.get("fix_budget_used_min"))
    if fix_used is not None and fix_used > 0:
        # Synthesize a fake fix_budget_started_at for display purposes
        if ts:
            from datetime import timedelta
            story.fix_budget_started_at = ts - timedelta(minutes=fix_used)
            story.fix_budget_min = 45

    total_elapsed = _as_int(evt.get("total_elapsed_min"))
    if total_elapsed is not None and ts and not story.received_at:
        from datetime import timedelta
        story.received_at = ts - timedelta(minutes=total_elapsed)


def rollup_stories(events: list[dict[str, Any]]) -> dict[str, Story]:
    """Group events by story and compute per-story metrics."""
    stories: dict[str, Story] = {}

    for evt in events:
        story_id = evt.get("story")
        if not story_id:
            continue
        story = stories.setdefault(story_id, Story(story_id=story_id))

        if "epic" in evt and not story.epic:
            story.epic = evt["epic"]

        event_type = evt.get("event")
        ts_raw = evt.get("ts")
        ts = None
        if ts_raw:
            try:
                ts = parse_ts(ts_raw)
            except ValueError:
                pass

        # v1.1 PRIMARY events (rollup-first) — check these first
        if event_type == "story_rollup":
            _apply_rollup(story, evt, ts, escalated=False)
            continue

        elif event_type == "story_escalated":
            _apply_rollup(story, evt, ts, escalated=True)
            continue

        # v1.0 LEGACY events — aggregated on the fly if no rollup present
        if event_type == "received":
            story.received_at = ts

        elif event_type == "spec_validated":
            verdict = evt.get("verdict")
            story.spec_verdict = verdict
            if verdict == "NEEDS_CLARIFICATION":
                story.spec_clarification_rounds += 1

        elif event_type == "preflight":
            agent = evt.get("agent", "unknown")
            est = evt.get("estimated_tokens", 0)
            story.preflight_estimates[agent] = est
            if evt.get("result") == "overflow":
                story.preflight_overflow = True

        elif event_type == "review":
            agent = evt.get("agent", "")
            verdict = evt.get("verdict")
            is_backend = "backend" in agent
            if is_backend:
                story.backend_cycles += 1
                story.backend_final_verdict = verdict
            else:
                story.frontend_cycles += 1
                story.frontend_final_verdict = verdict
            story.total_issues += evt.get("issues_count", 0)
            if evt.get("clerk_skill_triggered"):
                story.clerk_skill_runs += 1
                cv = evt.get("clerk_verdict")
                if cv:
                    story.clerk_verdicts.append(cv)
            if evt.get("test_patterns_consistent") is False:
                story.test_patterns_inconsistencies += 1

        elif event_type == "fix_budget_started":
            story.fix_budget_started_at = ts
            story.fix_budget_min = evt.get("budget_min", 45)

        elif event_type == "escalated":
            story.escalated_at = ts
            story.escalation_reason = evt.get("reason")
            story.escalation_fp = evt.get("failure_pattern_id")
            if evt.get("reason") == "fix_budget_exhausted":
                story.fix_budget_exhausted = True

        elif event_type == "passed":
            story.passed_at = ts
            if evt.get("backend_verdict"):
                story.backend_final_verdict = evt["backend_verdict"]
            if evt.get("frontend_verdict"):
                story.frontend_final_verdict = evt["frontend_verdict"]

    return stories


SCHEMA_MARKER = (
    "_Schema: v2 (events.jsonl), "
    "legacy archive available at events.archive-2026-05-16.jsonl_"
)

# Tag prefixes eligible for FP candidate detection (Trigger C).
# AC-T*, DECISION, BOY_* are excluded to avoid trivial noise.
_FP_CANDIDATE_ENUM_PREFIXES = {"SPEC_GAP", "PROCESS"}
_TAG_RE = re.compile(r"\*\*Tag\*\*\s*:\s*([A-Z][A-Z0-9_]+)")


_ENUM_PREFIXES = {
    "SPEC_GAP", "DECISION", "SCOPE_CUT", "BOY_SCOUT",
    "DOMAIN_NEW", "PROCESS", "TEST_DRIFT", "UPSTREAM_MISMATCH",
}


def _bucket_tag(raw_tag: str) -> str:
    """Map a raw tag to its 8-value enum prefix, or "OTHER" if no match.

    Handles both single-word (DECISION, PROCESS) and multi-word
    (SPEC_GAP, UPSTREAM_MISMATCH) enum values uniformly: match the full
    enum value as a prefix of the tag, followed by either end-of-string
    or "_<suffix>".
    """
    for prefix in _ENUM_PREFIXES:
        if raw_tag == prefix or raw_tag.startswith(prefix + "_"):
            return prefix
    return "OTHER"


def compute_tag_distribution(epics_root: Path) -> dict[str, int]:
    """Parse **Tag**: lines from all story-*.reconcile.md files and group by enum prefix.

    Matches each tag against the 8-value enum (some enum values contain underscores,
    e.g. SPEC_GAP, UPSTREAM_MISMATCH), checking whether the tag starts with an enum
    value followed by _ or end-of-string. Tags that don't match are bucketed as OTHER.
    """
    counts: Counter[str] = Counter()
    for reconcile_file in sorted(epics_root.glob("*/story-*.reconcile.md")):
        try:
            text = reconcile_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _TAG_RE.finditer(text):
            counts[_bucket_tag(match.group(1))] += 1
    return dict(counts)


def detect_fp_candidates(
    epics_root: Path,
    window_days: int = 30,
) -> list[dict[str, Any]]:
    """Scan *.reconcile.md files for Trigger C FP candidates.

    Returns a list of dicts: {prefix, story_count, stories: [str]}.
    Only SPEC_* and PROCESS_* prefixes with ≥ 3 distinct stories in the
    rolling window are returned. Uses file mtime as the story date proxy.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    # prefix -> set of story_ids within the window
    prefix_stories: dict[str, set[str]] = defaultdict(set)

    for reconcile_file in sorted(epics_root.glob("*/story-*.reconcile.md")):
        # Date proxy: file mtime
        try:
            mtime = datetime.fromtimestamp(
                reconcile_file.stat().st_mtime, tz=timezone.utc
            )
        except OSError:
            continue
        if mtime < cutoff:
            continue

        story_id = reconcile_file.stem  # e.g. story-05-archive-events...

        try:
            text = reconcile_file.read_text(encoding="utf-8")
        except OSError:
            continue

        for match in _TAG_RE.finditer(text):
            bucket = _bucket_tag(match.group(1))
            if bucket in _FP_CANDIDATE_ENUM_PREFIXES:
                prefix_stories[bucket].add(story_id)

    candidates = []
    for prefix, stories in sorted(prefix_stories.items()):
        if len(stories) >= 3:
            candidates.append(
                {
                    "prefix": prefix,
                    "story_count": len(stories),
                    "stories": sorted(stories),
                }
            )
    return candidates


# ============================================================================
# v2.1 observability helpers (schema v2.1)
# ============================================================================


def compute_tag_distribution_by_epic(
    epics_root: Path,
) -> dict[str, dict[str, int]]:
    """Per-epic version of compute_tag_distribution.

    Returns: {epic_dir_name: {prefix: count}}, where epic_dir_name is the
    directory name (e.g. "epic-16-kiat-framework-improvements").
    """
    by_epic: dict[str, Counter[str]] = defaultdict(Counter)
    for reconcile_file in sorted(epics_root.glob("*/story-*.reconcile.md")):
        epic_name = reconcile_file.parent.name
        try:
            text = reconcile_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _TAG_RE.finditer(text):
            by_epic[epic_name][_bucket_tag(match.group(1))] += 1
    return {epic: dict(c) for epic, c in sorted(by_epic.items())}


def compute_reconciliation_latency(
    events: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    """Pair `reconciliation_needed` with `reconcile_complete` events.

    Pairing key: (epic, story). Pairing strategy: **positional** — the
    N-th `reconciliation_needed` for a given (epic, story) pairs with
    the N-th `reconcile_complete` for the same key. This supports
    legitimate re-reconcile cycles (per bmad-reconcile-contract.md
    §"Idempotency and re-runs"). Latency = complete.ts - needed.ts
    in minutes. Negative deltas (clock skew, mis-write) are dropped
    from the latency stats but still counted as paired.

    Returns:
        (by_epic, unpaired_needed_count)

        by_epic: {epic: {"n": int, "p50": int, "p90": int, "min": int, "max": int}}
        unpaired_needed_count: count of `reconciliation_needed` events with no
                               matching `reconcile_complete` (stories awaiting triage).
    """
    needed: dict[tuple[str, str], list[datetime]] = defaultdict(list)
    completed: dict[tuple[str, str], list[datetime]] = defaultdict(list)

    for evt in events:
        evt_type = evt.get("event")
        if evt_type not in ("reconciliation_needed", "reconcile_complete"):
            continue
        epic = evt.get("epic") or ""
        story = evt.get("story") or ""
        if not story:
            continue
        try:
            ts = parse_ts(evt.get("ts", ""))
        except (ValueError, TypeError):
            continue
        key = (epic, story)
        if evt_type == "reconciliation_needed":
            needed[key].append(ts)
        else:
            completed[key].append(ts)

    # Stabilise pairing order by ts so out-of-order writes still pair correctly.
    for ts_list in needed.values():
        ts_list.sort()
    for ts_list in completed.values():
        ts_list.sort()

    by_epic: dict[str, list[int]] = defaultdict(list)
    unpaired = 0
    for key, need_list in needed.items():
        comp_list = completed.get(key, [])
        paired = min(len(need_list), len(comp_list))
        unpaired += len(need_list) - paired
        for i in range(paired):
            delta_min = int((comp_list[i] - need_list[i]).total_seconds() / 60)
            if delta_min < 0:
                continue
            by_epic[key[0]].append(delta_min)

    out: dict[str, dict[str, Any]] = {}
    for epic, latencies in sorted(by_epic.items()):
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        if n == 0:
            continue

        def pct(p: float, lat: list[int] = sorted_lat, count: int = n) -> int:
            idx = min(int(count * p / 100), count - 1)
            return lat[idx]

        out[epic or "(no-epic)"] = {
            "n": n,
            "p50": pct(50),
            "p90": pct(90),
            "min": sorted_lat[0],
            "max": sorted_lat[-1],
        }
    return out, unpaired


def compute_severity_by_tag(
    events: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Aggregate `severity_by_tag` across all `reconcile_complete` events.

    Returns: {tag_prefix: {"L1": int, "L2": int, "L3": int}}.
    Only tag prefixes that appear in at least one event are included.
    """
    out: dict[str, dict[str, int]] = defaultdict(
        lambda: {"L1": 0, "L2": 0, "L3": 0}
    )
    for evt in events:
        if evt.get("event") != "reconcile_complete":
            continue
        sbt = evt.get("severity_by_tag") or {}
        if not isinstance(sbt, dict):
            continue
        for tag_prefix, sev_counts in sbt.items():
            if not isinstance(sev_counts, dict):
                continue
            for sev in ("L1", "L2", "L3"):
                v = _as_int(sev_counts.get(sev)) or 0
                out[tag_prefix][sev] += v
    return {k: dict(v) for k, v in sorted(out.items())}


_QUEUE_ENTRY_RE = re.compile(
    r"^##\s+Q-\d+\s+—\s+`\[(OPEN|RESOLVED|REJECTED|PROMOTED|SUPERSEDED)\]`",
    re.MULTILINE,
)


def compute_l2_queue_stats(queue_path: Path) -> dict[str, int]:
    """Parse the L2 queue file and count entries by current status.

    Returns: {"total": int, "OPEN": int, "RESOLVED": int, "REJECTED": int,
              "PROMOTED": int, "SUPERSEDED": int}.

    Returns all-zero counts if the queue file doesn't exist or can't be read.
    """
    counts = {
        "total": 0,
        "OPEN": 0,
        "RESOLVED": 0,
        "REJECTED": 0,
        "PROMOTED": 0,
        "SUPERSEDED": 0,
    }
    if not queue_path.exists():
        return counts
    try:
        text = queue_path.read_text(encoding="utf-8")
    except OSError:
        return counts
    for m in _QUEUE_ENTRY_RE.finditer(text):
        status = m.group(1)
        counts["total"] += 1
        counts[status] = counts.get(status, 0) + 1
    return counts


def format_report(
    stories: dict[str, Story],
    filter_desc: str,
    events: list[dict[str, Any]] | None = None,
) -> str:
    """Render the markdown report."""
    if not stories:
        return (
            "# Kiat Health Report\n\n"
            f"{SCHEMA_MARKER}\n\n"
            f"{filter_desc}\n\n"
            "_No stories in scope. Run some stories through Team Lead first._\n"
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append("# Kiat Health Report")
    lines.append("")
    lines.append(SCHEMA_MARKER)
    lines.append("")
    lines.append(f"_Generated {now} — {filter_desc}_")
    lines.append("")

    # ---------- Summary ----------
    n_total = len(stories)
    n_passed = sum(1 for s in stories.values() if s.status == "PASSED")
    n_escalated = sum(1 for s in stories.values() if s.status == "ESCALATED")
    n_inprogress = sum(1 for s in stories.values() if s.status == "IN_PROGRESS")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total stories:** {n_total}")
    lines.append(f"- **Passed:** {n_passed}")
    lines.append(f"- **Escalated:** {n_escalated}")
    lines.append(f"- **In progress:** {n_inprogress}")

    completed = [s for s in stories.values() if s.status in ("PASSED", "ESCALATED")]
    if completed:
        elapsed_values = [s.total_elapsed_min for s in completed if s.total_elapsed_min is not None]
        cycle_values = [s.total_cycles for s in completed]
        if elapsed_values:
            lines.append(
                f"- **Avg elapsed time per story:** {sum(elapsed_values) // len(elapsed_values)} min "
                f"(min {min(elapsed_values)}, max {max(elapsed_values)})"
            )
        if cycle_values:
            avg_cycles = sum(cycle_values) / len(cycle_values)
            lines.append(f"- **Avg review cycles per story:** {avg_cycles:.1f}")
    lines.append("")

    # ---------- Spec validation ----------
    spec_verdicts = Counter(s.spec_verdict for s in stories.values() if s.spec_verdict)
    clarification_total = sum(s.spec_clarification_rounds for s in stories.values())
    if spec_verdicts:
        lines.append("## Spec Validation (Phase 0a)")
        lines.append("")
        for verdict in ("CLEAR", "NEEDS_CLARIFICATION", "BLOCKED"):
            count = spec_verdicts.get(verdict, 0)
            lines.append(f"- **{verdict}:** {count}")
        lines.append(f"- **Total clarification rounds (tech-spec-writer + BMad):** {clarification_total}")
        if n_total and spec_verdicts.get("CLEAR", 0) < n_total * 0.7:
            lines.append("")
            lines.append("> ⚠️ CLEAR rate below 70% — investigate which layer is letting ambiguities through (Business Context / BMad vs technical sections / tech-spec-writer) and tighten that author's clarification loop.")
        lines.append("")

    # ---------- Pre-flight overflow ----------
    overflow_stories = [s for s in stories.values() if s.preflight_overflow]
    lines.append("## Pre-flight Context Budget (Phase 0b)")
    lines.append("")
    lines.append(f"- **Stories with budget overflow:** {len(overflow_stories)} / {n_total}")
    if overflow_stories:
        lines.append("- **Overflow incidents:**")
        for s in overflow_stories:
            ests = ", ".join(f"{agent}={tok}" for agent, tok in s.preflight_estimates.items())
            lines.append(f"  - `{s.story_id}` — estimates: {ests}")
    if n_total and len(overflow_stories) / n_total > 0.2:
        lines.append("")
        lines.append("> ⚠️ Overflow rate > 20% — the tech-spec-writer may be producing stories too large (ask it to split more aggressively) OR budget is too tight.")
    lines.append("")

    # ---------- Verdict distribution ----------
    backend_verdicts = Counter(
        s.backend_final_verdict for s in stories.values() if s.backend_final_verdict
    )
    frontend_verdicts = Counter(
        s.frontend_final_verdict for s in stories.values() if s.frontend_final_verdict
    )
    if backend_verdicts or frontend_verdicts:
        lines.append("## Review Verdict Distribution (Final)")
        lines.append("")
        lines.append("| Agent | APPROVED | NEEDS_DISCUSSION | BLOCKED |")
        lines.append("|---|---|---|---|")
        if backend_verdicts:
            lines.append(
                f"| kiat-backend-reviewer | {backend_verdicts.get('APPROVED', 0)} "
                f"| {backend_verdicts.get('NEEDS_DISCUSSION', 0)} "
                f"| {backend_verdicts.get('BLOCKED', 0)} |"
            )
        if frontend_verdicts:
            lines.append(
                f"| kiat-frontend-reviewer | {frontend_verdicts.get('APPROVED', 0)} "
                f"| {frontend_verdicts.get('NEEDS_DISCUSSION', 0)} "
                f"| {frontend_verdicts.get('BLOCKED', 0)} |"
            )
        lines.append("")

    # ---------- Cycles per story ----------
    cycles_counter = Counter(s.total_cycles for s in completed)
    if cycles_counter:
        lines.append("## Cycles Per Story")
        lines.append("")
        for cycles in sorted(cycles_counter):
            bar = "█" * cycles_counter[cycles]
            lines.append(f"- **{cycles} cycles:** {cycles_counter[cycles]} {bar}")
        lines.append("")

    # ---------- Fix budget distribution (retrospective; EV-0003 retired the 45-min gate) ----------
    fix_used_values = [
        s.fix_budget_min
        for s in stories.values()
        if s.fix_budget_started_at and s.fix_budget_min is not None
    ]
    # fix_budget_min is set to the elapsed value at rollup-apply time, so it doubles as the per-story
    # retrospective minute count. See _apply_rollup.
    elapsed_values: list[int] = []
    for s in stories.values():
        if s.fix_budget_started_at and s.passed_at:
            delta = int((s.passed_at - s.fix_budget_started_at).total_seconds() / 60)
            if delta >= 0:
                elapsed_values.append(delta)
    if elapsed_values:
        lines.append("## Fix Budget Distribution (retrospective)")
        lines.append("")
        lines.append(
            f"- **Stories that entered a fix cycle:** {len(elapsed_values)} / {n_total}"
        )
        elapsed_sorted = sorted(elapsed_values)
        p50 = elapsed_sorted[len(elapsed_sorted) // 2]
        p90_idx = max(0, int(len(elapsed_sorted) * 0.9) - 1)
        p90 = elapsed_sorted[p90_idx]
        lines.append(f"- **min / p50 / p90 / max (min):** "
                     f"{elapsed_sorted[0]} / {p50} / {p90} / {elapsed_sorted[-1]}")
        lines.append("")
        lines.append("> Field kept for retro analytics only — the 45-min escalation gate "
                     "was retired by EV-0003 (zero firings over 80 stories).")
        lines.append("")

    # ---------- Clerk skill ----------
    clerk_run_stories = [s for s in stories.values() if s.clerk_skill_runs > 0]
    clerk_verdicts_all = Counter()
    for s in stories.values():
        clerk_verdicts_all.update(s.clerk_verdicts)
    if clerk_run_stories or clerk_verdicts_all:
        lines.append("## Clerk Auth Skill (Layer 3)")
        lines.append("")
        lines.append(f"- **Stories triggering kiat-clerk-auth-review:** {len(clerk_run_stories)} / {n_total}")
        if clerk_verdicts_all:
            lines.append("- **Clerk verdict distribution:**")
            for verdict, count in clerk_verdicts_all.most_common():
                lines.append(f"  - `{verdict}`: {count}")
        lines.append("")

    # ---------- Test patterns consistency ----------
    inconsistent = [s for s in stories.values() if s.test_patterns_inconsistencies > 0]
    if inconsistent:
        lines.append("## Test-Patterns Check (Coder Step 0.5)")
        lines.append("")
        lines.append(
            f"- **Stories where coder's code violated acknowledged test patterns:** "
            f"{len(inconsistent)}"
        )
        for s in inconsistent:
            lines.append(f"  - `{s.story_id}` — {s.test_patterns_inconsistencies} inconsistency event(s)")
        lines.append("")
        lines.append("> ⚠️ Acknowledged ≠ applied. Coders are skimming kiat-test-patterns-check. "
                     "Consider making the check stricter or escalating drift.")
        lines.append("")

    # ---------- Escalations ----------
    escalations = [s for s in stories.values() if s.escalated_at]
    if escalations:
        reasons = Counter(s.escalation_reason for s in escalations)
        lines.append("## Escalations")
        lines.append("")
        lines.append(f"- **Total escalations:** {len(escalations)}")
        lines.append("- **Reasons:**")
        for reason, count in reasons.most_common():
            lines.append(f"  - `{reason}`: {count}")
        lines.append("")
        lines.append("**Details:**")
        for s in escalations:
            fp_note = f" → {s.escalation_fp}" if s.escalation_fp else ""
            lines.append(f"- `{s.story_id}` ({s.epic or 'no-epic'}): {s.escalation_reason}{fp_note}")
        lines.append("")

    # ---------- Deviation Tag Distribution (EV-0008: 8-prefix enum) ----------
    epics_root = Path("delivery/epics")
    tag_distribution = compute_tag_distribution(epics_root)
    lines.append("## Deviation Tag Distribution")
    lines.append("")
    lines.append(
        "_Groups `**Tag**:` prefixes from all `story-*.reconcile.md` files by the 8-value enum "
        "(EV-0008). Unknown prefixes surface as `OTHER` — they are pre-epic-16 free-form tags or "
        "invalid new ones the hook should have caught._"
    )
    lines.append("")
    if not tag_distribution:
        lines.append("_No `.reconcile.md` files found — no tag data._")
    else:
        total_tags = sum(v for v in tag_distribution.values())
        lines.append("| Prefix | Count | % of total |")
        lines.append("|---|---|---|")
        for prefix, count in sorted(tag_distribution.items(), key=lambda x: -x[1]):
            pct = 100 * count / total_tags if total_tags else 0
            lines.append(f"| `{prefix}` | {count} | {pct:.1f}% |")
        lines.append(f"| **Total** | **{total_tags}** | 100% |")
    lines.append("")

    # ---------- Phase 1: Per-Epic Tag Distribution ----------
    tag_by_epic = compute_tag_distribution_by_epic(epics_root)
    if tag_by_epic:
        lines.append("### By epic")
        lines.append("")
        lines.append(
            "_Same data, broken down per epic. Highlights which epics generated which deviation "
            "categories — useful for spotting epic-level patterns (e.g. one epic dominated by "
            "TEST_DRIFT signals a testing-discipline gap, one dominated by SPEC_GAP signals a "
            "spec-clarity gap)._"
        )
        lines.append("")
        # Collect the union of prefixes that appear in any epic, ordered by global frequency
        prefixes_in_use = sorted(
            {p for epic_data in tag_by_epic.values() for p in epic_data.keys()},
            key=lambda p: -tag_distribution.get(p, 0),
        )
        header = "| Epic |" + "".join(f" `{p}` |" for p in prefixes_in_use) + " Total |"
        sep = "|---|" + "---|" * (len(prefixes_in_use) + 1)
        lines.append(header)
        lines.append(sep)
        for epic, prefix_counts in tag_by_epic.items():
            row_total = sum(prefix_counts.values())
            cells = [f" {prefix_counts.get(p, 0)} |" for p in prefixes_in_use]
            lines.append(f"| `{epic}` |" + "".join(cells) + f" **{row_total}** |")
        lines.append("")

    # ---------- Phase 1: Reconciliation Latency (human-triage cost) ----------
    if events is not None:
        latency_by_epic, unpaired = compute_reconciliation_latency(events)
        lines.append("## Reconciliation Latency (Phase 1)")
        lines.append("")
        lines.append(
            "_Time between Team Lead emitting `reconciliation_needed` (Phase 5d) and "
            "`/bmad-correct-course` emitting `reconcile_complete`. Measures the **human-triage "
            "cost** per story. A growing p90 means humans are bottlenecking the pipeline._"
        )
        lines.append("")
        if not latency_by_epic and unpaired == 0:
            lines.append("_No `reconciliation_needed` / `reconcile_complete` pairs in scope._")
        else:
            lines.append("| Epic | N paired | p50 (min) | p90 (min) | Min | Max |")
            lines.append("|---|---|---|---|---|---|")
            for epic, stats in latency_by_epic.items():
                lines.append(
                    f"| `{epic}` | {stats['n']} | {stats['p50']} | {stats['p90']} | "
                    f"{stats['min']} | {stats['max']} |"
                )
            if unpaired > 0:
                lines.append("")
                lines.append(
                    f"**Unpaired:** {unpaired} `reconciliation_needed` event(s) without a "
                    f"matching `reconcile_complete` — stories still awaiting human triage."
                )
        lines.append("")

        # ---------- Phase 1: Severity × Tag Cross-Table ----------
        severity_by_tag = compute_severity_by_tag(events)
        lines.append("## Severity × Tag Cross-Table (Phase 1)")
        lines.append("")
        lines.append(
            "_For each tag prefix, the final L1 / L2 / L3 breakdown post-triage by "
            "`/bmad-correct-course`. Reads `severity_by_tag` from `reconcile_complete` events. "
            "Surfaces which categories of deviation cluster at which severities project-wide — "
            "e.g. a high L3 % on a given prefix means that category routinely produces blocking "
            "drift._"
        )
        lines.append("")
        if not severity_by_tag:
            lines.append(
                "_No `severity_by_tag` data on `reconcile_complete` events in scope. "
                "Either no reconciles have run yet, or they predate schema v2.1._"
            )
        else:
            lines.append("| Tag prefix | L1 | L2 | L3 | Total | % L3 |")
            lines.append("|---|---|---|---|---|---|")
            grand_l1 = 0
            grand_l2 = 0
            grand_l3 = 0
            grand_total = 0
            for prefix, sev in sorted(severity_by_tag.items()):
                row_total = sev["L1"] + sev["L2"] + sev["L3"]
                pct_l3 = 100 * sev["L3"] / row_total if row_total else 0
                grand_l1 += sev["L1"]
                grand_l2 += sev["L2"]
                grand_l3 += sev["L3"]
                grand_total += row_total
                lines.append(
                    f"| `{prefix}` | {sev['L1']} | {sev['L2']} | {sev['L3']} | "
                    f"{row_total} | {pct_l3:.1f}% |"
                )
            pct_l3_overall = 100 * grand_l3 / grand_total if grand_total else 0
            lines.append(
                f"| **Total** | **{grand_l1}** | **{grand_l2}** | **{grand_l3}** | "
                f"**{grand_total}** | **{pct_l3_overall:.1f}%** |"
            )
        lines.append("")

    # ---------- Phase 1: L2 Queue Health (promotion-rate drift signal) ----------
    queue_path = Path("delivery/_queue/needs-human-review.md")
    queue_stats = compute_l2_queue_stats(queue_path)
    if queue_stats["total"] > 0 or queue_path.exists():
        lines.append("## L2 Queue Health (Phase 1)")
        lines.append("")
        lines.append(
            "_Counts the L2 queue at [`delivery/_queue/needs-human-review.md`](delivery/_queue/needs-human-review.md) "
            "by current status. **Promotion rate** = `PROMOTED / total` (L2 → L3 auto-promotions "
            "by Team Lead Phase 0c on scope-overlap). A rising promotion rate means queue items "
            "are not being triaged fast enough, and downstream stories keep colliding with them._"
        )
        lines.append("")
        total = queue_stats["total"]
        if total == 0:
            lines.append("_Queue file exists but is empty._")
        else:
            promoted = queue_stats["PROMOTED"]
            promotion_rate = 100 * promoted / total if total else 0
            lines.append(f"- **Total entries ever opened:** {total}")
            lines.append(f"- **OPEN:** {queue_stats['OPEN']}")
            lines.append(f"- **RESOLVED:** {queue_stats['RESOLVED']}")
            lines.append(f"- **REJECTED:** {queue_stats['REJECTED']}")
            lines.append(
                f"- **PROMOTED to L3:** {promoted} "
                f"(**{promotion_rate:.1f}%** promotion rate)"
            )
            lines.append(f"- **SUPERSEDED:** {queue_stats['SUPERSEDED']}")
        lines.append("")

    # ---------- FP Candidates (passive detection — Trigger C) ----------
    candidates = detect_fp_candidates(epics_root)
    lines.append("## FP Candidates (passive detection)")
    lines.append("")
    lines.append(
        "_Scans `delivery/epics/*/story-*.reconcile.md` files modified in the last 30 days "
        "for `SPEC_*` / `PROCESS_*` tag prefixes appearing across ≥ 3 distinct stories. "
        "Does NOT auto-create FP files — surfaces candidates for human review (Trigger C)._"
    )
    lines.append("")
    if not candidates:
        lines.append("_No candidates detected._")
    else:
        for c in candidates:
            lines.append(
                f"- **{c['prefix']}**: {c['story_count']} stories — "
                + ", ".join(f"`{s}`" for s in c["stories"])
                + " → Consider creating FP-NNN per Trigger C"
            )
    lines.append("")

    # ---------- Per-story table ----------
    lines.append("## Stories (Table)")
    lines.append("")
    lines.append("| Story | Epic | Status | Cycles | Elapsed (min) | Backend | Frontend | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for story_id in sorted(stories.keys()):
        s = stories[story_id]
        notes = []
        if s.spec_verdict and s.spec_verdict != "CLEAR":
            notes.append(f"spec:{s.spec_verdict}")
        if s.preflight_overflow:
            notes.append("overflow")
        if s.test_patterns_inconsistencies:
            notes.append(f"patterns-drift:{s.test_patterns_inconsistencies}")
        if s.escalation_fp:
            notes.append(s.escalation_fp)
        elapsed = s.total_elapsed_min if s.total_elapsed_min is not None else "-"
        lines.append(
            f"| `{s.story_id}` "
            f"| {s.epic or '-'} "
            f"| {s.status} "
            f"| {s.total_cycles} "
            f"| {elapsed} "
            f"| {s.backend_final_verdict or '-'} "
            f"| {s.frontend_final_verdict or '-'} "
            f"| {', '.join(notes) if notes else '-'} |"
        )
    lines.append("")

    return "\n".join(lines) + "\n"


def validate_events_file(path: Path) -> tuple[int, list[str]]:
    """Validate every line of the events file against the v1.1 schema.

    Returns (exit_code, issues) where exit_code is 0 if all events are valid,
    1 otherwise. issues is a list of human-readable strings describing each
    problem, prefixed with the line number.

    Validation is lenient on purpose: we flag schema issues but we never crash
    on a malformed line. The goal is to tell the user exactly which line is
    broken and why, not to refuse to read anything.
    """
    issues: list[str] = []

    if not path.exists():
        return 0, [f"(no events file at {path} — nothing to validate)"]

    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue

            # 1) Must be valid JSON
            try:
                evt = json.loads(raw)
            except json.JSONDecodeError as exc:
                issues.append(f"L{lineno}: invalid JSON — {exc}")
                continue

            # 2) Must be an object
            if not isinstance(evt, dict):
                issues.append(f"L{lineno}: top-level value must be an object, got {type(evt).__name__}")
                continue

            # 3) Common required fields
            for field in ("ts", "story", "event"):
                if field not in evt:
                    issues.append(f"L{lineno}: missing required field `{field}`")

            # 4) ts must parse as ISO 8601 if present
            if "ts" in evt and evt["ts"] is not None:
                try:
                    parse_ts(str(evt["ts"]))
                except ValueError:
                    issues.append(f"L{lineno}: `ts` is not a valid ISO 8601 UTC timestamp: {evt['ts']!r}")

            event_type = evt.get("event")
            if not event_type:
                continue  # already flagged

            # 5) Per-event-type validation
            if event_type == "story_rollup":
                _validate_rollup(evt, lineno, issues, escalated=False)
            elif event_type == "story_escalated":
                _validate_rollup(evt, lineno, issues, escalated=True)
            elif event_type == "reconciliation_needed":
                _validate_reconciliation_needed(evt, lineno, issues)
            elif event_type == "reconcile_complete":
                _validate_reconcile_complete(evt, lineno, issues)
            elif event_type == "reconcile_failed":
                _validate_reconcile_failed(evt, lineno, issues)
            elif event_type == "epic_block":
                _validate_epic_block(evt, lineno, issues)
            elif event_type == "epic_unblock":
                _validate_epic_unblock(evt, lineno, issues)
            elif event_type == "queue_supersede":
                _validate_queue_supersede(evt, lineno, issues)
            elif event_type in {
                "received", "spec_validated", "preflight", "coder_launched",
                "coder_finished", "review", "fix_budget_started", "escalated",
                "passed", "correction",
            }:
                # Legacy v1.0 events — only lightly checked, they're deprecated
                pass
            else:
                issues.append(f"L{lineno}: unknown event type {event_type!r}")

    exit_code = 1 if issues else 0
    return exit_code, issues


def _validate_rollup(
    evt: dict[str, Any],
    lineno: int,
    issues: list[str],
    escalated: bool,
) -> None:
    """Validate a v1.1 rollup event (story_rollup or story_escalated)."""
    name = "story_escalated" if escalated else "story_rollup"

    # outcome field
    expected_outcome = "escalated" if escalated else "passed"
    actual_outcome = evt.get("outcome")
    if actual_outcome != expected_outcome:
        issues.append(
            f"L{lineno}: {name} `outcome` should be {expected_outcome!r}, got {actual_outcome!r}"
        )

    # escalation-specific required fields
    if escalated:
        for field in ("escalated_to", "reason"):
            if field not in evt:
                issues.append(f"L{lineno}: {name} missing required field `{field}`")
        # `reached_stage` (v2+) or legacy `reached_phase` (v1/v1.1) — accept either
        if "reached_stage" not in evt and "reached_phase" not in evt:
            issues.append(f"L{lineno}: {name} missing required field `reached_stage` (or legacy `reached_phase`)")
        valid_reasons = {
            "spec_blocked", "spec_clarification_loop", "budget_overflow",
            "fix_budget_exhausted", "needs_discussion", "security_blocker",
            "test_flakiness", "other",
        }
        reason = evt.get("reason")
        if reason is not None and reason not in valid_reasons:
            issues.append(
                f"L{lineno}: {name} `reason` {reason!r} is not in the valid set "
                f"({', '.join(sorted(valid_reasons))})"
            )
        valid_targets = {"tech-spec-writer", "bmad", "user", "designer"}
        target = evt.get("escalated_to")
        if target is not None and target not in valid_targets:
            issues.append(
                f"L{lineno}: {name} `escalated_to` {target!r} is not in the valid set "
                f"({', '.join(sorted(valid_targets))})"
            )

    # spec_verdict
    if "spec_verdict" in evt:
        valid_verdicts = {"CLEAR", "NEEDS_CLARIFICATION", "BLOCKED"}
        if evt["spec_verdict"] not in valid_verdicts:
            issues.append(
                f"L{lineno}: {name} `spec_verdict` {evt['spec_verdict']!r} is not in "
                f"{valid_verdicts}"
            )

    # preflight shape
    preflight = evt.get("preflight")
    if preflight is not None and not isinstance(preflight, dict):
        issues.append(
            f"L{lineno}: {name} `preflight` should be an object, got {type(preflight).__name__}"
        )
    elif isinstance(preflight, dict):
        for agent, data in preflight.items():
            if not isinstance(data, dict):
                issues.append(
                    f"L{lineno}: {name} preflight entry for {agent!r} should be an object"
                )
                continue
            if data.get("result") not in ("pass", "overflow", None):
                issues.append(
                    f"L{lineno}: {name} preflight[{agent}].result must be 'pass' or 'overflow', "
                    f"got {data.get('result')!r}"
                )

    # reviews shape
    reviews = evt.get("reviews")
    if reviews is not None and not isinstance(reviews, dict):
        issues.append(
            f"L{lineno}: {name} `reviews` should be an object, got {type(reviews).__name__}"
        )
    elif isinstance(reviews, dict):
        valid_verdicts = {"APPROVED", "NEEDS_DISCUSSION", "BLOCKED"}
        for domain, data in reviews.items():
            if domain not in ("backend", "frontend"):
                issues.append(
                    f"L{lineno}: {name} reviews.{domain} should be 'backend' or 'frontend'"
                )
            if not isinstance(data, dict):
                continue
            fv = data.get("final_verdict")
            if fv is not None and fv not in valid_verdicts:
                issues.append(
                    f"L{lineno}: {name} reviews.{domain}.final_verdict {fv!r} not in {valid_verdicts}"
                )


# ============================================================================
# Validators for reconciliation events (v1.2 + v2.1)
# Lite-schema: required fields + enum/type checks, no deep field semantics.
# Schema source of truth: .claude/specs/metrics-events.md
# ============================================================================


def _check_int_field(
    evt: dict[str, Any],
    field: str,
    name: str,
    lineno: int,
    issues: list[str],
    required: bool = True,
) -> None:
    if field not in evt:
        if required:
            issues.append(f"L{lineno}: {name} missing required field `{field}`")
        return
    if _as_int(evt[field]) is None:
        issues.append(
            f"L{lineno}: {name} `{field}` must be an int, got {type(evt[field]).__name__}"
        )


def _check_severity_breakdown(
    sev: Any,
    field_path: str,
    name: str,
    lineno: int,
    issues: list[str],
) -> None:
    """Validate a {"L1": int, "L2": int, "L3": int} object."""
    if not isinstance(sev, dict):
        issues.append(
            f"L{lineno}: {name} `{field_path}` should be an object, got {type(sev).__name__}"
        )
        return
    for level in ("L1", "L2", "L3"):
        if level in sev and _as_int(sev[level]) is None:
            issues.append(
                f"L{lineno}: {name} `{field_path}.{level}` must be an int, got {sev[level]!r}"
            )


def _validate_reconciliation_needed(
    evt: dict[str, Any], lineno: int, issues: list[str]
) -> None:
    name = "reconciliation_needed"
    for field in ("reconcile_path", "deviations_count", "deviations_unresolved"):
        if field not in evt:
            issues.append(f"L{lineno}: {name} missing required field `{field}`")
    _check_int_field(evt, "deviations_count", name, lineno, issues, required=False)
    _check_int_field(evt, "deviations_unresolved", name, lineno, issues, required=False)
    if "severity_hint" in evt:
        _check_severity_breakdown(
            evt["severity_hint"], "severity_hint", name, lineno, issues
        )


def _validate_reconcile_complete(
    evt: dict[str, Any], lineno: int, issues: list[str]
) -> None:
    name = "reconcile_complete"
    for field in (
        "reconcile_path", "l1_applied", "l2_queued", "l3_blocked",
        "next_story_launchable",
    ):
        if field not in evt:
            issues.append(f"L{lineno}: {name} missing required field `{field}`")
    for cnt in ("l1_applied", "l2_queued", "l3_blocked"):
        _check_int_field(evt, cnt, name, lineno, issues, required=False)
    if "next_story_launchable" in evt and not isinstance(
        evt["next_story_launchable"], bool
    ):
        issues.append(
            f"L{lineno}: {name} `next_story_launchable` must be a bool, "
            f"got {type(evt['next_story_launchable']).__name__}"
        )
    if "queue_ids_added" in evt and not isinstance(evt["queue_ids_added"], list):
        issues.append(
            f"L{lineno}: {name} `queue_ids_added` should be a list, "
            f"got {type(evt['queue_ids_added']).__name__}"
        )
    # severity_by_tag (Phase 1 v2.1 additive)
    if "severity_by_tag" in evt:
        sbt = evt["severity_by_tag"]
        if not isinstance(sbt, dict):
            issues.append(
                f"L{lineno}: {name} `severity_by_tag` should be an object, "
                f"got {type(sbt).__name__}"
            )
        else:
            for tag_prefix, sev in sbt.items():
                if tag_prefix not in _ENUM_PREFIXES:
                    issues.append(
                        f"L{lineno}: {name} `severity_by_tag` key {tag_prefix!r} is not "
                        f"in the 8-value enum ({', '.join(sorted(_ENUM_PREFIXES))})"
                    )
                _check_severity_breakdown(
                    sev, f"severity_by_tag.{tag_prefix}", name, lineno, issues
                )


def _validate_reconcile_failed(
    evt: dict[str, Any], lineno: int, issues: list[str]
) -> None:
    name = "reconcile_failed"
    if "reason" not in evt:
        issues.append(f"L{lineno}: {name} missing required field `reason`")
        return
    valid_reasons = {
        "post_delivery_schema_invalid", "queue_write_failed",
        "events_write_failed", "contradiction_with_business", "other",
    }
    if evt["reason"] not in valid_reasons:
        issues.append(
            f"L{lineno}: {name} `reason` {evt['reason']!r} is not in the valid set "
            f"({', '.join(sorted(valid_reasons))})"
        )


def _validate_epic_block(
    evt: dict[str, Any], lineno: int, issues: list[str]
) -> None:
    name = "epic_block"
    for field in ("source", "deviation_tag", "summary", "blocked_until"):
        if field not in evt:
            issues.append(f"L{lineno}: {name} missing required field `{field}`")
    valid_sources = {"bmad-correct-course", "kiat-team-lead", "tech-spec-writer"}
    if "source" in evt and evt["source"] not in valid_sources:
        issues.append(
            f"L{lineno}: {name} `source` {evt['source']!r} not in "
            f"({', '.join(sorted(valid_sources))})"
        )


def _validate_epic_unblock(
    evt: dict[str, Any], lineno: int, issues: list[str]
) -> None:
    name = "epic_unblock"
    if "blocks_cleared" not in evt:
        issues.append(f"L{lineno}: {name} missing required field `blocks_cleared`")
    elif not isinstance(evt["blocks_cleared"], list):
        issues.append(
            f"L{lineno}: {name} `blocks_cleared` should be a list, "
            f"got {type(evt['blocks_cleared']).__name__}"
        )
    if "resolution" not in evt:
        issues.append(f"L{lineno}: {name} missing required field `resolution`")


def _validate_queue_supersede(
    evt: dict[str, Any], lineno: int, issues: list[str]
) -> None:
    name = "queue_supersede"
    for field in ("queue_id", "deviation_tag", "summary", "source"):
        if field not in evt:
            issues.append(f"L{lineno}: {name} missing required field `{field}`")
    if "source" in evt and evt["source"] != "kiat-team-lead":
        issues.append(
            f"L{lineno}: {name} `source` must be 'kiat-team-lead' "
            f"(Phase 0c is the only writer), got {evt['source']!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiat health report generator")
    parser.add_argument(
        "--events",
        default=str(DEFAULT_EVENTS_PATH),
        help=f"Path to events.jsonl (default: {DEFAULT_EVENTS_PATH})",
    )
    parser.add_argument(
        "--scope",
        default="active",
        choices=["active", "all-time"],
        help=(
            "active (default): read events.jsonl only. "
            "all-time: also read events.archive-2026-05-16.jsonl, "
            "normalizing legacy events to v2 shape in-memory."
        ),
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Filter events on/after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--epic",
        default=None,
        help="Filter to a single epic (e.g. epic-3)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write report to file instead of stdout",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the events file against the v2 schema. Exits 0 if clean, 1 if issues found. Prints issue list to stderr.",
    )
    args = parser.parse_args()

    since_dt = None
    if args.since:
        try:
            since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Error: --since must be YYYY-MM-DD, got {args.since!r}", file=sys.stderr)
            return 2

    events_path = Path(args.events)

    # --validate mode: short-circuit the report, just check the file
    if args.validate:
        exit_code, issues = validate_events_file(events_path)
        if exit_code == 0 and not issues:
            print(f"✓ {events_path}: all events conform to v2 schema", file=sys.stderr)
            return 0
        if exit_code == 0 and issues:
            # Informational only (e.g., file doesn't exist yet)
            for issue in issues:
                print(f"  {issue}", file=sys.stderr)
            return 0
        print(f"✗ {events_path}: {len(issues)} issue(s) found", file=sys.stderr)
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        return exit_code

    raw_events = load_events(events_path)

    # --scope all-time: also load the legacy archive, normalizing events in-memory
    if args.scope == "all-time":
        archive_path = events_path.parent / DEFAULT_ARCHIVE_PATH.name
        archive_events = load_events(archive_path)
        normalized = [normalize_legacy_event(e) for e in archive_events]
        raw_events = normalized + raw_events

    filtered = filter_events(raw_events, since=since_dt, epic=args.epic)

    filter_parts = []
    if args.scope == "all-time":
        filter_parts.append("all-time (active + archive)")
    if args.since:
        filter_parts.append(f"since {args.since}")
    if args.epic:
        filter_parts.append(f"epic {args.epic}")
    filter_desc = "Scope: " + (", ".join(filter_parts) if filter_parts else "active (v2 events only)")

    stories = rollup_stories(filtered)
    report = format_report(stories, filter_desc, events=filtered)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
