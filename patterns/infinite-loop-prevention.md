# Pattern: Preventing Infinite Review Loops

**Problem**: Reviewer finds issue → coder fixes → reviewer finds new issue → ... (loop never ends)

**Root cause**: Feedback comes one-at-a-time; coder doesn't see full picture; reviewer doesn't accumulate fixes.

**Solution**: Batch feedback + convergence rules.

---

## The Loop We're Preventing

### ❌ Bad Workflow (Infinite Loop)

```
Round 1:
  Coder: "Code ready for review"
  Reviewer: "Issue 1: RLS policy missing"
  
Round 2:
  Coder: "Fixed issue 1"
  Reviewer: "Issue 2: Test missing"
  
Round 3:
  Coder: "Fixed issue 2"
  Reviewer: "Issue 3: Error message unclear"
  
Round 4:
  ...
  
[No clear endpoint]
```

**Why bad:**
- Tokens wasted in ping-pong
- Coder doesn't learn patterns (sees 1 issue at a time)
- Reviewer is inefficient (partial checks each round)
- Story never converges

---

### ✅ Good Workflow (Convergence Guaranteed)

```
Round 1:
  Coder: "Code ready for review"
  Reviewer: "Found 3 issues: RLS missing, test missing, error unclear"
  
Round 2:
  Coder: [reads ALL feedback] → fixes ALL issues → reruns tests
  Coder: "Ready for second review"
  Reviewer: [quick check] → "Approved ✅"
```

**Why good:**
- Tokens saved (2 rounds vs 4+)
- Coder sees patterns (understands expectations)
- Reviewer is efficient (batches all checks)
- Story converges (done after round 2)

---

## Rule 1: Reviewer Batches All Feedback

### When Reviewer Finds Issues

**Reviewer reads the ENTIRE code submission**, accumulates ALL issues, reports them in ONE message.

**Structure:**
```
## Code Review: story-42

### Database ✓
- [ ] Migration correct
- [ ] RLS policy included

### API ✓
- [ ] Contracts match spec
- [ ] Errors handled

### Testing ✓
- [ ] Venom tests comprehensive
- [ ] RLS tested

---

### Issues Found (3 Total)

**1. RLS Policy Missing** [Blocker]
   Location: migrations/XXX.sql
   Problem: Table has no RLS policy
   Fix: Add RLS policy

**2. Test Coverage** [Major]
   Location: venom/handler_test.go
   Problem: No RLS test
   Fix: Add test that User B can't read User A's data

**3. Error Message** [Minor]
   Location: handler.go
   Problem: "Something went wrong" (too vague)
   Fix: "Name is required (max 255 chars)"
```

**NOT:**
```
❌ Reviewer: "I found an issue: RLS policy missing"
```

---

## Rule 2: Coder Reads ALL Feedback Before Fixing

### When Coder Receives Feedback

**Coder reads the ENTIRE feedback list**, understands ALL issues, fixes them in ONE session.

**Workflow:**
```
Reviewer output: [3 issues: RLS, test, error message]

Coder:
  1. Read all 3 issues (don't start fixing yet)
  2. Understand each one
  3. Plan fixes for all 3
  4. Implement all 3 fixes in code
  5. Rerun tests (confirm all pass)
  6. Say: "Ready for second review"
```

**NOT:**
```
❌ Coder: "Fixed RLS policy, ready for review again?"
   [submit]
   Reviewer: "Now test is missing"
   ❌ Coder: "Fixed test, ready?"
   [submit]
   Reviewer: "Error message unclear"
   ...
```

---

## Rule 3: Max 2 Review Cycles

### After Coder Submits Fixes

**Reviewer conducts SECOND review**:
- Does code fix issue #1? ✅
- Does code fix issue #2? ✅
- Does code fix issue #3? ✅
- Any NEW issues? ❌

**Outcome:**
- **All fixed, no new issues** → "Approved ✅"
- **Some not fixed** → "Still 2 issues to fix" (very rare, coder should have gotten it right)
- **New issues found** → Escalate to human (not back to coder)

**Why 2 cycles max:**
- First review: Reviewer finds gaps
- Second review: Coder fixes gaps (should be clean)
- If still issues after 2 → story is too ambitious OR spec is bad → human decides what to do

---

## Rule 4: Clear Convergence Gates

### Blocker Issues (Must Fix Before Second Review)

Blocker = Must address. Examples:
- RLS policy missing (security hole)
- Test failing (spec not met)
- Spec not implemented (contract doesn't match)
- Secrets in code (security hole)

**Blocker checklist (reviewer uses this):**
- [ ] Does code match spec?
- [ ] All tests passing?
- [ ] No security issues (RLS, secrets, input validation)?
- [ ] No basic errors (migrations run? handlers wired)?

If ANY blocker fails → report, ask coder to fix.

### Major Issues (Nice to Fix Before Second Review)

Major = Should improve. Examples:
- Error message unclear
- Test missing (but not breaking)
- Performance could be better
- Code could be cleaner

**For major issues:** Reviewer includes them, coder should fix, but not mandatory if too many (escalate instead).

### Minor Issues (Nice to Have)

Minor = Doesn't block. Examples:
- Code style (trailing space)
- Comment clarity
- Variable naming
- Optimization opportunity

**For minor issues:** Reviewer mentions them, coder can fix next time.

---

## Rule 5: Escalation on Non-Convergence

### If After 2 Review Cycles Issues Persist

**Escalate to human** (don't ask coder to resubmit):

```
Reviewer: "Issue 1 (RLS) fixed ✅
          Issue 2 (tests) fixed ✅
          But discovered issue 4: Architecture doesn't support this approach
          
          This needs human decision: Do we split story? Redesign? Accept tech debt?"
```

**Human decides:**
- Approve with tech debt note
- Ask to split story and resubmit part 2 separately
- Ask to redesign (major rework)
- Escalate to architect

---

## Pattern: Reviewer Sees Code + Prior Feedback

### For Second Review

Reviewer gets:
- Original code submission (round 1)
- Original feedback (issues found round 1)
- Code diff from fixes (round 2)

Reviewer checks:
- Is each issue from round 1 actually fixed?
- Are there NEW issues?

**Reviewer prompt template:**
```
## Second Review: story-42

**Original issues found:**
1. RLS policy missing
2. Test missing
3. Error message unclear

**Checking if fixed:**
- Issue 1: ✅ RLS policy added (verified in migration)
- Issue 2: ✅ RLS test added (passing)
- Issue 3: ✅ Error message improved

**Checking for new issues:**
- Code quality: ✅ Clean
- Tests: ✅ All passing
- Security: ✅ No new issues

## Approved ✅
```

---

## Anti-Pattern: Multiple Submissions

### ❌ What NOT to do

```
Coder gets feedback with 3 issues.

Submission 1: Fixes issue 1 only → "Ready for review?"
Reviewer: "Still issues 2 and 3"

Submission 2: Fixes issue 2 only → "Ready for review?"
Reviewer: "Still issue 3"

Submission 3: Fixes issue 3 → "Ready for review?"
Reviewer: "Approved ✅"

[4 submissions total, 4 rounds of context, massive token waste]
```

---

## Anti-Pattern: Reviewer Incrementalism

### ❌ What NOT to do

```
Reviewer finds issue 1 → Reports it → Waits for coder

Coder fixes issue 1 → Submits → Reviewer reviews

Reviewer finds issue 2 (should have found in first review!) → Reports

[Reviewer didn't batch check, now reviewing multiple times]
```

---

## Checklist: Avoiding Loops

### For Coder:
- [ ] Read ENTIRE feedback list before starting fixes
- [ ] Fix ALL issues in one session (not multiple submissions)
- [ ] Rerun tests before saying "Ready for review"
- [ ] If feedback unclear, ask coder in chat (don't guess)

### For Reviewer:
- [ ] Do first review of entire code (not partial)
- [ ] List ALL issues in one message (not multiple messages)
- [ ] Do second review only to verify fixes (not to find new issues)
- [ ] If more issues found in round 2 → Escalate (don't ask coder to resubmit)

### For Human:
- [ ] Approve when code is ready (after round 1 or round 2)
- [ ] Escalate if loop breaks (issues persist after round 2)
- [ ] Decide: split story? redesign? accept tech debt?

---

## Real-World Example

### Story 42: Webhook Handler

**Round 1: Code Review**

Reviewer reads entire code (all files), checks against spec and checklist.

```
## Code Review: story-42

✅ Spec compliance: Code matches spec
✅ Tests: Venom tests passing
❌ RLS: Policy missing
❌ Errors: Generic "Something went wrong"
⚠️ Logging: Could include more detail

## Issues Found (2 Blockers)

**1. Blocker: RLS policy missing**
   File: migrations/025.sql
   Problem: Table created without RLS policy
   Fix: Add RLS policy that checks user access
   
**2. Blocker: Error message**
   File: handler.go, line 45
   Problem: "Something went wrong" (doesn't help user)
   Fix: "Webhook signature invalid" or appropriate error

## Minor Observations
- Logging could include webhook_id for debugging
```

**Coder reads feedback:**
- Issue 1: Understand what RLS means, fix migration
- Issue 2: Understand error should be specific, update handler
- Minor: Consider adding webhook_id to logs

**Round 2: Coder Fixes**

Coder makes BOTH fixes (RLS + error message) and logs.

```bash
git diff story-42
  - migrations/025.sql: Added RLS policy
  - handler.go: Updated error message to "Webhook signature invalid"
  - handler.go: Added webhook_id to logs
```

Coder runs tests:
```bash
make test-back
✅ All 5 tests pass (including RLS test)
```

**Round 2: Second Review**

Reviewer verifies:
- Issue 1 fixed? ✅ RLS policy in migration, RLS test added
- Issue 2 fixed? ✅ Error message specific now
- New issues? ❌ No

```
## Approved ✅

Issue 1: Fixed (RLS policy added, test verifies)
Issue 2: Fixed (error message specific)
No new issues found.

Ready for merge.
```

---

## Summary

| What | Who | When | Result |
|------|-----|------|--------|
| **Batch feedback** | Reviewer | Round 1 | All issues visible at once |
| **Fix all at once** | Coder | Round 2 prep | All fixes in one submission |
| **Verify fixes** | Reviewer | Round 2 | Check each fix, no new issues |
| **Approve or escalate** | Reviewer | End of round 2 | "Approved" or "Human decision needed" |

**Convergence guaranteed in 2 rounds max.**

---

**Next**: Read `test-gate-automation.md` to understand how tests are run and who fixes failures.
