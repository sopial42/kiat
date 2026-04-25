#!/bin/bash
# SubagentStop hook for kiat-team-lead.
#
# Validates the schema of the `## Post-Delivery Notes` section in any
# story file Team Lead modified during this run. Triggered after Team
# Lead's Phase 5c edits. The reconciliation pipeline downstream
# (bmad-reconcile, scope-overlap checks, retrospective) all assume the
# schema defined in:
#   .claude/specs/reconciliation-protocol.md
#
# Two valid forms of the section:
#   1. Placeholder: contains exactly `_(no deviations)_`. Hook passes.
#   2. Populated: contains a `<!-- POST_DELIVERY_BLOCK_BEGIN -->` ...
#      `<!-- POST_DELIVERY_BLOCK_END -->` pair, with at least one bullet
#      between them, and every bullet carries the required fields:
#      Tag, Severity, Summary, File, SpecRef, Status, Why.
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

# Find every story file Team Lead wrote/edited during this session.
# We grep the transcript for tool-use calls that touched a story file.
# Pattern matches: delivery/epics/epic-N/story-NN-<slug>.md (NOT .reconcile.md)
STORY_FILES="$(grep -oE 'delivery/epics/epic-[^/]+/story-[0-9]+[A-Za-z0-9_-]*\.md' "$TRANSCRIPT" \
  | grep -v '\.reconcile\.md$' \
  | sort -u)"

if [[ -z "$STORY_FILES" ]]; then
  # Team Lead didn't touch a story file this run — nothing to validate
  exit 0
fi

VIOLATIONS=()

# Validate one story file's Post-Delivery Notes section.
# Uses awk to walk through bullets multi-line and check required fields per bullet.
# Appends to global VIOLATIONS array on issues.
validate_story() {
  local story="$1"

  if [[ ! -f "$story" ]]; then
    return
  fi

  # Extract the Post-Delivery Notes section (between `## Post-Delivery Notes`
  # and the next `^## ` heading or EOF).
  local section
  section="$(awk '
    /^## Post-Delivery Notes/ { capture=1; next }
    capture && /^## / { exit }
    capture { print }
  ' "$story")"

  if [[ -z "$section" ]]; then
    # Story has no Post-Delivery Notes section at all — that's a different
    # protocol violation (template missing); flag but don't block here.
    return
  fi

  # Form 1: placeholder
  if echo "$section" | grep -qE '_\(no deviations\)_'; then
    return
  fi

  # Form 2: populated. Must have BEGIN/END markers with content between.
  if ! echo "$section" | grep -q 'POST_DELIVERY_BLOCK_BEGIN'; then
    VIOLATIONS+=("$story: section is populated but missing <!-- POST_DELIVERY_BLOCK_BEGIN --> marker")
    return
  fi
  if ! echo "$section" | grep -q 'POST_DELIVERY_BLOCK_END'; then
    VIOLATIONS+=("$story: section has BEGIN marker but missing <!-- POST_DELIVERY_BLOCK_END --> marker")
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
    VIOLATIONS+=("$story: BEGIN/END markers are empty — use the _(no deviations)_ placeholder instead")
    return
  fi

  # Check whether the block contains any actual bullets matching the schema.
  local bullet_count
  bullet_count="$(echo "$block" | grep -cE '^- \*\*Tag\*\*:' || true)"

  if [[ "$bullet_count" -eq 0 ]]; then
    # No schema bullets found. Allow if every sub-section explicitly says _(none)_,
    # otherwise reject.
    if echo "$block" | grep -qvE '^[[:space:]]*$|^### |_\(none\)_'; then
      VIOLATIONS+=("$story: BEGIN/END block contains content but no bullet matches the schema (\`- **Tag**: ...\`)")
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
          VIOLATIONS+=("$story bullet #$chunk_idx: missing required field **${field}**")
        fi
      done

      if echo "$current_chunk" | grep -qE '\*\*Severity\*\*:'; then
        if ! echo "$current_chunk" | grep -qE '\*\*Severity\*\*:[[:space:]]*L[123]([[:space:]]|$|\|)'; then
          VIOLATIONS+=("$story bullet #$chunk_idx: **Severity** must be L1, L2, or L3")
        fi
      fi

      if echo "$current_chunk" | grep -qE '\*\*Status\*\*:'; then
        if ! echo "$current_chunk" | grep -qE '\*\*Status\*\*:[[:space:]]*(RESOLVED|NEEDS_PROMOTION|BLOCKING)'; then
          VIOLATIONS+=("$story bullet #$chunk_idx: **Status** must be RESOLVED, NEEDS_PROMOTION, or BLOCKING")
        fi
      fi

      current_chunk=""
    else
      current_chunk="${current_chunk}${line}"$'\n'
    fi
  done <<< "$chunks"
}

for STORY in $STORY_FILES; do
  validate_story "$STORY"
done

if [[ ${#VIOLATIONS[@]} -eq 0 ]]; then
  exit 0
fi

cat >&2 <<MSG
PROTOCOL VIOLATION: \`## Post-Delivery Notes\` schema check failed.

Schema authoritative source:
  .claude/specs/reconciliation-protocol.md

Violations found:
$(for V in "${VIOLATIONS[@]}"; do echo "  - $V"; done)

Two valid forms of the section:

  1. Placeholder (no deviations reported by any coder):
     \`_(no deviations)_\`

  2. Populated (one or more deviations):
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

Fix the section in the story file(s) above and re-run.
MSG
exit 2
