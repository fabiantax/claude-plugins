# Skill Validation Guide: Comprehensive Quality Assurance

Detailed validation framework to ensure your skill is production-ready before deployment.

---

## Pre-Deployment Validation Matrix

### TIER 1: YAML & Frontmatter (5 Items)

**1. YAML Syntax is Valid** ✓
- [ ] `---` opening fence on line 1
- [ ] All quoted strings have matching quotes
- [ ] Indentation is consistent (2 spaces)
- [ ] `---` closing fence after all fields
- [ ] No trailing whitespace

**How to test**:
```bash
python3 << 'EOF'
import yaml
with open('.claude/skills/your-skill/SKILL.md', 'r') as f:
    content = f.read()
    frontmatter = content.split('---')[1]
    yaml.safe_load(frontmatter)
    print("✓ YAML is valid")
EOF
```

**2. Required Fields Present** ✓
- [ ] `name:` field exists (lowercase, dashes)
- [ ] `description:` field exists (3-5 sentences)
- [ ] `description:` includes "Triggers:" clause
- [ ] `description:` includes "Use when:" clause
- [ ] `allowed-tools:` field exists

**Example (check each)**:
```yaml
---
name: your-skill-name              # ✓ Lowercase, dashes
description: |                      # ✓ Multi-line description
  One sentence what it does.
  One sentence why useful.
  Use when: [scenarios]             # ✓ "Use when:" present
  Triggers: keyword1, keyword2      # ✓ "Triggers:" present
allowed-tools: Read, Write, Edit    # ✓ Tools specified
---
```

**3. Trigger Keywords are Valid** ✓
- [ ] 5-10 keywords listed (not fewer, not 100+)
- [ ] Keywords are specific (not "code", "help", "write")
- [ ] Keywords don't overlap with other skills
- [ ] Keywords are separated by commas or newlines

**Validation checklist**:
```
Count keywords: _____ (target 5-10)
Are any keywords generic? (Yes/No)
Do keywords conflict with: spec-kit, skill-creator, others? (Yes/No)
```

**4. Tool Access is Justified** ✓
- [ ] `allowed-tools` lists only needed tools
- [ ] Skill doesn't request tools it won't use
- [ ] Each tool is justified in documentation
- [ ] Minimal permission principle applied

**Example violations**:
```yaml
❌ allowed-tools: Read, Write, Edit, Bash, Grep, Glob  # Too many
✅ allowed-tools: Read, Write                          # Only what's needed
```

**5. File Location is Correct** ✓
- [ ] File is at `.claude/skills/{name}/SKILL.md`
- [ ] Directory name matches `name:` field
- [ ] No file extensions in directory name
- [ ] Dashes (not underscores) used in name

---

### TIER 2: Content Structure (8 Items)

**6. Overview Section Exists** ✓
- [ ] Overview explains what skill does (1-2 paragraphs)
- [ ] Explains why it's useful
- [ ] Explains when to use it
- [ ] No code in overview (just explanation)

**Check**:
```
Does overview answer:
  "What is this skill?" □
  "Why is it useful?" □
  "When should I use it?" □
```

**7. Workflow/Phases Defined** ✓
- [ ] Skill has clear phases or steps (minimum 3)
- [ ] Each phase has description
- [ ] Each phase has expected output
- [ ] Phases are sequential (or explicitly parallelizable)

**Example structure**:
```
Phase 1: Specification
  - What: Define requirements (FR-001...)
  - Output: specification.md file
  - Time: 2-4 hours

Phase 2: Planning
  - What: Design architecture
  - Output: plan.md file with tech decisions
  - Time: 4-8 hours

Phase 3: Tasks
  - What: Break into actionable work
  - Output: tasks.md with dependency ordering
  - Time: 1-2 hours
```

**8. Examples Included** ✓
- [ ] Minimum 2 real examples provided
- [ ] Examples are not hypothetical ("Imagine...")
- [ ] Examples show input → process → output
- [ ] Examples explain the reasoning

**Quality check**:
```
Example 1 is:
  - Real (from actual project)? □
  - Complete (shows all steps)? □
  - Explained (why each step)? □
  - Actionable (user could copy)? □

Example 2 is:
  - Real? □
  - Complete? □
  - Explained? □
  - Actionable? □
```

**9. Best Practices Section** ✓
- [ ] "✅ DO" section with 3-7 good practices
- [ ] "❌ DON'T" section with 3-7 anti-patterns
- [ ] Each practice is specific (not generic advice)
- [ ] Reasons explained for each

**Check each practice**:
```
Practice: "Define requirements clearly"
  Is it specific? Yes □ No □
  Is reason explained? Yes □ No □
  Is it actionable? Yes □ No □
```

**10. Validation Checklist Included** ✓
- [ ] Pre-workflow checklist (before starting)
- [ ] During-workflow checklist (while working)
- [ ] Post-workflow checklist (before completion)
- [ ] Each item is specific and verifiable

**Quality of items**:
```
❌ Bad:   "Complete the task" (vague, not verifiable)
✅ Good:  "All FR-XXX requirements implemented" (specific, verifiable)
```

**11. Troubleshooting Section** ✓
- [ ] Q&A format (Question → Answer)
- [ ] Minimum 5 common questions
- [ ] Answers include root cause AND solution
- [ ] Covers common mistakes and edge cases

**Coverage check**:
```
Does troubleshooting address:
  - Common mistakes? □
  - Performance issues? □
  - Configuration problems? □
  - Integration challenges? □
  - Edge cases? □
```

**12. Version History Included** ✓
- [ ] Version number (v1.0 format)
- [ ] Date (YYYY-MM-DD format)
- [ ] Description of what's in version
- [ ] Previous versions listed if applicable

**Example**:
```markdown
## Version History

- **v1.0** (2025-10-24): Initial release with 5-phase workflow, templates, validation checklist
```

**13. References/Links Included** ✓
- [ ] External references provided (GitHub, docs, etc.)
- [ ] Links to related skills mentioned
- [ ] Links to supporting files (.specify/ templates, etc.)
- [ ] All links are valid (not 404)

---

### TIER 3: Content Quality (7 Items)

**14. Word Count and Depth** ✓
- [ ] Main SKILL.md is 2000+ words
- [ ] Not just surface-level (teaches methodology)
- [ ] Substantial explanations, not brief mentions
- [ ] Supporting files if content > 5000 words

**Count words**:
```bash
wc -w .claude/skills/your-skill/SKILL.md
# Target: 2000-4000 for main file
```

**Quality checklist**:
```
Does skill teach methodology? Yes □ No □
Or just list steps? Yes □ No □
Would user understand the "why"? Yes □ No □
```

**15. Tone and Voice** ✓
- [ ] Prescriptive (tells you exactly what to do)
- [ ] Professional but accessible (not overly academic)
- [ ] Honest about limitations (not overselling)
- [ ] Helpful and encouraging

**Sample check**:
```
This sentence: "You should create specifications for requirements"
  Is it prescriptive? Yes □ No □
  Is it professional? Yes □ No □
  Is it clear? Yes □ No □
```

**16. Jargon and Accessibility** ✓
- [ ] Technical terms are defined
- [ ] Not assuming prior knowledge of methodology
- [ ] Acronyms are spelled out (FR-XXX = Functional Requirement)
- [ ] Links provided for advanced concepts

**Check**:
```
Technical terms used: _____, _____, _____
Are they defined? Yes □ No □
Would non-expert understand? Yes □ No □
```

**17. Code Examples Quality** ✓
- [ ] Code examples are syntactically valid
- [ ] Examples show what's being explained
- [ ] Comments explain non-obvious parts
- [ ] Examples are runnable (or clearly marked as pseudo-code)

**Validation**:
```python
# ✓ Good: Comment explains purpose
def calculate_welchs_ttest(champion_returns, challenger_returns):
    """Calculate statistical significance of difference"""
    return scipy.stats.ttest_ind(champion_returns, challenger_returns, equal_var=False)

# ❌ Bad: No explanation, unclear purpose
def calc(a, b):
    return scipy.stats.ttest_ind(a, b, equal_var=False)
```

**18. Cross-References and Links** ✓
- [ ] Links to supporting files (templates/, examples.md, reference.md)
- [ ] Links to other related skills
- [ ] Links are relative paths (not absolute URLs)
- [ ] All links are valid and findable

**Check**:
```bash
# Find all links
grep -o '\[.*\](.*\.md)' .claude/skills/your-skill/SKILL.md
# Verify each file exists
```

**19. Formatting and Readability** ✓
- [ ] Clear heading hierarchy (# → ## → ###)
- [ ] Short paragraphs (2-3 sentences max)
- [ ] Bullet points for lists (not paragraphs)
- [ ] Code blocks properly formatted with language
- [ ] Tables for structured data

---

### TIER 4: Functional Validation (5 Items)

**20. Skill Activates Correctly** ✓
- [ ] Create test conversation mentioning trigger keywords
- [ ] Claude mentions or offers to use the skill
- [ ] Skill content is relevant to conversation
- [ ] No false positives (doesn't activate unexpectedly)

**Test conversation**:
```
You: "I want to define specifications for my new feature"

Claude should: Mention spec-kit skill or offer to help with spec-kit methodology
Not: Suggest unrelated skills

You: "I want to write code"

spec-kit skill should: NOT activate (not about specifications)
```

**21. Template Files Exist** ✓
- [ ] If skill has templates, they exist
- [ ] Templates are at `templates/` subdirectory
- [ ] Templates are copy-paste ready
- [ ] Examples in templates match documented process

**Check**:
```bash
ls -la .claude/skills/your-skill/templates/
# Should see: template-1.md, template-2.md, etc.
```

**22. Supporting Files Quality** ✓
- [ ] If examples.md exists, has real examples
- [ ] If reference.md exists, provides deep methodology
- [ ] If validation.md exists, helps teams validate
- [ ] Supporting files are properly linked from SKILL.md

**Structure check**:
```
.claude/skills/your-skill/
├── SKILL.md (main, 2000+ words) ✓
├── templates/ (if needed)
│   ├── template-1.md ✓
│   └── template-2.md ✓
├── examples.md (if needed) ✓
└── reference.md (optional) ✓
```

**23. No Hardcoded Assumptions** ✓
- [ ] No paths like `/home/user/projects/` (assumes structure)
- [ ] No assumed tools (e.g., "use npm" without mentioning alternatives)
- [ ] No project-specific references (like "neural-trader")
- [ ] Generalizable to different projects and teams

**Bad examples**:
```
❌ "In the src/ directory..."      (assumes structure)
❌ "Run npm install..."            (assumes npm, not yarn/pnpm)
❌ "Like in neural-trader..."      (project-specific)

✓ Good: "In your project's source directory..."
✓ Good: "Run your package manager (npm, yarn, pnpm)..."
✓ Good: "Like in the A/B testing example..."
```

**24. Integration with CLAUDE.md** ✓
- [ ] Skill respects project's CLAUDE.md instructions
- [ ] Doesn't conflict with project standards
- [ ] Works with project's tech stack
- [ ] Follows project's development practices

**Check against CLAUDE.md**:
```
Does skill respect:
  - Concurrent execution (single message pattern)? □
  - File organization (src/, tests/, docs/)? □
  - Python version (3.14 requirement)? □
  - No root directory files rule? □
  - Task tool usage over slash commands? □
```

---

## Comprehensive Deployment Checklist

### BEFORE YOU DEPLOY (30-Point Checklist)

**YAML & Structure (5 points)**
- [ ] 1. YAML syntax is valid
- [ ] 2. Required fields present (name, description, allowed-tools)
- [ ] 3. Trigger keywords are valid (5-10, specific, not conflicting)
- [ ] 4. Tool access is justified (minimal permission)
- [ ] 5. File at `.claude/skills/{name}/SKILL.md`

**Content Structure (8 points)**
- [ ] 6. Overview section explains what/why/when
- [ ] 7. Workflow has 3+ phases with outputs
- [ ] 8. 2+ real examples included
- [ ] 9. Best practices section (DO's and DON'Ts)
- [ ] 10. Validation checklist (pre/during/post)
- [ ] 11. Troubleshooting Q&A section
- [ ] 12. Version history included
- [ ] 13. References and related skills linked

**Content Quality (7 points)**
- [ ] 14. 2000+ words (not shallow)
- [ ] 15. Tone is prescriptive and helpful
- [ ] 16. Jargon is defined, accessible
- [ ] 17. Code examples are valid and explained
- [ ] 18. All links are valid (relative paths)
- [ ] 19. Formatting is clean and readable

**Functional Validation (5 points)**
- [ ] 20. Skill activates on trigger keywords
- [ ] 21. Template files exist and are usable
- [ ] 22. Supporting files (examples, reference) included
- [ ] 23. No hardcoded assumptions
- [ ] 24. Integrates with project's CLAUDE.md

### Score Calculation

```
Points earned: _____ / 30

✅ 27-30: Ready to deploy (excellent)
⚠️  24-26: Ready with minor fixes
❌ < 24: Needs revision before deployment
```

---

## Common Validation Failures

### Failure 1: Vague Trigger Keywords

**Problem**: "code", "help", "write" used as triggers
**Result**: Skill activates on almost every message
**Fix**: Use problem-domain specific keywords

```
❌ Before: Triggers: code, help, writing, functions
✅ After: Triggers: specification, spec-driven, requirements, formal spec
```

### Failure 2: Shallow Content

**Problem**: SKILL.md is 500 words, just lists steps
**Result**: Doesn't teach methodology, feels incomplete
**Fix**: Expand to 2000+ words with examples, reasoning, best practices

```
❌ Before:
  Phase 1: Write specifications
  Phase 2: Implement code
  Phase 3: Test code

✅ After:
  Phase 1: Specification
    - Define problem (who, what, why, when)
    - Extract requirements (FR-001, FR-002...)
    - Document acceptance criteria
    - Get stakeholder approval
    - Output: specification.md file
    - Why: Clear contract with implementation
    - Time: 2-4 hours
    - Example: [Real A/B testing example]
    - Common mistakes: [What goes wrong]
```

### Failure 3: No Examples

**Problem**: "Imagine you have a project..."
**Result**: Too abstract, users don't connect
**Fix**: Use real examples from actual projects

```
❌ Before: "Suppose you have a feature to specify..."
✅ After: "In the neural-trader A/B testing feature, specification defined
         Welch's t-test (FR-001), Cohen's d (FR-002), confidence intervals (FR-003)..."
```

### Failure 4: No Validation

**Problem**: User doesn't know when they're done
**Result**: Incomplete work, satisfaction unclear
**Fix**: Add specific checklists

```
❌ Before: "Complete the workflow"
✅ After:
  - [ ] All FR-XXX requirements implemented
  - [ ] Tests cover all acceptance criteria
  - [ ] Implementation matches plan
  - [ ] No scope creep (only spec features)
  - [ ] Documentation updated
```

### Failure 5: Too Many Permissions

**Problem**: `allowed-tools: Read, Write, Edit, Bash, Glob, Grep` for documentation skill
**Result**: Excessive permissions (why does docs skill need Bash?)
**Fix**: Only list tools actually needed

```
❌ Before: allowed-tools: Read, Write, Edit, Bash, Glob, Grep
✅ After: allowed-tools: Write, Edit, Glob
```

---

## Validation Tools & Commands

### YAML Validation

```bash
# Check YAML syntax
python3 -c "import yaml; yaml.safe_load(open('.claude/skills/your-skill/SKILL.md').read().split('---')[1])"
```

### Word Count

```bash
# Count words in main file
wc -w .claude/skills/your-skill/SKILL.md

# Should be 2000+
```

### Link Validation

```bash
# Find all markdown links
grep -o '\[.*\](.*\.md)' .claude/skills/your-skill/SKILL.md

# Check if files exist
for link in $(grep -o '\[.*\](.*\.md)' | sed 's/.*(\(.*\)).*/\1/'); do
  if [ ! -f "$link" ]; then
    echo "❌ Missing: $link"
  else
    echo "✓ Found: $link"
  fi
done
```

### Structure Check

```bash
# List skill directory
tree .claude/skills/your-skill/

# Should show: SKILL.md + optional templates/, examples.md, reference.md
```

---

## Final Sign-Off

Before deploying, verify:

```markdown
## Skill Validation Sign-Off

**Skill Name**: [your-skill-name]
**Date**: [YYYY-MM-DD]
**Reviewer**: [Your name]

### Validation Results
- YAML & Structure: ✅ 5/5
- Content Structure: ✅ 8/8
- Content Quality: ✅ 7/7
- Functional: ✅ 5/5

### Total Score: ✅ 30/30 - READY TO DEPLOY

### Notes:
- Trigger keywords validated against existing skills
- All examples are real and from actual projects
- Validation checklists tested with sample workflows
- No conflicting assumptions with CLAUDE.md

**Approval**: ✅ Ready for deployment
```

---

## Version History

- **v1.0** (2025-10-24): Initial validation guide with 24-point pre-deployment checklist, common failure patterns, validation tools, and sign-off template.
