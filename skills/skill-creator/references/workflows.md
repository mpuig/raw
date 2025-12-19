# Workflow patterns

Structure multi-step processes for clarity and reliability.

## Sequential workflows

For procedures with a clear order of steps.

```markdown
## Process overview

1. Analyze input
2. Transform data
3. Validate output
4. Save results

### Step 1: Analyze input

Run the analysis script:
```bash
python scripts/analyze.py input.json
```

Expected output: `analysis.json` with structure details.

### Step 2: Transform data

Using the analysis, transform the data:
```bash
python scripts/transform.py analysis.json
```

### Step 3: Validate output

Check the transformation succeeded:
```bash
python scripts/validate.py output.json
```

### Step 4: Save results

Move validated output to final location.
```

### Tips for sequential workflows

- Provide an overview first so the full sequence is clear
- Each step should have clear inputs and outputs
- Include verification steps between major operations
- Make steps atomic - each should succeed or fail independently

## Conditional workflows

For processes with decision branches.

```markdown
## Determine task type

First, identify what the user needs:

**If creating new content:**
→ Go to [Content creation workflow](#content-creation)

**If editing existing content:**
→ Go to [Content editing workflow](#content-editing)

### Content creation workflow

1. Gather requirements
2. Create draft
3. Review and refine

### Content editing workflow

1. Load existing content
2. Identify changes needed
3. Apply edits
4. Verify changes
```

### Tips for conditional workflows

- Put the decision point early
- Make conditions mutually exclusive when possible
- Each branch should be self-contained
- Consider fallback for unclear cases

## Iterative workflows

For processes that refine through cycles.

```markdown
## Refinement process

Repeat until satisfied:

1. **Generate** - Create initial output
2. **Evaluate** - Check against criteria
3. **Identify gaps** - Note what's missing or wrong
4. **Refine** - Address specific issues

### Iteration limits

- Maximum 3 iterations for minor refinements
- Stop if no progress between iterations
- Escalate if requirements are unclear
```

## Error handling in workflows

```markdown
## Error recovery

### If step fails

1. Log the error with context
2. Determine if retryable
3. If retryable: wait, then retry (max 2 attempts)
4. If not retryable: report and stop

### Common errors

| Error | Cause | Recovery |
|-------|-------|----------|
| File not found | Missing input | Check path, ask user |
| Validation failed | Bad data | Show issues, request fix |
| Timeout | Slow operation | Retry with longer timeout |
```

## Choosing workflow type

| Scenario | Pattern | Reason |
|----------|---------|--------|
| Build process | Sequential | Clear dependencies |
| User request handling | Conditional | Different request types |
| Content generation | Iterative | Quality refinement |
| Data pipeline | Sequential | Transform chain |
| Bug triage | Conditional | Different bug types |
