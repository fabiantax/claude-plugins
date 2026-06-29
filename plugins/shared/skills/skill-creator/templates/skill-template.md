# Skill Template: Starting Point for New Skills

Use this template as a starting point when creating a new Claude Code skill.

---

## YAML Frontmatter

```yaml
---
name: your-skill-name
description: |
  One sentence describing what the skill does.
  One sentence explaining why it's useful and what problem it solves.
  Use when: [scenario 1], [scenario 2], [scenario 3]
  Triggers: keyword1, keyword2, keyword3, keyword4, keyword5
allowed-tools: Read, Write, Edit, Bash
---
```

### Frontmatter Guide

| Field | Purpose | Example |
|-------|---------|---------|
| `name` | Unique skill identifier (lowercase, dashes) | `api-documentation`, `testing-guide` |
| `description` | 3-5 sentences explaining what + when to use | "Create REST API documentation..." |
| `Triggers:` | Keywords Claude watches for (5-10 options) | "specification", "spec-driven", "requirements" |
| `allowed-tools` | Tools skill is allowed to use | "Read, Write, Edit, Bash, Glob, Grep" |

---

## Main Content Structure

```markdown
# Your Skill Name: Subtitle

## Overview
- What is this skill?
- What problem does it solve?
- Why should you use it?

## When to Use This Skill
- Scenario 1: [Explain specific situation]
- Scenario 2: [Explain specific situation]
- Scenario 3: [Explain specific situation]

## Core Concepts
### Concept 1: Name
Definition and why it matters

### Concept 2: Name
Definition and why it matters

### Concept 3: Name
Definition and why it matters

## The Workflow (Main Content)

### Phase 1: [Name]
- What happens in this phase?
- What's the output?
- How long does it take?

### Phase 2: [Name]
- What happens in this phase?
- What's the output?
- How long does it take?

### Phase 3: [Name]
- What happens in this phase?
- What's the output?
- How long does it take?

## Implementation Guide

### Step 1: [Name]
Detailed explanation of what to do

**Example**:
```
Code or concrete example here
```

### Step 2: [Name]
Detailed explanation of what to do

**Example**:
```
Code or concrete example here
```

## Examples

### Example 1: [Realistic Scenario]
- **Situation**: Describe the situation
- **Process**: Show step-by-step what happens
- **Outcome**: What is the result?
- **Learning**: Why does this matter?

### Example 2: [Different Scenario]
- **Situation**: Describe the situation
- **Process**: Show step-by-step what happens
- **Outcome**: What is the result?
- **Learning**: Why does this matter?

## Best Practices

### ✅ DO

1. **Best practice 1** - Why this matters
2. **Best practice 2** - Why this matters
3. **Best practice 3** - Why this matters

### ❌ DON'T

1. **Anti-pattern 1** - Why to avoid
2. **Anti-pattern 2** - Why to avoid
3. **Anti-pattern 3** - Why to avoid

## Validation Checklist

### Pre-Workflow
- [ ] Specific item 1
- [ ] Specific item 2
- [ ] Specific item 3

### During Workflow
- [ ] Specific item 1
- [ ] Specific item 2
- [ ] Specific item 3

### Post-Workflow (Completion)
- [ ] Specific item 1
- [ ] Specific item 2
- [ ] Specific item 3

## Common Mistakes

### ❌ Mistake 1: [Name]
- **What happens**: Describe the error
- **Why it happens**: Root cause
- **How to fix**: Solution
- **Prevention**: How to avoid

### ❌ Mistake 2: [Name]
- **What happens**: Describe the error
- **Why it happens**: Root cause
- **How to fix**: Solution
- **Prevention**: How to avoid

## Troubleshooting

### Q: Common question?
**A**: Direct answer with explanation

### Q: Another question?
**A**: Direct answer with explanation

### Q: Question about edge case?
**A**: Direct answer with explanation

## Related Skills
- **[Skill Name]**: When to use this related skill
- **[Skill Name]**: When to use this related skill

## References
- [Link to reference 1]
- [Link to reference 2]
- [Link to reference 3]

## Version History
- **v1.0** (YYYY-MM-DD): Initial release with [what's included]

---

## Content Guidelines

### Length
- **Minimum**: 2000 words (substantial content)
- **Maximum**: No limit, but split into supporting files if > 5000 words
- **Target**: 2500-4000 words for main SKILL.md

### Tone
- **Prescriptive**: Tell people exactly what to do
- **Practical**: Use real examples, not hypothetical
- **Honest**: Include limitations and trade-offs
- **Helpful**: Provide checklists and templates

### Structure
- **Clear headings**: Users should be able to skim and find answers
- **Short paragraphs**: 2-3 sentences max per paragraph
- **Code blocks**: For any code examples
- **Lists**: For steps, options, criteria
- **Tables**: For comparisons or structured data

### Examples
- **Real over hypothetical**: Use actual projects, not "imagine..."
- **Complete**: Show input → process → output
- **Explained**: Why each step matters
- **Actionable**: Users should be able to copy and adapt

### Validation
- **Specific, not vague**: "Return HTTP 400" not "Handle errors well"
- **Testable**: Can be verified automatically or manually
- **Comprehensive**: Cover normal cases AND edge cases
- **Checkboxes**: [ ] for yes/no items in checklists

---

## File Organization

If your skill is complex, create supporting files:

```
.claude/skills/your-skill/
├── SKILL.md                    # Main skill file (this file)
├── templates/
│   ├── template-1.md           # Starter template
│   └── template-2.md           # Another template
├── examples.md                 # Real-world examples
├── validation.md               # Deep validation guide
└── reference.md                # Optional: deep methodology guide
```

---

## Before You Deploy

- [ ] YAML frontmatter is valid (no syntax errors)
- [ ] Trigger keywords are specific + broad (5-10 options)
- [ ] Tool access is minimal (only what's needed)
- [ ] Content is 2000+ words
- [ ] Examples are real, not hypothetical
- [ ] Validation checklists actually catch errors
- [ ] No hardcoded paths or project assumptions
- [ ] Works with CLAUDE.md instructions
- [ ] Skill is at `.claude/skills/{name}/SKILL.md`
- [ ] Version history is current

---

## Tips for Great Skills

1. **Use your own project as example** - Real beats fake
2. **Teach methodology, not just steps** - Why each phase matters
3. **Provide checklists** - Users should know when they're done
4. **Include failures** - Show what goes wrong and why
5. **Link to related skills** - Help users understand ecosystem
6. **Version your skills** - Document improvements over time
7. **Get feedback** - Use your skill, iterate based on reality

---

Good luck building your skill! 🚀
