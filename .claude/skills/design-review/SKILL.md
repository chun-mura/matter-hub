---
name: design-review
description: Use when reviewing React UI for consistency, token usage, and visual quality before merging.
---

# Design Review

Use this skill to review UI output and catch visual inconsistency before human review.

## Review goals

- Detect system drift early.
- Catch AI-like or improvised visual decisions.
- Ensure token and component reuse are happening.

## Review procedure

1. Identify which shared components and tokens appear to be in use.
2. Flag direct style values that should be tokens.
3. Check spacing, hierarchy, and alignment consistency.
4. Check states and edge cases.
5. Check whether the screen fits the product's overall tone.
6. Produce findings grouped by severity.

## Severity levels

- Critical: accessibility, severe inconsistency, broken state handling, misleading action hierarchy
- High: token bypass, inconsistent layout patterns, unclear CTA hierarchy
- Medium: spacing drift, copy vagueness, weak empty/error states
- Low: polish issues, icon inconsistency, minor alignment noise

## What to flag

- Hardcoded visual values instead of tokens
- Duplicate components that should be unified
- Inconsistent button sizing or placement
- Mixed spacing rhythm across similar containers
- Over-emphasized secondary actions
- Missing empty/loading/error states
- Weak contrast or invisible focus treatment
- Generic AI-looking layout patterns with little hierarchy

## Anti-patterns

- Three-card generic marketing layout inside product UI without reason
- Decorative color use that competes with the main action
- Too many component variants with unclear differences
- Tables or forms with inconsistent cell padding and label alignment
- Modal overuse for simple inline tasks
- Dense screens with no grouping or section rhythm

## Output format

Return findings as:

- Summary
- Critical issues
- High-priority issues
- Medium/low issues
- Recommended fixes in implementation order
