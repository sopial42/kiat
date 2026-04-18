# How to Invoke ui-ux-pro-max

Concrete examples of running `search.py` for common Kiat scenarios. Copy-paste and adapt.

## Basic command structure

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category <category-name> \
  --query "<search terms>"
```

Optional flags (check `search.py --help` for the full list):
- `--limit N` — cap the number of results (default 5)
- `--priority critical|high|medium|low` — filter by priority
- `--format markdown|json` — output format (default markdown)

## Example 1: Designing a new form with validation

**Scenario**: Story 03 introduces a signup form with 8 fields, client-side validation, and inline errors.

```bash
# Form design patterns
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category forms-feedback \
  --query "inline validation error" \
  --limit 5

# Accessibility rules for forms
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category accessibility \
  --query "form labels required" \
  --limit 3
```

**Expected output**: 5-8 recommendations covering validation timing, error message placement, required field indicators, and label/input association.

## Example 2: Choosing a layout for a new dashboard page

**Scenario**: Story 07 builds a new analytics dashboard showing 4 KPI cards and 2 time-series charts.

```bash
# Layout pattern
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category layout-responsive \
  --query "dashboard KPI cards grid" \
  --limit 5

# Chart type selection
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category charts-data \
  --query "time series line chart" \
  --limit 3
```

**Expected output**: Recommendations on grid breakpoints for the KPI cards, spacing between the cards and charts, and which chart library patterns suit time-series data.

## Example 3: Picking a color palette for a new project

**Scenario**: Bootstrapping a new SaaS with a trusted, professional look.

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category typography-color \
  --query "SaaS professional trust palette" \
  --limit 5
```

**Expected output**: 3-5 curated color palettes from the 161 available, each with hex codes and reasoning.

**Important**: after getting palette recommendations, always cross-reference with `delivery/specs/design-system.md` — the project may already have an established palette that takes precedence.

## Example 4: Ensuring touch targets are mobile-friendly

**Scenario**: Story 12 adds swipe gestures and tappable cards to an existing mobile view.

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category touch-interaction \
  --query "tap target size swipe gesture"
```

**Expected output**: Minimum tap target dimensions (usually 44×44 per Apple HIG, 48×48 per Material), safe spacing between interactive elements, swipe affordance patterns.

## Example 5: Micro-interactions for form submission

**Scenario**: Story 09 adds success/error animations when submitting a contact form.

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  --category animation \
  --query "form submit success error feedback"
```

**Expected output**: Recommended transition durations (usually 200-400ms), easing functions (ease-out for success, ease-in-out for errors), visual patterns (checkmark animation, shake effect).

## Tips for effective queries

**Be specific in the query terms.** "button" alone is too vague; "button hover primary" gives much better results.

**Match the query to the category.** Querying "color palette" in `layout-responsive` won't give useful results — use `typography-color`.

**Use 2-4 keywords.** Too few (1 keyword) returns noise; too many (5+) returns nothing.

**Run multiple small queries.** Better to run 3 focused queries than 1 giant one. Each query costs ~500-2000 tokens of output, so budget accordingly.

**Iterate.** If the first query returns irrelevant results, rephrase and try again. The knowledge base is searchable by semantic similarity, not just keyword match.

## What to do with the results

1. **Read the recommendations**, noting any that explicitly contradict your project's design system or existing patterns (project wins).
2. **Apply the non-conflicting recommendations** to your spec or code.
3. **Leave an audit line** in your output summarizing what you queried and what you applied:
   ```
   UI/UX search: category=forms-feedback, query="inline validation error", 3 recommendations applied (inline timing, red-500 color, aria-invalid)
   ```
4. **Don't cite the skill as authoritative** — present the recommendations as "based on UI/UX best practices from ui-ux-pro-max" so the user and reviewer know where they come from.
