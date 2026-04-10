# When to Use (and When to Skip) kiat-ui-ux-search

Extended decision guide for the tech-spec-writer and frontend coders. Read this when you're on the fence about whether a story needs this skill.

## Use this skill when

### The story introduces something new visually

Anything that didn't exist before — a new page, a new component, a new section of an existing page. First-time design decisions benefit from a structured knowledge base because the decisions will stick around (changing a pattern after 10 stories is expensive).

**Examples:**
- Adding a settings page that didn't exist
- Creating a patient search component with filters and results
- Designing an empty state for a list that could now be empty
- Building a first-time-user onboarding flow

### The story changes interaction patterns

Existing components may be getting new interaction models: hover states, drag behavior, keyboard shortcuts, focus management. Interaction decisions impact accessibility and expected user behavior.

**Examples:**
- Making an existing table sortable and filterable
- Adding keyboard shortcuts to a form
- Introducing drag-and-drop to a list
- Converting click-to-open into hover-to-preview

### The story touches accessibility-critical paths

Any screen where WCAG AA compliance matters — forms, error messages, navigation, data tables, anything that a screen reader user needs to navigate. Skip this only if the story is a trivial text change.

**Examples:**
- Building any form with more than one field
- Designing error states with visual and textual indicators
- Building navigation menus (primary, secondary, mobile)
- Creating data tables with sort and pagination

### The story involves choice points the framework doesn't dictate

When `delivery/specs/design-system.md` gives you the colors and spacing but doesn't tell you which font pairing or chart type to use, that's when a broader knowledge base helps.

**Examples:**
- Picking a time-series chart library or visualization style
- Choosing between tabs, accordion, or stepper for a multi-step form
- Deciding whether to use a modal, drawer, or inline expansion for a detail view
- Selecting loading indicator style (spinner, skeleton, progress bar)

## Skip this skill when

### The story uses an existing pattern

If the spec says "reuse PatientCard" or "follow the same layout as the existing dashboard", consistency with what's already there matters more than fresh recommendations. Query `delivery/specs/project-memory.md` and existing code instead.

**Examples to skip:**
- Adding another card to an existing card grid
- Adding a new menu item to an existing nav
- Adding a new form field to an existing form (just follow the other fields' pattern)

### The design is already provided

If the user references a Figma file, gives you explicit colors/spacing, or has a clear design direction from a designer, follow it. Querying this skill would give you recommendations that contradict the provided design, causing confusion.

**Examples to skip:**
- "Implement the design from Figma link X"
- "Use our brand color #2563EB"
- "Match the style of our homepage"

### The story is trivial

Label changes, copy edits, one-line text updates, color swaps that don't affect layout or meaning. The query overhead is not worth it.

**Examples to skip:**
- Changing "Save" button text to "Save changes"
- Updating an error message from "Invalid" to "Invalid email format"
- Swapping a placeholder image
- Adjusting padding on an existing component by a few pixels

### The story is backend-only

No UI, no user-visible changes, no frontend work at all. Skip unconditionally.

**Examples to skip:**
- Adding a new API endpoint with no frontend consumer yet
- Writing a database migration
- Refactoring backend services
- Adding logging or metrics

### The story is pure refactoring

Moving code around without changing behavior. Users see nothing different, so UI/UX knowledge doesn't apply.

**Examples to skip:**
- Extracting a hook from a component
- Splitting a component into smaller pieces
- Renaming CSS classes
- Updating dependencies

## Decision shortcuts

**One-line test**: ask yourself *"would a designer want to review this story?"* If yes, query the skill. If no, skip.

**Two-question test**:
1. Does this story change something users see or interact with?
2. Does the spec leave visual/interaction decisions open?

If both are "yes", use the skill. If either is "no", skip.

**Budget test**: if adding this skill pushes the coder's context budget above the 25k hard limit, **always skip**, even if the story is visual. Context budget is enforced; a missed UX recommendation is a soft quality issue; a context overflow is a hard failure. Budget wins.

## If you're still unsure

Default to **not** using the skill. The tech-spec-writer's "one source of truth" rule applies: `delivery/specs/design-system.md` and `delivery/specs/project-memory.md` are the project's design authorities. Generic UX recommendations are a supplement, not a replacement.

If a reviewer later says the story should have used the skill, that's feedback you can incorporate into future stories — but it's better to be under-cautious than to blow budgets on every story.
