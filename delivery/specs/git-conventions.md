# Git Conventions

Project-level rules for branching, commits, and history management.

---

## Branch Names

**Format:** `<type>/story-NN-<slug>`

| Type | Use case |
|---|---|
| `feature/` | New functionality from a story |
| `fix/` | Bug fix |
| `refactor/` | Internal refactor with no behavior change |
| `docs/` | Documentation-only changes |
| `chore/` | Tooling, CI, dependencies |

**Examples:**
- `feature/story-27-item-bulk-import`
- `fix/story-42-null-guard-in-handler`
- `refactor/story-51-extract-auth-middleware`

**Rule:** one story per branch. If you find yourself mixing stories, split the branch.

---

## Commit Messages

**Format:** conventional commits with a short subject + bullet body.

```
<type>: <short subject — what changed, imperative mood>

- Bullet describing the concrete change
- Another bullet for a related change
- Keep bullets focused on WHAT, not WHY (the "why" goes in the PR description)

Fixes #<issue-number>   (if applicable)
```

**Types** (same set as branch types): `feat`, `fix`, `refactor`, `docs`, `chore`.

**Subject rules:**
- Imperative mood ("add item photo upload", not "added item photo upload")
- Under 72 characters
- No trailing period
- Lowercase (except proper nouns)

**Example:**
```
feat: add item photo upload

- Created migration for item_photos table with RLS policy
- Added POST /items/:id/photos with S3 upload
- Added client-side compression (max 2MB per photo)
- Added E2E test covering full upload lifecycle

Fixes #42
```

---

## Commit Immutability Rule

**Commits are immutable once pushed.**

- ❌ Never force-push to shared branches (`main`, `develop`, shared feature branches)
- ❌ Never amend public commits (commits already visible to other developers)
- ❌ Never rewrite history of a shared branch with `rebase -i` after push
- ✅ Create new commits instead ("fixup: <previous commit subject>")
- ✅ Force-push is acceptable only on strictly personal branches that no one else has pulled

**Why:** amending published commits breaks other developers' local history, destroys PR review trails, and erases the audit trail that reviewers and failure-pattern analysis depend on.

**If you absolutely must rewrite history on a shared branch:** discuss with the team first, announce the force-push, and ensure everyone re-fetches before continuing work.

---

## PR Discipline

- **One PR per story.** A story that requires 2 PRs means the story is too large — ask `kiat-tech-spec-writer` to split it at Phase 0.
- **PR description references the story spec.** Include `Story: delivery/epics/epic-X/story-NN-slug.md`.
- **PR body explains the WHY.** The commit body already covers the WHAT. The PR description adds context: what decision led here, what alternatives were considered.
- **No merging with red CI.** See [testing.md](testing.md) "CI Gate" section.
- **No merging without reviewer approval.** See `.claude/agents/kiat-team-lead.md` Phase 4 for the 3-way verdict protocol.

---

## When Pre-commit Hooks Fail

A pre-commit hook failure means **the commit did not happen**. Do NOT:
- Use `--amend` (it would modify the previous commit, which may destroy prior work)
- Use `--no-verify` to bypass the hook (unless explicitly authorized for a specific debugging session)

**Correct flow:** fix the underlying issue, re-stage, create a NEW commit.

---

## Secrets in Git

**Never commit secrets.** This is covered in [security-checklist.md](security-checklist.md). If you commit a secret accidentally:
1. Stop immediately
2. Rotate the secret in its provider (Clerk, AWS, etc.)
3. Discuss with the team before touching git history — removing a committed secret from history is a destructive operation

**Prevention:** use `.env.example` files with placeholder values, and add `.env`, `*.pem`, `credentials.json` etc. to `.gitignore`.
