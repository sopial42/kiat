# Frontend-Coder Checklist: "Am I Done?"

Before saying "Frontend code ready for review", check ALL:

## Components ✓
- [ ] Uses Shadcn/UI components (not custom unless necessary)
- [ ] Props typed with TypeScript (no `any`)
- [ ] Client/Server boundary correct (`'use client'` for state)
- [ ] Component composition is clean (not monolithic)

## Styling ✓
- [ ] Uses Tailwind classes (no inline styles)
- [ ] Responsive breakpoints: `sm:`, `md:`, `lg:` progressive
- [ ] Border radius: `rounded-[16px]` for buttons/cards, `rounded-full` for circles
- [ ] Colors from design system (e.g., `text-[#273d54]`)
- [ ] Spacing progressive: `p-4 sm:p-6 lg:p-8`
- [ ] Mobile tested at: 320px, 640px, 1024px

## Hooks & State ✓
- [ ] `useQuery` for data fetching (not useEffect + useState)
- [ ] `useMutation` for mutations
- [ ] `useAutoSave` correct (if form) with `enabled` condition
- [ ] Error handling in hooks (user-friendly messages)
- [ ] No stale closure bugs

## Accessibility ✓
- [ ] Every input has label or `aria-label`
- [ ] Labels linked to inputs via `htmlFor`
- [ ] Buttons have accessible text
- [ ] ARIA attributes correct (role, aria-expanded, etc.)
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Focus styles visible (not removed)
- [ ] Axe-core scan passes

## Testing ✓
- [ ] E2E test file exists (`.spec.ts`)
- [ ] Happy path test (complete user flow)
- [ ] Validation test (invalid input → error)
- [ ] Edge case test (offline, slow network, double-click)
- [ ] All tests passing locally (`npm run test:e2e`)

## Error Handling ✓
- [ ] Network errors shown in toast
- [ ] Validation errors shown below fields
- [ ] Offline detection + banner
- [ ] Retry button when appropriate

## Performance ✓
- [ ] No N+1 queries in hooks
- [ ] No unnecessary re-renders
- [ ] No console errors (warnings OK)

## Code Quality ✓
- [ ] No unused imports
- [ ] No commented-out code
- [ ] Clear variable/component names
- [ ] Functions are small and focused

## Final Check ✓
- [ ] Run `npm run test:e2e` → all pass
- [ ] Run `npm run build` → no errors
- [ ] Review changes with `git diff`
- [ ] Branch named with story name
- [ ] Commit message descriptive
- [ ] Ready to hand off to Frontend-Reviewer

---

**If any checkbox unchecked**: Fix before submitting.

**If unsure**: Ask in chat before submitting.
