#!/bin/bash
# SubagentStop hook for kiat-team-lead.
#
# Validates the schema of the `## Deviations` section in any
# story-NN-<slug>.reconcile.md companion file Team Lead created or
# modified during this run. Triggered after Team Lead's Phase 5c.
#
# The reconciliation pipeline downstream (/bmad-correct-course,
# scope-overlap checks at Team Lead Phase 0c, /bmad-retrospective) all
# assume the schema defined in:
#   .claude/specs/reconciliation-protocol.md
#
# A populated `## Deviations` section MUST contain a
#   `<!-- POST_DELIVERY_BLOCK_BEGIN -->` ...
#   `<!-- POST_DELIVERY_BLOCK_END -->`
# pair, with at least one bullet between them, and every bullet
# carrying the required fields:
#   Tag, Severity, Summary, File, SpecRef, Status, Why.
#
# Note: stories that ship as specified do NOT get a `.reconcile.md`
# (Phase 5c does not create one when all coders reported NONE), so
# this hook only fires when there is something to validate.
#
# Hook input: JSON via stdin with `transcript_path` to the session transcript.
# Exit 0 = pass. Exit 2 = block, stderr shown to the model.

set -euo pipefail

INPUT="$(cat)"

# Extract transcript path
if command -v jq >/dev/null 2>&1; then
  TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // .transcriptPath // empty')"
else
  TRANSCRIPT="$(printf '%s' "$INPUT" | grep -oE '"transcript_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/')"
fi

if [[ -z "${TRANSCRIPT:-}" ]] || [[ ! -f "$TRANSCRIPT" ]]; then
  exit 0
fi

# Find every .reconcile.md companion file Team Lead wrote/edited during
# this session. We grep the transcript for tool-use calls that touched
# any story-NN-<slug>.reconcile.md (excluding _epic.reconcile.md, which
# is /bmad-retrospective's territory, not Team Lead's).
RECONCILE_FILES="$(grep -oE 'delivery/epics/epic-[^/]+/story-[0-9]+[A-Za-z0-9_-]*\.reconcile\.md' "$TRANSCRIPT" 2>/dev/null \
  | sort -u || true)"

if [[ -z "$RECONCILE_FILES" ]]; then
  # Team Lead didn't touch a .reconcile.md this run — nothing to validate.
  # (Common case: all coders reported NONE, so no companion file was created.)
  exit 0
fi

VIOLATIONS=()

# Validate one .reconcile.md companion file's ## Deviations section.
# Uses awk to walk through bullets multi-line and check required fields per bullet.
# Appends to global VIOLATIONS array on issues.
validate_reconcile() {
  local recon="$1"

  if [[ ! -f "$recon" ]]; then
    return
  fi

  # Extract the ## Deviations section (between `## Deviations`
  # and the next `^## ` heading or EOF).
  local section
  section="$(awk '
    /^## Deviations/ { capture=1; next }
    capture && /^## / { exit }
    capture { print }
  ' "$recon")"

  if [[ -z "$section" ]]; then
    # File has no ## Deviations section at all — protocol violation.
    VIOLATIONS+=("$recon: missing ## Deviations section — Phase 5c MUST populate it before /bmad-correct-course can run")
    return
  fi

  # Must have BEGIN/END markers with content between.
  if ! echo "$section" | grep -q 'POST_DELIVERY_BLOCK_BEGIN'; then
    VIOLATIONS+=("$recon: ## Deviations section missing <!-- POST_DELIVERY_BLOCK_BEGIN --> marker")
    return
  fi
  if ! echo "$section" | grep -q 'POST_DELIVERY_BLOCK_END'; then
    VIOLATIONS+=("$recon: ## Deviations section has BEGIN marker but missing <!-- POST_DELIVERY_BLOCK_END --> marker")
    return
  fi

  # Extract content between markers
  local block
  block="$(echo "$section" | awk '
    /POST_DELIVERY_BLOCK_BEGIN/ { capture=1; next }
    /POST_DELIVERY_BLOCK_END/   { capture=0; next }
    capture { print }
  ')"

  if [[ -z "$(echo "$block" | tr -d '[:space:]')" ]]; then
    VIOLATIONS+=("$recon: BEGIN/END markers in ## Deviations are empty — a .reconcile.md should not exist when there are no deviations")
    return
  fi

  # Check whether the block contains any actual bullets matching the schema.
  local bullet_count
  bullet_count="$(echo "$block" | grep -cE '^- \*\*Tag\*\*:' || true)"

  if [[ "$bullet_count" -eq 0 ]]; then
    # No schema bullets found. Allow if every sub-section explicitly says _(none)_,
    # otherwise reject.
    if echo "$block" | grep -qvE '^[[:space:]]*$|^### |_\(none\)_'; then
      VIOLATIONS+=("$recon: BEGIN/END block in ## Deviations contains content but no bullet matches the schema (\`- **Tag**: ...\`)")
    fi
    return
  fi

  # Parse each bullet as a multi-line chunk, validate fields per bullet.
  # awk emits one block per bullet, separated by a record-delimiter line `<<<EOR>>>`.
  local chunks
  chunks="$(echo "$block" | awk '
    /^- \*\*Tag\*\*:/ {
      if (NR > 1 && have_chunk) print "<<<EOR>>>"
      have_chunk = 1
    }
    have_chunk { print }
    END { if (have_chunk) print "<<<EOR>>>" }
  ')"

  # Iterate chunks (separated by <<<EOR>>>)
  local current_chunk=""
  local chunk_idx=0
  local required_fields=("Tag" "Severity" "Summary" "File" "SpecRef" "Status" "Why")

  while IFS= read -r line; do
    if [[ "$line" == "<<<EOR>>>" ]]; then
      chunk_idx=$((chunk_idx + 1))
      # Validate the accumulated chunk
      for field in "${required_fields[@]}"; do
        if ! echo "$current_chunk" | grep -qE "\*\*${field}\*\*:"; then
          VIOLATIONS+=("$recon bullet #$chunk_idx: missing required field **${field}**")
        fi
      done

      if echo "$current_chunk" | grep -qE '\*\*Severity\*\*:'; then
        if ! echo "$current_chunk" | grep -qE '\*\*Severity\*\*:[[:space:]]*L[123]([[:space:]]|$|\|)'; then
          VIOLATIONS+=("$recon bullet #$chunk_idx: **Severity** must be L1, L2, or L3")
        fi
      fi

      if echo "$current_chunk" | grep -qE '\*\*Status\*\*:'; then
        if ! echo "$current_chunk" | grep -qE '\*\*Status\*\*:[[:space:]]*(RESOLVED|NEEDS_PROMOTION|BLOCKING)'; then
          VIOLATIONS+=("$recon bullet #$chunk_idx: **Status** must be RESOLVED, NEEDS_PROMOTION, or BLOCKING")
        fi
      fi

      current_chunk=""
    else
      current_chunk="${current_chunk}${line}"$'\n'
    fi
  done <<< "$chunks"
}

for RECON in $RECONCILE_FILES; do
  validate_reconcile "$RECON"
done

if [[ ${#VIOLATIONS[@]} -eq 0 ]]; then
  exit 0
fi

cat >&2 <<MSG
PROTOCOL VIOLATION: \`## Deviations\` schema check failed in one or more
\`.reconcile.md\` companion files.

Schema authoritative source:
  .claude/specs/reconciliation-protocol.md

Violations found:
$(for V in "${VIOLATIONS[@]}"; do echo "  - $V"; done)

The \`## Deviations\` section in a \`.reconcile.md\` MUST contain:

     <!-- POST_DELIVERY_BLOCK_BEGIN -->
     ### Backend deviations
     - **Tag**: AC-N | **Severity**: L1
       **Summary**: <one line>
       **File**: <path:line>
       **SpecRef**: <story-NN.md:line or "none">
       **Status**: RESOLVED | NEEDS_PROMOTION | BLOCKING
       **Why**: <one or two sentences>

     ### Frontend deviations
     - _(none)_
     <!-- POST_DELIVERY_BLOCK_END -->

Note: a \`.reconcile.md\` should NOT exist when there are no
deviations — Phase 5c only creates the file when at least one coder
reported a deviation. If your file's BEGIN/END block is empty, delete
the entire \`.reconcile.md\` file instead.

Fix the section in the file(s) above and re-run.
MSG
exit 2
