#!/usr/bin/env bash
# install-claude-skills.sh — install external Claude Code skills at pinned versions.
#
# Reads skills-lock.json at the repo root and, for each entry, fetches the
# pinned commit SHA from the source repo, copies the declared subpath into
# .claude/skills/<name>/, and verifies the SHA-256 directory hash.
#
# Modes:
#   (default)    install missing skills, verify present ones, write back any
#                missing computedHash to the lock file (first-install bootstrap)
#   --check      verify only — fail on missing skill or hash mismatch (CI mode)
#   --force      reinstall every skill, overwriting existing dirs
#
# Lock file schema (skills-lock.json):
#   {
#     "version": 1,
#     "skills": {
#       "<name>": {
#         "source":       "<owner>/<repo>",          # GitHub slug
#         "sourceType":   "github",                   # only "github" supported today
#         "ref":          "<full-40-char-sha>",       # pinned commit SHA
#         "path":         "<subpath/in/repo>",        # what to copy into .claude/skills/<name>/
#                                                    #   (omit or "." to copy the whole repo)
#         "computedHash": "<sha256 of installed dir>" # filled after first install
#       }
#     }
#   }
#
# Dependencies: bash, git, jq, shasum (or sha256sum), find, sort, awk.
# Tested on macOS (Darwin) and Ubuntu CI.

set -euo pipefail

# ── Resolve repo root (script lives at .claude/tools/) ───────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOCK_FILE="${REPO_ROOT}/skills-lock.json"
SKILLS_DIR="${REPO_ROOT}/.claude/skills"
CACHE_DIR="${REPO_ROOT}/.claude/.skills-cache"

# ── Parse mode ───────────────────────────────────────────────────────────────
MODE="install"
case "${1:-}" in
  --check) MODE="check" ;;
  --force) MODE="force" ;;
  "")      MODE="install" ;;
  *)       echo "Usage: $0 [--check|--force]" >&2; exit 2 ;;
esac

# ── Dependency checks ────────────────────────────────────────────────────────
command -v jq   >/dev/null 2>&1 || { echo "ERROR: jq is required (brew install jq / apt install jq)" >&2; exit 1; }
command -v git  >/dev/null 2>&1 || { echo "ERROR: git is required" >&2; exit 1; }
if command -v shasum >/dev/null 2>&1; then
  SHA256="shasum -a 256"
elif command -v sha256sum >/dev/null 2>&1; then
  SHA256="sha256sum"
else
  echo "ERROR: shasum or sha256sum is required" >&2; exit 1
fi
[[ -f "${LOCK_FILE}" ]] || { echo "ERROR: ${LOCK_FILE} not found" >&2; exit 1; }

mkdir -p "${SKILLS_DIR}" "${CACHE_DIR}"

# ── Helpers ──────────────────────────────────────────────────────────────────

# compute_hash <dir> → sha256 of sorted file hashes (deterministic, ignores ctime/order)
compute_hash() {
  local dir="$1"
  ( cd "${dir}" && find . -type f -not -path './.git/*' -print0 \
      | LC_ALL=C sort -z \
      | xargs -0 ${SHA256} \
      | ${SHA256} \
      | awk '{print $1}'
  )
}

# fetch_at_ref <source-slug> <sha> → echoes the cache dir path
fetch_at_ref() {
  local source="$1" ref="$2"
  local cache="${CACHE_DIR}/${source//\//__}"
  if [[ -d "${cache}/.git" ]]; then
    ( cd "${cache}" \
      && git fetch --depth 1 origin "${ref}" >/dev/null 2>&1 \
      && git checkout --quiet "${ref}" )
  else
    rm -rf "${cache}"
    git init --quiet "${cache}"
    ( cd "${cache}" \
      && git remote add origin "https://github.com/${source}.git" \
      && git fetch --depth 1 origin "${ref}" >/dev/null 2>&1 \
      && git checkout --quiet FETCH_HEAD )
  fi
  echo "${cache}"
}

# install_skill <name>
install_skill() {
  local name="$1"
  local entry; entry="$(jq -r --arg n "${name}" '.skills[$n]' "${LOCK_FILE}")"
  local source ref path source_type expected_hash
  source="$(jq -r '.source // empty'       <<<"${entry}")"
  source_type="$(jq -r '.sourceType // empty' <<<"${entry}")"
  ref="$(jq -r '.ref // empty'              <<<"${entry}")"
  path="$(jq -r '.path // "."'              <<<"${entry}")"
  expected_hash="$(jq -r '.computedHash // empty' <<<"${entry}")"

  local target="${SKILLS_DIR}/${name}"

  # Pending entries (no ref pinned yet) — skip with a clear notice.
  if [[ -z "${ref}" || "${ref}" == "null" ]]; then
    printf "  %-32s ⏸  pending (no ref pinned in skills-lock.json)\n" "${name}"
    return 0
  fi

  if [[ "${source_type}" != "github" ]]; then
    printf "  %-32s ✗ unsupported sourceType '%s' (only 'github')\n" "${name}" "${source_type}" >&2
    return 1
  fi

  # Check mode: fail loudly if the skill is missing or hash mismatches.
  if [[ "${MODE}" == "check" ]]; then
    if [[ ! -d "${target}" ]]; then
      printf "  %-32s ✗ MISSING (run: make install-claude-skills)\n" "${name}" >&2
      return 1
    fi
    if [[ -n "${expected_hash}" ]]; then
      local actual; actual="$(compute_hash "${target}")"
      if [[ "${actual}" != "${expected_hash}" ]]; then
        printf "  %-32s ✗ HASH MISMATCH\n      expected: %s\n      actual:   %s\n" \
          "${name}" "${expected_hash}" "${actual}" >&2
        return 1
      fi
      printf "  %-32s ✓ verified (%s)\n" "${name}" "${expected_hash:0:12}"
    else
      printf "  %-32s ⚠  no computedHash in lock — run install once to record it\n" "${name}" >&2
    fi
    return 0
  fi

  # Install or force-reinstall.
  if [[ "${MODE}" != "force" && -d "${target}" ]]; then
    if [[ -n "${expected_hash}" ]]; then
      local actual; actual="$(compute_hash "${target}")"
      if [[ "${actual}" == "${expected_hash}" ]]; then
        printf "  %-32s ✓ already installed (hash matches)\n" "${name}"
        return 0
      else
        printf "  %-32s ⚠  hash drift detected — keeping local copy (use --force to overwrite)\n" "${name}"
        printf "      lock:    %s\n      onDisk:  %s\n" "${expected_hash}" "${actual}"
        return 0
      fi
    else
      printf "  %-32s ✓ present (no lock hash to verify; recording one)\n" "${name}"
      local actual; actual="$(compute_hash "${target}")"
      record_hash "${name}" "${actual}"
      return 0
    fi
  fi

  # Fetch + copy.
  printf "  %-32s ⏳ fetching %s @ %s\n" "${name}" "${source}" "${ref:0:12}"
  local cache; cache="$(fetch_at_ref "${source}" "${ref}")"
  local src_path="${cache}/${path}"
  if [[ ! -d "${src_path}" ]]; then
    printf "  %-32s ✗ path '%s' not found in %s @ %s\n" "${name}" "${path}" "${source}" "${ref:0:12}" >&2
    return 1
  fi

  rm -rf "${target}"
  mkdir -p "${target}"
  # Copy contents (not the dir itself); -a preserves perms; works on macOS + GNU cp.
  ( cd "${src_path}" && tar -cf - . ) | ( cd "${target}" && tar -xf - )

  local actual; actual="$(compute_hash "${target}")"
  if [[ -n "${expected_hash}" && "${actual}" != "${expected_hash}" ]]; then
    printf "  %-32s ✗ HASH MISMATCH after install (supply chain check failed)\n" "${name}" >&2
    printf "      expected: %s\n      actual:   %s\n" "${expected_hash}" "${actual}" >&2
    rm -rf "${target}"
    return 1
  fi
  if [[ -z "${expected_hash}" ]]; then
    record_hash "${name}" "${actual}"
    printf "  %-32s ✓ installed + recorded hash %s\n" "${name}" "${actual:0:12}"
  else
    printf "  %-32s ✓ installed + verified (%s)\n" "${name}" "${actual:0:12}"
  fi
}

# record_hash <name> <hash> — write computedHash back to the lock file
record_hash() {
  local name="$1" hash="$2"
  local tmp; tmp="$(mktemp)"
  jq --arg n "${name}" --arg h "${hash}" \
     '.skills[$n].computedHash = $h' "${LOCK_FILE}" > "${tmp}"
  mv "${tmp}" "${LOCK_FILE}"
}

# ── Main ─────────────────────────────────────────────────────────────────────
echo "Mode: ${MODE} | Lock: ${LOCK_FILE}"
echo

SKILLS=()
while IFS= read -r line; do SKILLS+=("${line}"); done < <(jq -r '.skills | keys[]' "${LOCK_FILE}")
if [[ "${#SKILLS[@]}" -eq 0 ]]; then
  echo "No skills declared in lock file — nothing to do."
  exit 0
fi

FAILED=0
for name in "${SKILLS[@]}"; do
  install_skill "${name}" || FAILED=1
done

echo
if [[ "${FAILED}" -ne 0 ]]; then
  echo "✗ One or more skills failed."
  exit 1
fi
echo "✓ All skills processed."
