#!/usr/bin/env python3
"""
Kiat doc audit tool.

Measures project convention docs in delivery/specs/ against two metrics:

  M1 — File size (tokens): each doc should be ≤ 8k tokens (bytes/4 estimate).
       Larger docs are unlikely to be fully loaded by agents under budget
       pressure and should be split or trimmed.

  M2 — Structure ratio: each doc should be ≥ 60% structured lines (headers,
       bullets, tables, code blocks) and ≤ 40% prose paragraphs. LLMs recover
       structured content more reliably than prose.

Outputs a markdown health report to stdout or a file.

Usage:
    python3 kiat/.claude/tools/doc-audit.py
    python3 kiat/.claude/tools/doc-audit.py --path delivery/specs/
    python3 kiat/.claude/tools/doc-audit.py --max-tokens 8000
    python3 kiat/.claude/tools/doc-audit.py --min-structure 0.6
    python3 kiat/.claude/tools/doc-audit.py --output doc-audit.md
    python3 kiat/.claude/tools/doc-audit.py --strict   # exit 1 if any doc fails

No external dependencies — stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PATH = "delivery/specs"
DEFAULT_MAX_TOKENS = 8000
DEFAULT_MIN_STRUCTURE_RATIO = 0.60

# Warning zone: 90-100% of budget
WARN_THRESHOLD = 0.90

# Lines considered "structured" (high information density, easy to scan)
STRUCTURED_PATTERNS = [
    re.compile(r"^\s*#{1,6}\s"),          # headers
    re.compile(r"^\s*[-*+]\s"),            # unordered lists
    re.compile(r"^\s*\d+\.\s"),            # ordered lists
    re.compile(r"^\s*\|.*\|"),             # table rows
    re.compile(r"^\s*```"),                # code fences
    re.compile(r"^\s*>\s"),                # blockquotes
    re.compile(r"^\s*---+\s*$"),           # horizontal rules
    re.compile(r"^\s*\[.*\]:\s"),          # reference links
]

# Lines ignored (blank or markdown table separators, neither structure nor prose)
IGNORED_PATTERNS = [
    re.compile(r"^\s*$"),                   # blank
    re.compile(r"^\s*\|?[\s\-:|]*[\-:][\s\-:|]*$"),  # table separator
]


@dataclass
class DocMetrics:
    path: Path
    bytes: int
    estimated_tokens: int
    total_lines: int
    structured_lines: int
    prose_lines: int
    ignored_lines: int
    in_code_block: bool = False  # transient during parse

    @property
    def structure_ratio(self) -> float:
        meaningful = self.structured_lines + self.prose_lines
        if meaningful == 0:
            return 1.0  # vacuously OK
        return self.structured_lines / meaningful

    @property
    def tokens_over_budget(self) -> bool:
        return self.estimated_tokens > self.max_tokens_budget

    @property
    def tokens_in_warning_zone(self) -> bool:
        return (
            not self.tokens_over_budget
            and self.estimated_tokens >= self.max_tokens_budget * WARN_THRESHOLD
        )

    # These are set by the caller (not fields to keep them out of __repr__)
    max_tokens_budget: int = 0
    min_structure_ratio: float = 0.0

    @property
    def structure_ratio_fail(self) -> bool:
        return self.structure_ratio < self.min_structure_ratio

    @property
    def passes(self) -> bool:
        return not self.tokens_over_budget and not self.structure_ratio_fail


def classify_line(line: str, inside_code_block: bool) -> tuple[str, bool]:
    """
    Classify a single line as structured / prose / ignored.

    Tracks code-block state: everything between ``` fences counts as structured.

    Returns (classification, new_inside_code_block).
    """
    # Code fence toggles
    if re.match(r"^\s*```", line):
        # The fence line itself is structured; state flips
        return "structured", not inside_code_block

    # Inside a code block, every line is structured
    if inside_code_block:
        return "structured", inside_code_block

    # Ignored lines (blank, table separators)
    for pat in IGNORED_PATTERNS:
        if pat.match(line):
            return "ignored", inside_code_block

    # Structured lines (headers, bullets, tables, etc.)
    for pat in STRUCTURED_PATTERNS:
        if pat.match(line):
            return "structured", inside_code_block

    # Everything else is prose
    return "prose", inside_code_block


def audit_file(path: Path, max_tokens: int, min_structure: float) -> DocMetrics:
    """Analyze one markdown file and return its metrics."""
    content = path.read_text(encoding="utf-8")
    byte_count = len(content.encode("utf-8"))
    estimated_tokens = byte_count // 4

    lines = content.splitlines()
    metrics = DocMetrics(
        path=path,
        bytes=byte_count,
        estimated_tokens=estimated_tokens,
        total_lines=len(lines),
        structured_lines=0,
        prose_lines=0,
        ignored_lines=0,
        max_tokens_budget=max_tokens,
        min_structure_ratio=min_structure,
    )

    inside_code_block = False
    for line in lines:
        classification, inside_code_block = classify_line(line, inside_code_block)
        if classification == "structured":
            metrics.structured_lines += 1
        elif classification == "prose":
            metrics.prose_lines += 1
        else:
            metrics.ignored_lines += 1

    return metrics


def audit_directory(path: Path, max_tokens: int, min_structure: float) -> list[DocMetrics]:
    """Audit all markdown files in a directory (non-recursive)."""
    if not path.exists():
        print(f"Error: path does not exist: {path}", file=sys.stderr)
        return []
    if not path.is_dir():
        # Single file
        return [audit_file(path, max_tokens, min_structure)]

    results: list[DocMetrics] = []
    for md_file in sorted(path.glob("*.md")):
        results.append(audit_file(md_file, max_tokens, min_structure))
    return results


def format_report(
    metrics_list: list[DocMetrics],
    scanned_path: Path,
    max_tokens: int,
    min_structure: float,
) -> str:
    """Render the markdown audit report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append("# Kiat Doc Audit Report")
    lines.append("")
    lines.append(f"_Generated {now} — scanned `{scanned_path}` ({len(metrics_list)} files)_")
    lines.append("")

    if not metrics_list:
        lines.append("_No markdown files found._")
        lines.append("")
        return "\n".join(lines) + "\n"

    # ---------- Summary ----------
    n = len(metrics_list)
    n_pass = sum(1 for m in metrics_list if m.passes)
    n_token_fail = sum(1 for m in metrics_list if m.tokens_over_budget)
    n_token_warn = sum(1 for m in metrics_list if m.tokens_in_warning_zone)
    n_structure_fail = sum(1 for m in metrics_list if m.structure_ratio_fail)

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total docs scanned:** {n}")
    lines.append(f"- **Passing both metrics:** {n_pass} / {n}")
    lines.append(f"- **M1 failures (over {max_tokens} tokens):** {n_token_fail}")
    lines.append(f"- **M1 warnings (≥ {int(WARN_THRESHOLD * 100)}% of budget):** {n_token_warn}")
    lines.append(f"- **M2 failures (< {int(min_structure * 100)}% structured):** {n_structure_fail}")
    lines.append("")

    # ---------- M1 table ----------
    lines.append(f"## M1 — File Size (Tokens, budget = {max_tokens})")
    lines.append("")
    lines.append("| File | Bytes | Tokens (est) | Status |")
    lines.append("|---|---:|---:|---|")
    for m in sorted(metrics_list, key=lambda x: -x.estimated_tokens):
        if m.tokens_over_budget:
            status = "❌ OVER (split recommended)"
        elif m.tokens_in_warning_zone:
            status = "⚠ close to limit"
        else:
            status = "✓ under"
        lines.append(
            f"| `{m.path.name}` | {m.bytes:,} | ~{m.estimated_tokens:,} | {status} |"
        )
    lines.append("")

    # ---------- M2 table ----------
    lines.append(f"## M2 — Structure Ratio (min = {int(min_structure * 100)}% structured)")
    lines.append("")
    lines.append("| File | Structured | Prose | Ignored | Ratio | Status |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for m in sorted(metrics_list, key=lambda x: x.structure_ratio):
        ratio_pct = int(m.structure_ratio * 100)
        if m.structure_ratio_fail:
            status = "❌ mostly prose (restructure)"
        elif m.structure_ratio < min_structure + 0.1:
            status = "⚠ borderline"
        else:
            status = "✓ well-structured"
        lines.append(
            f"| `{m.path.name}` | {m.structured_lines} | {m.prose_lines} "
            f"| {m.ignored_lines} | {ratio_pct}% | {status} |"
        )
    lines.append("")

    # ---------- Recommendations ----------
    token_fails = [m for m in metrics_list if m.tokens_over_budget]
    structure_fails = [m for m in metrics_list if m.structure_ratio_fail]
    if token_fails or structure_fails:
        lines.append("## Recommendations")
        lines.append("")
        if token_fails:
            lines.append("**Files to split or trim (M1 failures):**")
            for m in token_fails:
                over_by = m.estimated_tokens - max_tokens
                lines.append(
                    f"- `{m.path.name}` — ~{m.estimated_tokens:,} tokens "
                    f"(over by ~{over_by:,}). Consider splitting into 2-3 thematic docs."
                )
            lines.append("")
        if structure_fails:
            lines.append("**Files to restructure (M2 failures):**")
            for m in structure_fails:
                ratio_pct = int(m.structure_ratio * 100)
                lines.append(
                    f"- `{m.path.name}` — {ratio_pct}% structured. "
                    f"Convert prose paragraphs into bullets, tables, or code examples. "
                    f"LLMs retrieve structured content more reliably."
                )
            lines.append("")

    # ---------- Methodology footer ----------
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- **Tokens** estimated as `bytes / 4` (accurate to ±20% for English + code, slightly over-estimates which is the safe direction)."
    )
    lines.append(
        "- **Structured lines** = headers, bullets (`-`, `*`, `+`, numbered), table rows, code blocks (including contents), blockquotes, reference links, horizontal rules."
    )
    lines.append(
        "- **Prose lines** = everything else that's not blank or a table separator."
    )
    lines.append(
        "- **Ignored lines** = blank lines and table separator rows (`|---|---|`). These don't count toward either side of the ratio."
    )
    lines.append("")
    lines.append(
        "**Why these thresholds?** 8k tokens fits comfortably in a 25k coder budget alongside the story spec and ambient docs. 60% structured is an empirical minimum for LLM content retrieval — below this, agents skim and miss rules in prose paragraphs."
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiat doc audit tool")
    parser.add_argument(
        "--path",
        default=DEFAULT_PATH,
        help=f"Directory or file to audit (default: {DEFAULT_PATH})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max tokens per doc (default: {DEFAULT_MAX_TOKENS})",
    )
    parser.add_argument(
        "--min-structure",
        type=float,
        default=DEFAULT_MIN_STRUCTURE_RATIO,
        help=f"Min structured line ratio (default: {DEFAULT_MIN_STRUCTURE_RATIO})",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write report to file instead of stdout",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any doc fails M1 or M2 (useful in CI)",
    )
    args = parser.parse_args()

    scanned_path = Path(args.path)
    metrics_list = audit_directory(scanned_path, args.max_tokens, args.min_structure)

    report = format_report(metrics_list, scanned_path, args.max_tokens, args.min_structure)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(report)

    if args.strict:
        n_fail = sum(1 for m in metrics_list if not m.passes)
        if n_fail > 0:
            print(f"\n✗ {n_fail} doc(s) failed audit (strict mode)", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
