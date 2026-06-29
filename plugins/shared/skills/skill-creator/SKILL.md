---
name: skill-creator
description: |
  Create new Claude Code skills with proper YAML frontmatter, trigger keywords, and best practices.
  Use when designing custom skills for your workflow, needing to define new skill capabilities,
  or when you want to extend Claude Code with domain-specific automation.
triggers: skill creation, custom skill, define new skill, skill design, skill automation, skill generator, create skill, build skill, design skill framework, YAML frontmatter, trigger keywords
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Skill Creator: Design and Implement Claude Code Skills

## When Claude Should Activate This Skill

Claude should automatically activate **skill-creator** when:
- ✅ User mentions "skill creation" or "create a skill"
- ✅ User asks to "design a custom skill" or "build a new skill"
- ✅ User needs to define trigger keywords or YAML frontmatter
- ✅ User wants to extend Claude Code with domain-specific automation
- ✅ User is creating skill specifications or skill frameworks
- ✅ User asks about skill design best practices or skill structure

Claude should **NOT** activate this skill for:
- ❌ General code implementation or feature development
- ❌ Code reviews unrelated to skill creation
- ❌ Testing or debugging existing code
- ❌ Writing slash commands (different from skills)

## What is a Claude Code Skill?

A **Claude Code Skill** is a custom capability that Claude autonomously activates based on context. Unlike slash commands (which users explicitly trigger with `/`), skills are **model-invoked**:

- **Users don't ask for the skill** - Claude decides when to use it
- **Triggers are keyword-based** - Skill description contains keywords Claude watches for
- **Skills have full tool access** - Can use Read, Write, Edit, Bash, etc.
- **Persistent across context** - Skill definition loads automatically

### Key Difference: Skills vs. Slash Commands

| Feature | Skill | Slash Command |
|---------|-------|--------------|
| **Invocation** | Model-invoked (automatic) | User-invoked (`/name`) |
| **Trigger** | Keywords in description | User types `/` |
| **Use Case** | Autonomous decision-making | Explicit user requests |
| **Discovery** | Claude knows about skill | User must know slash command |
| **Best For** | Workflow automation, methodology | One-off operations |

**Example**:
- **Skill**: Claude sees "specification" in conversation → activates spec-kit skill automatically
- **Slash Command**: User must type `/sparc` → tells Claude to run SPARC workflow

---

## When to Create a New Skill

Create a skill when you need:

✅ **Autonomous activation** - "When Claude sees X, do Y automatically"
✅ **Methodology implementation** - Multi-phase workflows (spec-kit, SPARC)
✅ **Domain expertise** - Specialized knowledge for specific tasks
✅ **Reusable patterns** - Something you do repeatedly across projects
✅ **Best practices** - Standardized approach to common problems

❌ **Don't create a skill for** - One-time tasks, simple scripts, explicit user requests

---

## The Skill Design Framework

### Phase 1: Skill Concept

**Define the problem** the skill solves:
- What workflow does it automate?
- When should Claude activate it?
- What expertise does it provide?

**Example**: Spec-Kit Skill
- **Problem**: Teams need systematic specification-driven development
- **Activation**: When users discuss "specification", "spec-driven", "requirements"
- **Expertise**: 5-phase workflow, templates, validation checklists

### Phase 2: Trigger Keywords

**Choose keywords Claude watches for**. These go in skill description:

```yaml
description: |
  Create specifications for features using GitHub's Spec-Kit methodology.
  Use when defining requirements, starting new features, writing formal specs.
  Triggers: specification, spec-driven, requirements, spec-kit, formal spec
```

**Good trigger keywords**:
- Problem domain words ("specification", "architecture", "testing")
- User intent words ("define", "design", "plan", "validate")
- Methodology words ("spec-kit", "SPARC", "TDD")
- Common phrases users would type

**Bad trigger keywords**:
- Too generic ("code", "help", "do something") - triggers too often
- Too specific (single use case) - never triggers
- Ambiguous (multiple meanings) - confuses when to activate

### Phase 3: Tool Access

**Declare which tools the skill needs**:

```yaml
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
```

**Common combinations**:
- **Analysis**: `Read, Grep, Glob` (don't modify anything)
- **Code generation**: `Read, Write, Edit, Bash` (full code changes)
- **Testing**: `Read, Bash, Glob` (run tests, read results)
- **Documentation**: `Write, Edit, Read, Glob` (create/update docs)

### Phase 4: Content Structure

**Organize skill file in sections**:

1. **Overview** - What is this skill? What problem does it solve?
2. **When to Use** - When should Claude activate this?
3. **Core Concepts** - Key ideas and terminology
4. **Workflow** - The systematic approach (steps, phases)
5. **Implementation** - How to execute (step-by-step)
6. **Examples** - Real examples of the skill in action
7. **Best Practices** - Do's and don'ts
8. **Validation** - Checklists to verify correctness
9. **Templates** - Starter structures for common tasks
10. **Troubleshooting** - Q&A for common issues

### Phase 5: Validation

**Before deploying, verify**:
- [ ] Trigger keywords make sense
- [ ] Tool access is minimal (security)
- [ ] Skill teaches methodology, not just executes
- [ ] Examples are real and helpful
- [ ] Validation checklists catch errors
- [ ] No assumptions about project structure
- [ ] Works with CLAUDE.md instructions

---

## Skill YAML Structure

### Required Fields

```yaml
---
name: skill-name
description: |
  One-paragraph summary of what skill does.
  Use when [scenario 1], [scenario 2], [scenario 3].
  Triggers: keyword1, keyword2, keyword3
allowed-tools: Read, Write, Edit, Bash
---
```

### Field Breakdown

**`name`** (required, lowercase, dash-separated)
- Must match directory: `.claude/skills/{name}/SKILL.md`
- Example: `spec-kit`, `skill-creator`, `api-documentation`

**`description`** (required, 3-5 sentences max)
- First sentence: What does the skill do?
- Second sentence: What problem does it solve?
- "Use when:" clause explains scenarios
- "Triggers:" lists keywords Claude watches for

**`allowed-tools`** (required, comma-separated)
- List tools skill is allowed to use
- Options: `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`
- Default: All tools (but be explicit for security)

---

## Creating a New Skill: Step-by-Step

### Step 1: Concept & Design

**Ask these questions**:

1. **What problem does this skill solve?**
   - Specific problem (not vague)
   - Real pain point in your workflow
   - Example: "Team writes specifications inconsistently, missing important sections"

2. **When should Claude activate it?**
   - What keywords indicate this problem?
   - Example: Users might say "specification", "requirements", "spec-kit"
   - List 5-10 possible trigger keywords

3. **What methodology should it teach?**
   - Is there a proven process?
   - Example: 5-phase workflow (spec → plan → tasks → implement → evidence)
   - Document the phases

4. **What tools does it need?**
   - Read files? Write files? Run commands?
   - Example: Read (understand specs), Write (create files), Bash (validate structure)

**Document answers in CLAUDE.md or as skill outline**

### Step 2: Create SKILL.md Structure

```yaml
---
name: your-skill-name
description: |
  One sentence: What does the skill do?
  One sentence: Why is it useful?
  Use when: [scenarios where Claude should activate]
  Triggers: keyword1, keyword2, keyword3, keyword4
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Your Skill Name: Subtitle

## Overview
- What is this skill?
- What problem does it solve?
- When should you use it?

## When to Use This Skill
- Scenario 1: ...
- Scenario 2: ...
- Scenario 3: ...

## Core Concepts
- Key idea 1: Explanation
- Key idea 2: Explanation

## The Workflow
- Phase 1: ...
- Phase 2: ...
- Phase 3: ...

## Implementation Guide
- Step 1: ...
- Step 2: ...

## Examples
- Example 1: ...
- Example 2: ...

## Best Practices
- Do: ...
- Don't: ...

## Validation Checklist
- [ ] Item 1
- [ ] Item 2

## Troubleshooting
Q: Question?
A: Answer

## Version History
- **v1.0** (date): Initial release
```

### Step 3: Write Content

**For each section**:
- **Be concrete** - Use real examples, not abstract concepts
- **Be prescriptive** - Show exactly what to do, step-by-step
- **Be complete** - Cover normal cases AND edge cases
- **Be honest** - Include limitations and trade-offs
- **Be useful** - Checklists and templates that teams actually use

### Step 4: Create Supporting Files

**Optional but recommended**:
- `templates/` directory with starter templates
- `examples.md` with real use cases
- `validation.md` with detailed checklists
- `reference.md` with deep methodology

### Step 5: Validate Skill

**Before deploying**:
- [ ] YAML frontmatter is valid (no syntax errors)
- [ ] Trigger keywords are unique (don't conflict with other skills)
- [ ] Tool access is justified (why does skill need these tools?)
- [ ] Content is 2000+ words (substantial, not surface-level)
- [ ] Examples are real and tested
- [ ] Validation checklists actually catch errors
- [ ] No hardcoded assumptions about project structure
- [ ] Works well with CLAUDE.md instructions from project

---

## Skill Best Practices

### ✅ DO

1. **Make triggers specific enough to activate, broad enough to be useful**
   - Good: "specification", "spec-driven", "requirements"
   - Bad: "code" (too generic, activates everywhere), "welch's-t-test" (too specific)

2. **Teach methodology, not just execute**
   - Don't: Just provide templates
   - Do: Explain WHY each section exists, when to use it, trade-offs

3. **Provide validation checklists**
   - Users should know when they're done
   - Checklists catch common mistakes
   - Example: "All FR-XXX implemented" ✅

4. **Include real examples from your project**
   - Abstract examples don't help
   - Use actual features/code from your codebase
   - Example: A/B testing from neural-trader

5. **Document failure modes**
   - What goes wrong? How to fix it?
   - Troubleshooting Q&A section
   - Real errors, not hypothetical

6. **Cross-reference related skills**
   - Link to other skills that complement this one
   - Example: spec-kit skill references SPARC skill
   - Users understand ecosystem

7. **Version your skills**
   - When you improve skill, increment version
   - Document what changed
   - Old projects can use old version if needed

### ❌ DON'T

1. **Don't make skills for one-time tasks**
   - Skills are for reusable methodology
   - One-off scripts should use Bash directly
   - Skill overhead not worth it

2. **Don't use overly broad trigger keywords**
   - "help", "code", "write" trigger constantly
   - Users get skill activated when they don't want it
   - Use specific problem-domain keywords

3. **Don't assume project structure**
   - `/src` directory? `/app`? Don't assume
   - Tools might be in `/tools`, `/utils`, `/lib`
   - Skill should work with different structures

4. **Don't create shallow content**
   - "Run this command" is not a skill
   - Provide context, methodology, guidance
   - Minimum 2000-3000 words of substantial content

5. **Don't duplicate existing skills**
   - Check `.claude/skills/` directory first
   - Maybe existing skill needs enhancement?
   - Avoid conflicting trigger keywords

6. **Don't request excessive permissions**
   - Only include tools skill actually needs
   - `allowed-tools: Read, Write, Edit, Bash` is minimal
   - Don't ask for tools you won't use

7. **Don't forget to test activation**
   - Create sample conversation
   - Verify Claude activates your skill
   - Check if content makes sense in context

---

## Examples of Well-Designed Skills

### Example 1: Spec-Kit Skill

**Good because**:
- Trigger keywords are specific ("specification", "spec-driven", "requirements")
- Substantial content (300+ lines)
- Multiple examples (A/B testing, API endpoints, retrofitting)
- Validation checklists (what makes good requirement?)
- Real from neural-trader project
- Teaches 5-phase methodology (specification-driven development)

**Skill structure**:
```
.claude/skills/spec-kit/
├── SKILL.md (main, 320+ lines)
├── templates/
│   ├── constitution-template.md
│   ├── specification-template.md
│   └── plan-template.md
├── examples.md (real examples)
└── reference.md (deep methodology guide)
```

### Example 2: Skill-Creator Skill (This One!)

**Good because**:
- Trigger keywords ("skill creation", "custom skill", "skill design")
- Teaches skill design framework (5 phases)
- Validation checklist catches common mistakes
- Examples show well/poorly designed skills
- Templates for creating new skills
- Meta-skill (creates skills!)

### Example 3: Future Skill: Testing Framework

**Hypothetical example structure**:

```yaml
---
name: testing-guide
description: |
  Implement comprehensive testing strategies for Python projects.
  Use when writing test suites, setting up TDD workflows, or improving test coverage.
  Triggers: testing, test-driven development, TDD, unit test, integration test, pytest
allowed-tools: Read, Write, Edit, Bash, Glob
---

# Testing Guide: Test-Driven Development in Python

## Overview
...

## When to Use
- Starting new feature (write tests first)
- Fixing bug (write test that reproduces it)
- Improving coverage (identified untested code)

## Testing Pyramid
- Unit tests (70% - fast, focused)
- Integration tests (20% - multiple components)
- End-to-end tests (10% - full system)

## TDD Workflow
1. Write failing test (RED)
2. Write minimal code to pass (GREEN)
3. Refactor to clean code (REFACTOR)

## pytest Best Practices
- Use fixtures for setup/teardown
- Name tests descriptively (test_should_...)
- Mock external dependencies
- Aim for 80%+ coverage

## Coverage Tool Integration
```bash
pytest --cov=src --cov-report=html
```

## Validation Checklist
- [ ] All acceptance criteria have tests
- [ ] Coverage > 80%
- [ ] Tests run in < 10 seconds
- [ ] No flaky tests (consistent results)
...
```

---

## Creating Trigger Keywords

### Framework for Good Triggers

**Problem Domain** + **User Intent** + **Specific Scenario**

Example triggers for Spec-Kit:
- Problem domain: "specification", "requirements", "formal spec"
- User intent: "define", "plan", "specify", "document"
- Specific scenario: "spec-kit", "spec-driven", "before implementation"

Example triggers for Testing:
- Problem domain: "testing", "test", "quality"
- User intent: "write", "improve", "validate", "coverage"
- Specific scenario: "TDD", "unit test", "integration test"

### Trigger Keyword Audit

**Check your triggers**:
1. Are they specific enough? (not "code", "help", "write")
2. Are they broad enough? (not single use case)
3. Do they conflict? (don't overlap with other skills)
4. Would users naturally say these? (not jargon-heavy)
5. Are there 5-10 options? (users might phrase differently)

---

## Tool Access Guidelines

### Minimal Permission Model

Only include tools skill actually uses:

| Skill Type | Tools | Reasoning |
|-----------|-------|-----------|
| **Analysis-only** | `Read, Grep, Glob` | No modifications needed |
| **Code generation** | `Read, Write, Edit, Bash` | Creates/modifies files and runs commands |
| **Testing** | `Read, Bash, Glob` | Runs tests, reads results |
| **Documentation** | `Write, Edit, Read, Glob` | Creates/edits docs |
| **Methodology** | `Read, Write` | Provides templates and guidance |

### Security Considerations

- **Never include Bash** if skill doesn't need to run commands
- **Never include Write** if skill only reads
- **Be explicit** - Better to list needed tools than default to all
- **Justify in documentation** - Why does skill need each tool?

---

## Validation Framework

### Pre-Deployment Checklist

**YAML & Structure** (5 items)
- [ ] YAML syntax is valid (test with `yaml` validator)
- [ ] `name` matches directory (.claude/skills/{name}/)
- [ ] `description` includes triggers
- [ ] `allowed-tools` lists only needed tools
- [ ] File is at `.claude/skills/{name}/SKILL.md`

**Content Quality** (8 items)
- [ ] Overview explains what skill does
- [ ] Trigger keywords are specific + broad enough
- [ ] Methodology is 5+ phases or steps
- [ ] 3+ real examples included
- [ ] Validation checklists provided
- [ ] Troubleshooting Q&A section included
- [ ] Total content > 2000 words
- [ ] No hardcoded paths or assumptions

**Usability** (5 items)
- [ ] Examples use realistic scenarios
- [ ] Templates are copy-paste ready
- [ ] Checklists are specific, not vague
- [ ] Jargon is defined
- [ ] Cross-references to related skills

**Testing** (4 items)
- [ ] Skill activates on trigger keywords
- [ ] Content makes sense in context
- [ ] No errors or broken links
- [ ] Works with your CLAUDE.md instructions

---

## Directory Structure for Skills

```
.claude/skills/
├── spec-kit/                           # Feature: Specification-driven development
│   ├── SKILL.md                        # Main skill file (320+ lines)
│   ├── templates/
│   │   ├── constitution-template.md    # Project principles template
│   │   ├── specification-template.md   # Requirements template
│   │   └── plan-template.md            # Architecture template
│   ├── examples.md                     # Real examples (A/B testing, etc.)
│   └── reference.md                    # Deep methodology guide
│
├── skill-creator/                      # Feature: Create new skills
│   ├── SKILL.md                        # Main skill file (this file)
│   ├── templates/
│   │   ├── skill-template.md           # Template for new skills
│   │   └── skill-anatomy.md            # Understanding skill structure
│   ├── examples.md                     # Examples of well/poorly designed skills
│   └── validation.md                   # Detailed validation guide
│
└── {your-skill}/
    ├── SKILL.md                        # Main skill file
    ├── templates/                      # Optional: Starter templates
    └── reference.md                    # Optional: Deep guide
```

---

## Advanced: Skill Composition

### When Skills Work Together

Skills can reference and activate related skills:

```markdown
## Related Skills

This skill works well with:
- **Spec-Kit Skill** - If you're defining specifications, use spec-kit skill
- **Testing Guide** - After writing code, improve test coverage
- **API Documentation** - Once API is built, document it

You might activate multiple skills in one session:
1. spec-kit (define requirements)
2. testing-guide (write tests)
3. skill-creator (if you need new skill for domain)
4. api-documentation (when API is complete)
```

### Skill Handoff Pattern

```
Conversation Flow:
1. User mentions "specification" → spec-kit skill activates
2. User writes specification using spec-kit
3. User mentions "implementation" → task switches focus
4. User mentions "testing" → testing-guide skill activates
5. User writes tests using testing-guide
6. User mentions "API documentation" → api-documentation skill activates
```

---

## Version Management

### Versioning Scheme

Use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR** (1.0 → 2.0): Breaking changes (restructured workflow)
- **MINOR** (1.0 → 1.1): New features (added phase, new template)
- **PATCH** (1.0 → 1.0.1): Bug fixes (corrected example, fixed typo)

### Change Log Example

```markdown
## Version History

- **v1.1** (2025-10-25): Added "testing" trigger keyword, expanded troubleshooting
- **v1.0** (2025-10-24): Initial release with 5-phase workflow, templates, examples
```

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Triggers That Are Too Generic

**Bad**: "code", "help", "write"
**Why**: Activates on almost every message
**Fix**: Use problem-domain specific keywords ("specification", "requirements")

### ❌ Mistake 2: Tool Access That's Too Broad

**Bad**: `allowed-tools: Read, Write, Edit, Bash, Glob, Grep`
**Why**: Skills should have minimal permissions
**Fix**: `allowed-tools: Read, Write` (if skill only creates files)

### ❌ Mistake 3: Content That's Too Shallow

**Bad**: SKILL.md is 500 words, just lists steps
**Why**: Doesn't teach methodology or reasoning
**Fix**: Expand to 2000+ words with examples, best practices, trade-offs

### ❌ Mistake 4: Examples That Are Fake

**Bad**: "Suppose you have a project with /src directory..."
**Why**: Users don't connect to abstract examples
**Fix**: Use real examples from actual projects (neural-trader, your work)

### ❌ Mistake 5: No Validation Checklist

**Bad**: Skill teaches process but doesn't say when you're done
**Why**: Users don't know if they completed it correctly
**Fix**: Add checklists for each phase

---

## Troubleshooting

### Q: How do I know if my skill will activate?

**A**: Test with trigger keywords:
1. Type a message mentioning your trigger keywords
2. Does Claude mention the skill or offer to use it?
3. Does Claude provide skill content relevant to your message?
4. If not, trigger keywords might be too specific or conflicting

### Q: Can I modify skill after deployment?

**A**: Yes! Skills are living documents:
1. Update SKILL.md with improvements
2. Add new examples as you use skill
3. Increment version number
4. Document changes in version history

### Q: How detailed should examples be?

**A**: Detailed enough that users could copy and adapt:
- Show input (what the starting point is)
- Show process (step-by-step actions)
- Show output (what the result looks like)
- Explain reasoning (why each step matters)

### Q: Can I have multiple trigger keywords that do the same thing?

**A**: No - each keyword should point to ONE skill. But ONE skill can have multiple keywords:

```yaml
Triggers: specification, spec-kit, spec-driven, requirements, formal spec
```

All these keywords activate the same spec-kit skill.

### Q: How do I prevent skill conflicts?

**A**: Check existing skills:
```bash
ls -la .claude/skills/*/SKILL.md
# Review each skill's trigger keywords
# Make sure your keywords don't overlap
```

If keywords conflict, either:
- Choose different keywords for new skill
- Enhance existing skill instead of creating new one

---

## Next Steps: Building Your First Skill

1. **Choose a problem** you solve repeatedly
2. **Design the workflow** (phases, steps, validation)
3. **Pick trigger keywords** (5-10 specific ones)
4. **Write SKILL.md** (use structure from this guide)
5. **Create templates** (if needed for repeated tasks)
6. **Add examples** (real ones from your work)
7. **Add validation** (checklists and Q&A)
8. **Test activation** (make sure skill triggers correctly)
9. **Deploy** to `.claude/skills/{name}/SKILL.md`
10. **Iterate** (improve based on usage)

---

## References

- **Anthropic Skills Repository**: https://github.com/anthropics/skills
- **Skill Creator Resource**: https://github.com/anthropics/skills/tree/main/skill-creator
- **Spec-Kit Skill Example**: `.claude/skills/spec-kit/SKILL.md`
- **Claude Code Documentation**: https://docs.claude.com/en/docs/claude-code/
- **Skills Documentation**: https://docs.claude.com/en/docs/claude-code/skills.md

---

## Version History

### v1.0.0 (2025-10-24)
- Initial creation with complete skill creation framework including YAML frontmatter specification, trigger keyword design, 5-phase skill design methodology, progressive disclosure architecture, and comprehensive validation checklists

---

## Notes for Skill Developers

This skill (skill-creator) is designed to teach you how to create skills systematically. Use it as a template:
- Same YAML structure
- Similar content organization
- Real examples (spec-kit, this skill)
- Validation checklist to catch errors

When you create your next skill, reference this skill as the model:
- "My skill should be as comprehensive as skill-creator"
- "My examples should be as real as skill-creator's"
- "My validation checklist should catch common mistakes"

Skills are most effective when they teach methodology + provide templates + show real examples. Avoid shallow content. Your users will benefit from the depth.

Happy skill building! 🚀
