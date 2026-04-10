#!/bin/bash
# SubagentStop hook for kiat-backend-reviewer / kiat-frontend-reviewer.
#
# Enforces the machine-parseable verdict contract: the reviewer MUST emit
# `VERDICT: APPROVED | NEEDS_DISCUSSION | BLOCKED` as the first non-empty
# line of its final output, so Team Lead can parse it deterministically.
#
# Hook input: JSON via stdin with `transcript_path`. Exit 0 = pass, exit 2 = block.

set -euo pipefail

INPUT="$(cat)"

if command -v jq >/dev/null 2>&1; then
  TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // .transcriptPath // empty')"
else
  TRANSCRIPT="$(printf '%s' "$INPUT" | grep -oE '"transcript_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/')"
fi

if [[ -z "${TRANSCRIPT:-}" ]] || [[ ! -f "$TRANSCRIPT" ]]; then
  # Can't verify — don't block blindly.
  exit 0
fi

# Check the last assistant message in the transcript contains a VERDICT line.
# Transcript is JSONL; each line is a message object. We look for any line that
# has the pattern `VERDICT: APPROVED`, `VERDICT: NEEDS_DISCUSSION`, or
# `VERDICT: BLOCKED`.
if grep -qE 'VERDICT: (APPROVED|NEEDS_DISCUSSION|BLOCKED)' "$TRANSCRIPT"; then
  exit 0
fi

cat >&2 <<'MSG'
PROTOCOL VIOLATION: reviewer did not emit a machine-parseable VERDICT line.

Team Lead parses the first non-empty line of your output deterministically.
It MUST match exactly one of:

  VERDICT: APPROVED
  VERDICT: NEEDS_DISCUSSION
  VERDICT: BLOCKED

Re-run the review skill and emit the verdict line before finalizing.
See: .claude/skills/kiat-review-backend/SKILL.md (or kiat-review-frontend)
MSG
exit 2
