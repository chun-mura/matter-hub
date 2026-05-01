---
name: ux-heuristics-review
description: Use when evaluating a React UI using usability heuristics and HCD-oriented review criteria.
---

# UX Heuristics Review

Use this skill to evaluate UI from the user's point of view, not just code quality.

## Evaluation lenses

Evaluate the screen or flow using at least these heuristics:

1. Visibility of system status
2. Match between system and real-world language
3. User control and freedom
4. Consistency and standards
5. Error prevention
6. Recognition rather than recall
7. Flexibility and efficiency of use
8. Aesthetic and minimalist design
9. Error recovery support
10. Help and guidance when needed

## HCD-oriented prompts

Also ask:

- Who is the user here?
- What is the main task they are trying to complete?
- What information do they need at this moment?
- What can go wrong in this context?
- Which parts increase cognitive load unnecessarily?
- Which labels or structures assume too much prior knowledge?

## Review method

For each issue, describe:

- Observed problem
- Violated heuristic
- Why it matters for the user
- Severity: 0 to 4
- Recommended improvement

## Severity guidance

- 0: not a usability problem
- 1: cosmetic
- 2: minor
- 3: major
- 4: critical

## Things to inspect closely

- Form completion flows
- Table filtering/sorting/searching
- Destructive actions
- Empty and zero-data states
- Permission-denied and partial-access states
- Loading feedback and background processing
- Confirmation and completion feedback

## Common failure patterns

- User cannot tell what changed after an action.
- System labels are implementation-oriented rather than task-oriented.
- Error messages blame the user but do not explain recovery.
- Important actions are visually buried.
- Too many choices appear at once.
- The interface forces memory of previous context that should be visible.

## Output format

Return:

- Overall usability assessment
- Issues by heuristic
- Highest-severity problems first
- Suggested next fixes for the team
