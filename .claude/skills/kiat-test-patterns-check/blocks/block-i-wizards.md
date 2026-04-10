# Block I — Multi-step Wizards

**Trigger:** any wizard, any step-based UI, any `currentStep` state, any stepper

## Mandatory rules

- Each step persists its data (auto-save per step, or explicit save at step transition — no data loss on navigation).
- **Back button** must restore prior step data exactly as the user left it. If you need to fetch, show a skeleton — don't show empty fields.
- `lastCompletedStep` tracked in the DB for **draft recovery**: if the user closes the browser mid-wizard, reopening lands them at the right step with their data intact.
- E2E test covers the **full workflow**: step 1 → step N → finalization. Not individual step tests in isolation.
- Step transitions MUST NOT lose unsaved data. If auto-save isn't wired up for a particular field, show a "You have unsaved changes" confirmation before allowing navigation away.

## Required acknowledgment (paste verbatim)

> I will persist each step's data, support back navigation, track lastCompletedStep for draft recovery, and write a full-workflow E2E test (step 1 → N → finalization).

## Common drift caught by reviewers

- Back button takes user to prior step but fields are empty — reviewer flags: acknowledged rule required data restoration
- No `lastCompletedStep` tracking — reviewer flags: draft recovery broken (user reopens, lands on step 1 with no data)
- E2E tests each step independently but not the full workflow — reviewer flags: integration bugs between steps slip through
- User navigates back mid-step with unsaved changes and the confirm dialog is missing — reviewer flags: silent data loss
