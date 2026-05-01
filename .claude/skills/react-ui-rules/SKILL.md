---
name: react-ui-rules
description: Use when building or refactoring React UI components, screens, forms, tables, dialogs, and flows.
---

# React UI Rules

Use this skill to build React UI that is reusable, accessible, and easy to maintain.

## Related skills

- `design-token-rules` — tokens, naming, introducing new values
- `design-review` — consistency, token use, visual anti-patterns
- `ux-heuristics-review` — heuristics, flows, cognitive load

## Goals

- Translate product requirements into stable React component structure.
- Avoid one-off JSX and style drift.
- Make states explicit and testable.

## Process

1. Clarify the user goal, main task, and context of use.
2. Identify the domain objects and user actions before designing the JSX structure.
3. Reuse existing primitives first; only create new ones when reuse is awkward.
4. Build mobile-safe and keyboard-safe interactions.
5. Cover all UI states before considering the task complete.
6. Before finalizing, self-review using `design-review` and `ux-heuristics-review`; explain trade-offs when introducing a new pattern or token.

## Component design rules

- Separate presentational primitives from feature-specific business logic.
- Prefer small composable components over giant configurable components.
- Do not introduce variants unless each has a distinct semantic purpose.
- Prefer predictable APIs:
  - Good: `variant`, `size`, `disabled`, `loading`, `tone`
  - Avoid: many boolean props that overlap or conflict
- Prefer composition patterns such as `Card`, `CardHeader`, `CardBody`, `CardFooter` when structure repeats.
- For forms, align label, help text, validation, and action placement consistently.

## State coverage checklist

For any screen or component, explicitly consider:

- Default
- Hover/focus/active
- Disabled
- Loading or skeleton
- Empty
- Error or validation failure
- Success or completion feedback
- Permission/role-based visibility if relevant
- Long content, short content, and unexpected content

## Accessibility rules

- Every interactive element must be keyboard reachable.
- Every icon-only control must have an accessible name.
- Every input must have a label.
- Dialogs, drawers, and menus must support focus management and Escape.
- Do not rely on color alone to communicate status.
- Preserve visible focus styles.

## Layout rules

- Use consistent spacing from tokens.
- Prefer left alignment for dense app UI.
- Keep one primary action per region.
- Use visual hierarchy through spacing, grouping, headings, and emphasis before adding decoration.
- Avoid dashboard clutter; reduce simultaneous emphasis.

## Anti-patterns

- Copy-pasting similar JSX across screens instead of extracting a reusable component.
- Styling with arbitrary values when an existing token would work.
- Overusing modals for workflows that should stay in page context.
- Hiding required information behind hover-only interactions.
- Using placeholder text as a substitute for labels.
- Building forms without inline validation strategy.

## Output expectations

When this skill is used, produce:

- Proposed component breakdown
- State coverage notes
- Accessibility notes
- Reuse opportunities
