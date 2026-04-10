# Block A — Forms / Input Fields

**Trigger:** any form, any input field

## Mandatory rules

- Inputs MUST have labels (`<label htmlFor>` or `aria-label`). Missing = a11y violation.
- Use `getByRole('textbox', { name: 'Email' })` in Playwright, NOT `getByPlaceholder`.
- Use `{ exact: true }` on role matchers when text is a substring of other visible UI text.
- Forms MUST show loading/disabled state during submit (prevents double-click double-submit).

## Required acknowledgment (paste verbatim)

> I will use `<label htmlFor>` for every input, use `getByRole('textbox', { name: ... })` in Playwright tests, and disable the submit button during pending mutations.

## Common drift caught by reviewers

- Test uses `getByPlaceholder('Email')` — reviewer flags: acknowledged Block A rules specify `getByRole`, not `getByPlaceholder`
- Submit button remains clickable during mutation — reviewer flags: acknowledged rule required disabled state during pending
- Input has only visual label via `<p>` or `<span>` without `<label htmlFor>` — reviewer flags: a11y rule violation
