---
name: design-token-rules
description: Use when creating or extending the visual foundation of a React project with no existing design system.
---

# Design Token Rules

Use this skill whenever UI styling decisions affect consistency across multiple components.

## Goals

- Create a minimal but scalable token system.
- Replace hardcoded styles with semantic design decisions.
- Make future theming and review easier.

## Token categories

Define tokens for at least:

- Color
- Spacing
- Typography
- Radius
- Border
- Shadow/elevation
- Motion duration/easing
- Z-index layers when needed

## Naming rules

Prefer semantic names over raw appearance names.

- Good: `color.text.primary`, `color.surface.muted`, `space.4`, `radius.md`
- Avoid: `gray300`, `blueButton`, `smallPadding`, `cardShadow2`

If CSS custom properties are used, a project-friendly structure is recommended:

- `--color-text-primary`
- `--color-text-muted`
- `--color-surface-default`
- `--color-surface-subtle`
- `--space-1` ... `--space-8`
- `--font-size-sm` ... `--font-size-xl`
- `--radius-sm` ... `--radius-lg`

## Minimum starter system

When no design system exists, start with:

- 2 to 3 text colors
- 2 to 4 surface colors
- 1 primary accent and semantic feedback colors
- 6 to 8 spacing steps
- 4 to 6 type sizes
- 3 radius levels
- 2 to 3 elevation levels

## Rules for introducing tokens

- Add a token only if it serves more than one component or represents a meaningful semantic role.
- Reuse an existing token before creating a new one.
- Every new token should have a short rationale.
- Favor consistency over micro-optimization.
- Avoid near-duplicate tokens that differ without a clear purpose.

## Hard rules

- No raw hex colors in component files.
- No arbitrary spacing values in component files unless there is a documented exception.
- No one-off font-size values that bypass the type scale.
- No special-case radius or shadow for a single component without justification.

## Review checklist

- Does this token represent a semantic role?
- Can another component reuse it?
- Is the naming future-proof?
- Does it reduce, rather than increase, visual entropy?
- Is contrast acceptable for text and interactive elements?

## Suggested starter files

- `src/styles/tokens.css`
- `src/styles/themes/light.css`
- `src/styles/themes/dark.css`
- `src/components/ui/*`
