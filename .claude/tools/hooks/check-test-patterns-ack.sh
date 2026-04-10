#!/bin/bash
# SubagentStop hook for kiat-backend-coder / kiat-frontend-coder.
#
# Enforces Step 0.5 protocol: coder MUST emit a `TEST_PATTERNS: ACKNOWLEDGED`
# block before handing off. Defense in depth on top of the reviewer check.
#
# Hook input: JSON via stdin with `transcript_path` to the session transcript.
# Exit 0 = pass. Exit 2 = block, stderr shown to the model.

set -euo pipefail

INPUT="$(cat)"

if command -v jq >/dev/null 2>&1; then
  TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // .transcriptPath // empty')"
else
  TRANSCRIPT="$(printf '%s' "$INPUT" | grep -oE '"transcript_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/')"
fi

if [[ -z "${TRANSCRIPT:-}" ]] || [[ ! -f "$TRANSCRIPT" ]]; then
  exit 0
fi

if grep -q 'TEST_PATTERNS: ACKNOWLEDGED' "$TRANSCRIPT"; then
  exit 0
fi

cat >&2 <<'MSG'
PROTOCOL VIOLATION: coder did not emit `TEST_PATTERNS: ACKNOWLEDGED` block.

The kiat-test-patterns-check skill is mandatory at Step 0.5 of the coder
workflow. Its `TEST_PATTERNS: ACKNOWLEDGED` block must appear verbatim in the
handoff, or the reviewer will return VERDICT: BLOCKED.

Re-run the skill before finalizing:
  1. Do the 9-question scope detection on the story spec
  2. Load applicable reference blocks under references/block-*.md
  3. Paste the full ACKNOWLEDGED block into your handoff

See: .claude/skills/kiat-test-patterns-check/SKILL.md
MSG
exit 2
