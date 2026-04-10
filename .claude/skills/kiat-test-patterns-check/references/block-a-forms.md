# Block A — Forms and input fields

**Trigger:** any form, any input field.

## Rules and reasons

**Every input has a programmatic label.** Use `<label htmlFor="id">` or `aria-label` — not a visual `<p>` or `<span>` next to the input.

> *Why*: screen readers announce the label when focus reaches the input. Visual proximity means nothing to assistive tech — a user navigating by Tab hears "edit text" with no context.

**In Playwright tests, use `getByRole('textbox', { name: 'Email' })`, not `getByPlaceholder`.**

> *Why*: `getByRole` matches the accessible name (which screen readers use too), so a passing test is also evidence that the a11y label is correct. `getByPlaceholder` breaks when the placeholder is localized or restyled, and doesn't verify the label exists at all.

**Use `{ exact: true }` on role matchers when the expected text is a substring of other visible UI text.**

> *Why*: a non-exact match against "Save" will also match "Save and exit", producing flaky selector failures that are hard to diagnose.

**The submit button is disabled while the mutation is pending.**

> *Why*: a user clicking twice on a slow submit will fire two POST requests unless the button is disabled. On endpoints that aren't idempotent (new-user signup, order creation), that's duplicate data in the database.

## Required acknowledgment (paste verbatim)

> I will use `<label htmlFor>` for every input, use `getByRole('textbox', { name: ... })` in Playwright tests, and disable the submit button during pending mutations.

## Common drift caught by reviewers

- Test uses `getByPlaceholder('Email')` — reviewer flags: acknowledged Block A rules require `getByRole`.
- Submit button stays clickable during mutation — reviewer flags: acknowledged disabled-during-pending rule.
- Input has only a visual label via `<p>` or `<span>` without `<label htmlFor>` — reviewer flags: a11y violation.
