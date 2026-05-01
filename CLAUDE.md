# React UI Rules

- Think in English, answer in Japanese.
- Follow relevant skills under `.claude/skills/` when working on UI.
- Prefer shared components over one-off JSX.
- Define or extend design tokens before adding new visual patterns.
- No hardcoded colors, spacing, font sizes, radius, or shadows in component files unless justified.
- No inline styles for permanent visual rules.
- Cover loading, empty, error, success, disabled, and permission states.
- Preserve keyboard navigation, visible focus, labels, and accessible names.
- Prefer this structure:
  - `src/components/ui/*`
  - `src/components/patterns/*`
  - `src/features/<feature>/components/*`
  - `src/styles/tokens.css` or `src/theme/tokens.ts`
- For UI tasks, report:
  1. What changed
  2. Shared components or tokens used/added
  3. States considered
  4. Risks or follow-ups
