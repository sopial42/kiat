#!/bin/bash
# SubagentStop hook for kiat-frontend-coder / kiat-backend-coder.
#
# Two-pronged gate (catches both failure modes that shipped silently
# during epic-02):
#
#   1. SKIP-FROM-START — coder authored new spec files wrapped in
#      `test.describe.skip(...)` or `test.skip('name', ...)` from
#      the get-go (the pattern that put 5 search-journey specs in
#      cold storage during epic-02 stories 01-06). Catches by
#      grepping the diff vs main for *.spec.ts and *.venom.yml files
#      then matching the hard-skip patterns.
#
#   2. NEVER-RAN — coder added or modified specs but the session
#      transcript shows ZERO `make test-e2e` / `make test-venom` /
#      `npx playwright test` / `go test` invocations. The audit
#      line `E2E test execution:` / `Venom test execution:` is also
#      checked — both must be present when the diff includes spec
#      files. This catches the coder who ships a spec without ever
#      running it.
#
# Both checks fire at coder SubagentStop. The reviewer-side gates
# (Step 6.5 / 6.7 in the reviewer agents) remain in place — this
# hook is defense in depth, not a replacement.
#
# Allowed exceptions (so the hook is not a chainsaw):
#   - Pre-existing skipped specs already on main are NOT flagged.
#     Only NEW skips in the session diff are caught.
#   - Conditional skips like `test.skip(condition, 'reason')` (where
#     the first arg is NOT a string literal or `true`) are allowed.
#
# Hook input: JSON via stdin with `transcript_path` and `cwd`.
# Exit 0 = pass. Exit 2 = block, stderr is shown to the model.

set -euo pipefail

INPUT="$(cat)"

if command -v jq >/dev/null 2>&1; then
  # SubagentStop sends BOTH `transcript_path` (parent session) AND
  # `agent_transcript_path` (the sub-agent's own .jsonl). The parent
  # transcript does NOT see the sub-agent's bash tool invocations,
  # so reading `transcript_path` for a SubagentStop event yields
  # spurious NEVER-RAN / MISSING-AUDIT violations even when the
  # sub-agent ran the suite and emitted the audit lines correctly.
  # Prefer `agent_transcript_path` when present; fall back to
  # `transcript_path` for non-sub-agent Stop events.
  TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.agent_transcript_path // .transcript_path // .transcriptPath // empty')"
  CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
else
  # jq-less fallback: same precedence as the jq branch above.
  TRANSCRIPT="$(printf '%s' "$INPUT" | grep -oE '"agent_transcript_path"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/')"
  if [[ -z "$TRANSCRIPT" ]]; then
    TRANSCRIPT="$(printf '%s' "$INPUT" | grep -oE '"transcript_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/')"
  fi
  CWD=""
fi

if [[ -n "$CWD" ]] && [[ -d "$CWD" ]]; then
  cd "$CWD"
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# Discover the merge-base. Fall back gracefully on detached / fresh repos.
BASE=""
if git rev-parse --verify --quiet main >/dev/null 2>&1; then
  BASE="main"
elif git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
  BASE="origin/main"
elif git rev-parse --verify --quiet "HEAD~1" >/dev/null 2>&1; then
  BASE="HEAD~1"
fi

if [[ -z "$BASE" ]]; then
  exit 0
fi

# Spec files added or modified vs base (committed + uncommitted + untracked).
TRACKED="$(git diff --name-only "$BASE"...HEAD 2>/dev/null | grep -E '\.(spec|test)\.(ts|tsx|js|jsx)$|\.venom\.ya?ml$' || true)"
UNCOMMITTED="$(git diff --name-only HEAD 2>/dev/null | grep -E '\.(spec|test)\.(ts|tsx|js|jsx)$|\.venom\.ya?ml$' || true)"
UNTRACKED="$(git ls-files --others --exclude-standard 2>/dev/null | grep -E '\.(spec|test)\.(ts|tsx|js|jsx)$|\.venom\.ya?ml$' || true)"

ALL_SPEC_FILES="$(printf '%s\n%s\n%s\n' "$TRACKED" "$UNCOMMITTED" "$UNTRACKED" | sed '/^$/d' | sort -u)"

# Parallel-coder filter: when the backend coder and the frontend coder
# run on the SAME working tree (epic-05 story-04 scenario, Q-049), each
# coder's diff sees the other's spec changes. Without filtering, the
# backend coder is wrongly gated on `.spec.ts` files authored by the
# parallel frontend coder (and symmetrically). Heuristic: a spec file
# in the diff that was NEVER mentioned in this session's transcript
# (no Edit / Write / Bash call referencing its path) is a parallel-coder
# artifact, not this coder's responsibility — exclude it from the gate.
# If the transcript is unavailable (early-session failure / non-jq env),
# fail-safe by keeping all files in the gate.
if [[ -n "${TRANSCRIPT:-}" ]] && [[ -f "$TRANSCRIPT" ]]; then
  FILTERED_SPEC_FILES=""
  EXCLUDED_SPEC_FILES=""
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    # File path must literally appear in the transcript (any tool call
    # that touched it leaves the path verbatim — Edit/Write `file_path`,
    # Bash `cat`/`grep`/`make`, Playwright runner output).
    if grep -qF "$f" "$TRANSCRIPT" 2>/dev/null; then
      FILTERED_SPEC_FILES+="$f"$'\n'
    else
      EXCLUDED_SPEC_FILES+="$f"$'\n'
    fi
  done <<< "$ALL_SPEC_FILES"
  ALL_SPEC_FILES="$(printf '%s' "$FILTERED_SPEC_FILES" | sed '/^$/d' | sort -u)"
fi

# If the diff has no spec files at all (or none touched by this session
# after the parallel-coder filter), nothing to gate — exit clean.
if [[ -z "$ALL_SPEC_FILES" ]]; then
  exit 0
fi

# Split into Playwright vs Venom for tailored error messages.
PLAYWRIGHT_FILES=()
VENOM_FILES=()
while IFS= read -r f; do
  case "$f" in
    *.spec.ts|*.spec.tsx|*.spec.js|*.spec.jsx|*.test.ts|*.test.tsx|*.test.js|*.test.jsx)
      PLAYWRIGHT_FILES+=("$f") ;;
    *.venom.yml|*.venom.yaml)
      VENOM_FILES+=("$f") ;;
  esac
done <<< "$ALL_SPEC_FILES"

VIOLATIONS=()

# ── Check 1: hard-skip patterns in newly added/modified spec files ──
#
# We match ANY identifier (or chained identifiers) at module level —
# `^[[:space:]]{0,2}<id>(\.<id>)*\.(skip|fixme)\s*\(` — so the regex
# catches the Playwright canonical `test.skip('name', ...)` / `test.
# describe.skip('name', ...)` AND fixture-extended forms common in this
# project: `stateRef.skip(...)`, `stateRef.fixme(...)`, etc.
#
# `^` (column 0, no leading whitespace) means we ONLY catch
# module-level skips — the conditional `test.skip(condition, 'reason')`
# pattern called inside a test body is always indented (function body)
# and is correctly NOT matched. That branch is the legitimate use-case
# for `test.skip` (e.g. environment-gated test).
#
# We deliberately do NOT require a string-literal first arg because
# the offending forms in this codebase span multiple lines:
#   stateRef.fixme(
#     'name on next line',
#     async ({ page }) => { ... },
#   );
# and a single-line regex would miss them. The module-level anchor
# carries the discrimination instead.
SKIP_PATTERNS='^[a-zA-Z_$][a-zA-Z0-9_$]*(\.[a-zA-Z_$][a-zA-Z0-9_$]*)*\.(skip|fixme)[[:space:]]*\('

for f in "${PLAYWRIGHT_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then continue; fi
  MATCHES="$(grep -nE "$SKIP_PATTERNS" "$f" 2>/dev/null || true)"
  if [[ -n "$MATCHES" ]]; then
    while IFS= read -r line; do
      VIOLATIONS+=("[SKIP-FROM-START] $f:$line")
    done <<< "$MATCHES"
  fi
done

# ── Check 2: did the coder actually run the tests? ──
# Inspect the transcript for evidence of execution.
HAS_PLAYWRIGHT_RUN=0
HAS_VENOM_RUN=0
HAS_PLAYWRIGHT_AUDIT_LINE=0
HAS_VENOM_AUDIT_LINE=0

if [[ -n "${TRANSCRIPT:-}" ]] && [[ -f "$TRANSCRIPT" ]]; then
  if grep -qE '(make test-e2e|npx playwright test|npm run test:e2e)' "$TRANSCRIPT"; then
    HAS_PLAYWRIGHT_RUN=1
  fi
  if grep -qE '(make test-venom|venom run)' "$TRANSCRIPT"; then
    HAS_VENOM_RUN=1
  fi
  if grep -q 'E2E test execution:' "$TRANSCRIPT"; then
    HAS_PLAYWRIGHT_AUDIT_LINE=1
  fi
  if grep -q 'Venom test execution:' "$TRANSCRIPT"; then
    HAS_VENOM_AUDIT_LINE=1
  fi
fi

if [[ ${#PLAYWRIGHT_FILES[@]} -gt 0 ]]; then
  if [[ $HAS_PLAYWRIGHT_RUN -eq 0 ]]; then
    VIOLATIONS+=("[NEVER-RAN] Playwright spec(s) modified but transcript shows NO 'make test-e2e' / 'npx playwright test' / 'npm run test:e2e' invocation.")
  fi
  if [[ $HAS_PLAYWRIGHT_AUDIT_LINE -eq 0 ]]; then
    VIOLATIONS+=("[MISSING-AUDIT] Playwright spec(s) modified but the handoff has no 'E2E test execution:' verbatim summary line.")
  fi
fi

if [[ ${#VENOM_FILES[@]} -gt 0 ]]; then
  if [[ $HAS_VENOM_RUN -eq 0 ]]; then
    VIOLATIONS+=("[NEVER-RAN] Venom YAML(s) modified but transcript shows NO 'make test-venom' / 'venom run' invocation.")
  fi
  if [[ $HAS_VENOM_AUDIT_LINE -eq 0 ]]; then
    VIOLATIONS+=("[MISSING-AUDIT] Venom YAML(s) modified but the handoff has no 'Venom test execution:' verbatim summary line.")
  fi
fi

if [[ ${#VIOLATIONS[@]} -eq 0 ]]; then
  exit 0
fi

{
  echo "PROTOCOL VIOLATION: E2E / Venom test gate at coder SubagentStop"
  echo ""
  echo "The session diff includes test specifications, and one or more"
  echo "of the mandatory checks below failed. The coder cannot hand off"
  echo "to Team Lead until each violation below is resolved."
  echo ""
  echo "Modified spec files in this session's diff:"
  for f in "${PLAYWRIGHT_FILES[@]}"; do echo "  - $f"; done
  for f in "${VENOM_FILES[@]}"; do echo "  - $f"; done
  echo ""
  echo "Violations:"
  for v in "${VIOLATIONS[@]}"; do
    echo "  $v"
  done
  echo ""
  echo "Resolution:"
  echo "  [SKIP-FROM-START]   Make the test pass, OR delete the spec entirely."
  echo "                      'Wrapping in test.describe.skip with a TODO' is"
  echo "                      the exact pattern that shipped a 401 bug in"
  echo "                      epic-02 useSearchStatus. There is no third option."
  echo ""
  echo "  [NEVER-RAN]         Run the full suite from the repo root:"
  echo "                        Frontend → make test-e2e"
  echo "                        Backend  → make test-venom"
  echo "                      Do NOT cherry-pick a single spec; the full suite"
  echo "                      catches integration regressions a single-spec"
  echo "                      run won't see."
  echo ""
  echo "  [MISSING-AUDIT]     Add the verbatim Playwright / Venom summary line"
  echo "                      in your handoff message. Reviewer Step 6.5 / 6.7"
  echo "                      parses this line; without it the reviewer also"
  echo "                      blocks. Format:"
  echo "                        E2E test execution:  ✅ make test-e2e — N passed (Mm Ss)"
  echo "                        Venom test execution: ✅ make test-venom — N suites ok, 0 KO"
  echo ""
  echo "References:"
  echo "  .claude/agents/kiat-frontend-coder.md Step 5 (HARD GATE — green E2E)"
  echo "  .claude/agents/kiat-backend-coder.md  Step 5 (HARD GATE — green Venom)"
  echo "  .claude/agents/kiat-frontend-reviewer.md Step 6.5 (audit-line parser)"
  echo "  .claude/agents/kiat-backend-reviewer.md  Step 6.5 (audit-line parser)"
} >&2

exit 2
