# Output patterns

Two approaches for structuring consistent outputs in skills.

## Template pattern

Use templates when outputs need consistent structure.

### Strict templates

For standardized outputs like API responses or reports:

```markdown
## Report structure

ALWAYS use this exact template:

### Executive summary
[2-3 sentences summarizing findings]

### Key findings
- Finding 1
- Finding 2
- Finding 3

### Recommendations
1. First recommendation
2. Second recommendation
```

### Flexible templates

When context varies, allow adaptation:

```markdown
## Analysis structure

Use your best judgment. Adjust sections as needed for the specific analysis type.

Suggested sections:
- Overview
- Analysis
- Conclusions
```

## Examples pattern

Use input/output pairs to convey style preferences.

```markdown
## Commit message style

Examples help understand desired format better than descriptions.

### Example 1
Input: Added login button to header
Output: feat(ui): add login button to header

### Example 2
Input: Fixed bug where users couldn't logout
Output: fix(auth): resolve logout failure issue
```

## Choosing between patterns

| Scenario | Pattern | Reason |
|----------|---------|--------|
| API responses | Strict template | Consistent structure required |
| Reports | Strict template | Predictable sections |
| Code comments | Examples | Style is subjective |
| Summaries | Flexible template | Length varies by content |

## Combining patterns

Templates and examples can work together:

```markdown
## Pull request description

Use this template:

### Summary
[1-2 sentences]

### Changes
- Change 1
- Change 2

### Example

Input: Added dark mode toggle with system preference detection
Output:
### Summary
Adds dark mode support that respects system preferences.

### Changes
- Add ThemeProvider context
- Add useSystemTheme hook
- Update Button, Card components for dark mode
```
