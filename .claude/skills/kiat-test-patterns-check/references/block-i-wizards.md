# Block I — Multi-step wizards

**Trigger:** any wizard, any stepper, any step-based UI, any `currentStep` state.

## Rules and reasons

**Each step persists its data** — either auto-saved as the user types or saved explicitly at step transition. Data must not disappear when the user navigates between steps.

> *Why*: wizard data loss is one of the most frustrating bugs for users. They've filled in 20 fields over 3 steps, clicked "Back" to fix a typo, and everything is gone. Persisting per step is the only way to prevent this class of bug, and the cost is low compared to the user impact.

**The Back button restores prior step data exactly as the user left it.** If the data has to be re-fetched, show a skeleton rather than empty fields.

> *Why*: empty fields after navigating back look like the data was lost. A skeleton clearly communicates "loading" and the user waits instead of panicking and re-filling everything.

**A `lastCompletedStep` (or equivalent) is tracked in the DB for draft recovery.** If the user closes the browser mid-wizard, reopening should land them at the right step with their data intact.

> *Why*: users close tabs, lose network, or hit refresh. Without draft recovery, they restart from step 1 and give up. Tracking progress in the DB means they can pick up exactly where they left off.

**The E2E test covers the full workflow from step 1 to the final submission**, not individual step tests in isolation.

> *Why*: bugs in wizards live in the transitions between steps — a validation error that only triggers when step 2 has specific data, a field that clears when navigating forward then back. Testing steps in isolation misses all of these.

**Navigation away from a step with unsaved changes prompts a confirmation**, if auto-save isn't wired up for the current fields.

> *Why*: silent data loss is the worst failure mode. If the user doesn't notice the data is gone, they submit a half-completed wizard and hit an error on the server, or worse, submit bad data. A confirmation dialog is cheap and prevents both.

## Required acknowledgment (paste verbatim)

> I will persist each step's data, support back navigation, track `lastCompletedStep` for draft recovery, and write a full-workflow E2E test (step 1 through final submission).

## Common drift caught by reviewers

- Back button lands on the prior step with empty fields — reviewer flags: acknowledged rule required data restoration.
- No `lastCompletedStep` tracking — reviewer flags: draft recovery is broken.
- E2E tests each step independently instead of the full flow — reviewer flags: integration bugs between steps slip through.
- Navigation away mid-step with unsaved changes doesn't prompt — reviewer flags: silent data loss.
