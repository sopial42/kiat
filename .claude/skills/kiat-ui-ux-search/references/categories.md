# UI/UX Pro Max Categories

The underlying skill organizes its 99+ guidelines and recommendations into 10 priority categories. Pick the category that matches your current task, then use `search.py --category <name>` to query it.

## Priority CRITICAL

### `accessibility`
WCAG AA compliance, keyboard navigation, screen reader support, color contrast, focus management, ARIA attributes. Query this when building any interactive element.

**Typical queries:**
- Form accessibility: `--category accessibility --query "form labels"`
- Focus states: `--category accessibility --query "focus visible"`
- Color contrast: `--category accessibility --query "contrast ratio"`

### `touch-interaction`
Minimum tap target sizes, gesture patterns, hover vs tap differences, drag behaviors, touch feedback. Query this for anything that will be used on mobile.

**Typical queries:**
- Button sizing: `--category touch-interaction --query "tap target minimum"`
- Drag patterns: `--category touch-interaction --query "drag handle"`

## Priority HIGH

### `performance`
Perceived performance, loading states, skeleton screens, optimistic updates, debouncing, lazy loading. Query this when building pages that fetch data.

**Typical queries:**
- Loading UX: `--category performance --query "skeleton loading"`
- Optimistic UI: `--category performance --query "optimistic update"`

### `style-selection`
Choosing a visual style that matches the product type (SaaS dashboard, landing page, docs site, e-commerce, etc.). 50+ styles cataloged. Query this early in a new project or a new section.

**Typical queries:**
- SaaS dashboard style: `--category style-selection --query "SaaS dashboard minimal"`
- Landing page style: `--category style-selection --query "landing page modern"`

### `layout-responsive`
Grid systems, breakpoints, container patterns, responsive behavior across viewport sizes. Query this for any multi-element layout.

**Typical queries:**
- Card grids: `--category layout-responsive --query "card grid responsive"`
- Sidebar layouts: `--category layout-responsive --query "sidebar collapsible"`

### `navigation-patterns`
Top nav vs side nav, tabs, breadcrumbs, pagination, search patterns, back navigation. Query this when designing how users move through the app.

**Typical queries:**
- Tab patterns: `--category navigation-patterns --query "tab design"`
- Mobile nav: `--category navigation-patterns --query "hamburger mobile"`

## Priority MEDIUM

### `typography-color`
Font pairing (57 curated pairs), type scales, color palettes (161 cataloged), semantic colors, dark mode. Query this when starting a new project or redesigning visual identity.

**Typical queries:**
- Font pairing: `--category typography-color --query "sans-serif modern pairing"`
- Color palette: `--category typography-color --query "SaaS blue palette"`

### `animation`
Transition durations, easing functions, micro-interactions, loading animations, page transitions. Query this when adding motion to an interface.

**Typical queries:**
- Transition timing: `--category animation --query "transition duration"`
- Micro-interactions: `--category animation --query "button hover micro"`

### `forms-feedback`
Input types, validation UX, error messages, success states, progress indicators, multi-step forms. Query this when building any form.

**Typical queries:**
- Inline validation: `--category forms-feedback --query "inline validation error"`
- Multi-step forms: `--category forms-feedback --query "wizard stepper"`

## Priority LOW

### `charts-data`
Chart type selection (25 types across 10 stacks), data table design, empty states, zero-state illustrations. Query this only when the story involves data visualization.

**Typical queries:**
- Chart selection: `--category charts-data --query "time series line chart"`
- Empty states: `--category charts-data --query "empty state illustration"`

## How to pick a category

If you're unsure which category applies, default to `accessibility` (it touches everything) and `layout-responsive` (most visual stories involve layout). Start narrow with 1-2 categories; add more only if the first results don't cover your need.

**Multi-category queries:** you can run several queries in sequence, each with a different category. Don't try to load all 10 categories at once — that defeats the purpose of the on-demand pattern.
