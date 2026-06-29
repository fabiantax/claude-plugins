# Skill Creator Examples: Real Skills and Patterns

Comprehensive examples showing well-designed and poorly-designed skills.

---

## Example 1: Spec-Kit Skill (EXCELLENT)

### Why This Skill Works

✅ **Trigger keywords are specific**: "specification", "spec-driven", "requirements" don't conflict with others
✅ **Comprehensive content**: 320+ lines of methodology
✅ **Real examples**: A/B testing from actual neural-trader project
✅ **Validation checklists**: "All FR-XXX implemented" ✓
✅ **Supporting files**: Templates + reference guide
✅ **Teaches methodology**: 5-phase workflow explained

### Skill Analysis

```yaml
---
name: spec-kit
description: |
  Implement GitHub's Spec-Kit specification-driven development methodology.
  Use when defining requirements before implementation, starting new features,
  creating formal specifications, or organizing work using executable specs.
  Triggers: spec-kit, speckit, specification, spec-driven, requirements, constitution,
  executable specs, formal specification, or "what should I build?" before coding.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---
```

**What Makes This Good**:
- **Problem solved**: Teams write inconsistent specs, missing requirements
- **Trigger keywords**: 8 specific options, doesn't conflict
- **Workflow**: 5-phase sequential process (constitution → specify → plan → tasks → implement)
- **Support**: Templates for each phase, real examples, reference guide
- **Validation**: Checklists catch common mistakes (vague requirements, missing acceptance criteria)
- **Scope**: 320+ lines + supporting files = substantial, not shallow

### File Structure

```
.claude/skills/spec-kit/
├── SKILL.md (320+ lines)
├── templates/
│   ├── constitution-template.md
│   ├── specification-template.md
│   └── plan-template.md
├── examples.md (complete A/B testing walkthrough)
└── reference.md (deep methodology guide)
```

### How It Would Be Used

**Conversation Example**:
```
User: "I want to add A/B testing to our system. How should I define this?"

Claude: [Activates spec-kit skill based on "define" + "feature" keywords]

Claude: "I can help you specify the A/B testing feature using GitHub's Spec-Kit
methodology. This ensures you define requirements clearly before implementation.

The workflow is:
1. Specification (define WHAT - requirements FR-001, FR-002...)
2. Planning (define HOW - architecture, tech stack)
3. Tasks (break into actionable work)
4. Implementation (code to satisfy requirements)

Let's start with the specification..."
```

---

## Example 2: Skill-Creator Skill (This Skill - EXCELLENT)

### Why This Skill Works

✅ **Self-referential**: Teaches what makes a good skill by being one
✅ **Comprehensive framework**: 5-phase design process
✅ **Meta-skill**: Creates skills that create other skills
✅ **Real examples**: References spec-kit and itself as models
✅ **Validation checklist**: Pre-deployment verification
✅ **Tool access justified**: Only Read, Write, Edit (doesn't need Bash)

### Key Sections

1. **Concept & Design** (5 questions to ask)
2. **YAML Structure** (required fields explained)
3. **Step-by-step guide** (how to create skill)
4. **Best practices** (do's and don'ts)
5. **Validation framework** (deployment checklist)
6. **Examples** (spec-kit, testing-guide, this skill)
7. **Troubleshooting** (common problems + fixes)

### How It Works

**When user wants to create a new skill**:
1. User mentions "create a skill" or "skill design"
2. Claude activates skill-creator skill
3. Skill provides framework (5 phases)
4. User follows step-by-step guide
5. Skill's validation checklist catches errors
6. User deploys new skill

---

## Example 3: Testing Guide (HYPOTHETICAL - GOOD)

### Skill Definition

```yaml
---
name: testing-guide
description: |
  Implement comprehensive testing strategies for Python projects using TDD.
  Use when writing test suites, setting up pytest, improving coverage, or debugging failures.
  Triggers: testing, test-driven development, TDD, unit test, pytest, coverage, fixture, mock
allowed-tools: Read, Write, Edit, Bash, Glob
---

# Testing Guide: Test-Driven Development in Python

## Overview
Testing ensures code works correctly and catches regressions early. TDD
(test-driven development) means writing tests BEFORE implementation.

## When to Use
- Starting new feature (write test first)
- Fixing bug (write test reproducing bug)
- Improving coverage (identified untested code)
- Refactoring (tests ensure no regressions)

## The Testing Pyramid

- **Unit Tests (70%)**: Single function, fast (< 1ms each)
- **Integration Tests (20%)**: Multiple components together (< 100ms)
- **E2E Tests (10%)**: Full system flows (1-5 seconds)

## TDD Workflow

1. **RED**: Write failing test
   ```python
   def test_calculate_average():
       assert calculate_average([1, 2, 3]) == 2.0
   ```

2. **GREEN**: Write minimal code to pass
   ```python
   def calculate_average(numbers):
       return sum(numbers) / len(numbers)
   ```

3. **REFACTOR**: Improve code while keeping tests passing
   ```python
   from statistics import mean

   def calculate_average(numbers):
       return mean(numbers)
   ```

## pytest Best Practices

### Fixtures (Setup/Teardown)
```python
@pytest.fixture
def sample_data():
    return [1, 2, 3, 4, 5]

def test_with_fixture(sample_data):
    assert len(sample_data) == 5
```

### Mocking (Isolate Dependencies)
```python
from unittest.mock import patch

@patch('requests.get')
def test_api_call(mock_get):
    mock_get.return_value.json.return_value = {"status": "ok"}
    result = my_api_function()
    assert result == "ok"
```

### Parameterized Tests (Multiple Cases)
```python
@pytest.mark.parametrize("input,expected", [
    ([1, 2, 3], 2.0),
    ([10, 20], 15.0),
    ([5], 5.0),
])
def test_average(input, expected):
    assert calculate_average(input) == expected
```

## Validation Checklist

### Before Implementation
- [ ] Test describes behavior clearly (test name = what it tests)
- [ ] Test is failing (RED state)
- [ ] Test is specific (not testing multiple things)

### During Implementation
- [ ] Test passes (GREEN state)
- [ ] No new warnings or errors
- [ ] Existing tests still pass

### After Refactoring
- [ ] Tests still pass (REFACTOR state)
- [ ] Code is cleaner
- [ ] No test modifications needed

## Coverage Target
- Aim for > 80% code coverage
- 100% is overkill (tests for obvious code)
- Track coverage: `pytest --cov=src --cov-report=html`

## Common Mistakes

### ❌ Test is Too Broad
Bad: `test_user_flow()` (tests login, profile, purchase)
Good: `test_login_with_valid_credentials()` (tests one thing)

### ❌ Test Depends on External Services
Bad: Calls live API in test
Good: Mock the API, test your code logic

### ❌ Test is Flaky (Inconsistent Results)
Bad: Sleeps for 5 seconds hoping service recovers
Good: Mock time or service, test deterministically

## Troubleshooting

### Q: Tests are slow (> 10 seconds for suite)
A: Most tests should be unit tests (mocked). Move slow tests to integration suite.

### Q: Test keeps failing randomly (flaky)
A: Remove timing dependencies. Mock external services. Use fixed seeds for random data.

### Q: Coverage is low (< 60%)
A: Write tests for untested code. Start with high-risk areas (error handling, critical logic).

## Related Skills
- **Spec-Kit Skill**: Define requirements first, then write tests for each requirement
- **Debugging Guide**: When tests fail, use debugging skill to diagnose

## Version History
- **v1.0** (2025-10-24): Initial release with TDD workflow, pytest patterns, 80% coverage target
```

### Why This Hypothetical Skill Would Be Good

✅ **Clear triggers**: "testing", "TDD", "pytest", "coverage"
✅ **Practical workflow**: RED → GREEN → REFACTOR pattern
✅ **Real patterns**: Fixtures, mocking, parameterized tests
✅ **Validation**: Specific checklists ("Test is failing in RED state")
✅ **Common mistakes**: Addresses real problems teams face
✅ **Coverage target**: Specific metric (80%), not vague ("good coverage")
✅ **Tool access**: Bash for running tests, Read/Write for creating test files

---

## Example 4: API Documentation Skill (HYPOTHETICAL - GOOD)

```yaml
---
name: api-documentation
description: |
  Generate comprehensive REST API documentation from code and specifications.
  Use when building REST APIs, documenting endpoints, creating OpenAPI specs, or writing API guides.
  Triggers: API documentation, REST API, OpenAPI, Swagger, endpoint docs, API reference
allowed-tools: Read, Write, Edit, Glob
---

# API Documentation: REST API Reference Guide Generator

## Overview
Good API documentation helps developers understand endpoints without reading code.

## When to Use
- After implementing REST endpoint (document what you built)
- Before publishing API (ensure documentation is complete)
- When API contract changes (update documentation)
- Creating integration guide (help teams use your API)

## Documentation Levels

### Level 1: Endpoint Description
```markdown
## GET /api/v1/users/{user_id}

Retrieve user profile by ID.

**Parameters**:
- user_id (path, required): Unique user identifier

**Response** (200 OK):
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Errors**:
- 404 Not Found: User doesn't exist
- 401 Unauthorized: Not authenticated
```

### Level 2: OpenAPI Schema
```yaml
paths:
  /users/{user_id}:
    get:
      summary: Get user profile
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: User found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '404':
          description: User not found
```

### Level 3: Integration Guide
- How to authenticate
- How to handle errors
- Code examples in popular languages
- Rate limiting info
- Webhooks (if applicable)

## Validation Checklist

- [ ] All endpoints documented
- [ ] Parameters described (type, required, format)
- [ ] Response schema shown with example
- [ ] Error codes listed with explanations
- [ ] Authentication method documented
- [ ] OpenAPI spec is valid (can parse with swagger-ui)
- [ ] Examples are runnable (curl, Python, etc.)

## Tools

- **FastAPI**: Auto-generates OpenAPI from docstrings
- **OpenAPI Generator**: Creates client libraries
- **Swagger UI**: Interactive API documentation
- **Redoc**: Clean API documentation

## Version History
- **v1.0** (2025-10-24): Initial release with 3-level documentation approach
```

---

## Example 5: POOR Skill - What NOT to Do

### ❌ Bad Skill Design

```yaml
---
name: code-helper
description: |
  Help with code. Use when writing code.
  Triggers: code, help, write, function, debug, problem
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Code Helper

This skill helps with code.

## When to Use
When you need help with code.

## How to Use
1. Ask for help
2. I help you
3. Done

## Examples
Example 1: User wants to write a function
Example 2: User wants to debug code
Example 3: User has a problem

## Conclusion
Use this skill to help with code.
```

### Why This Skill is Bad

❌ **Trigger keywords are too generic**: "code", "help", "write" activate on almost every message
❌ **Content is shallow**: 200 words, no real methodology
❌ **No validation**: User doesn't know when they're done
❌ **No examples**: Abstract examples don't help
❌ **Conflicting with everything**: "help" is used in every conversation
❌ **No clear structure**: Doesn't teach anything specific
❌ **Tool access**: Why does this need all tools? Not justified

### How to Fix It

Make it SPECIFIC to a problem domain:

```yaml
---
name: python-performance
description: |
  Optimize Python code for speed and memory efficiency.
  Use when profiling code, identifying bottlenecks, implementing performance optimizations.
  Triggers: performance, optimization, slow, profiling, memory leak, bottleneck
allowed-tools: Read, Write, Edit, Bash, Glob
---

# Python Performance: Optimization Guide

## When to Use
- Code is too slow (identify and fix bottlenecks)
- Memory usage is high (find leaks)
- Profiling existing code (measure before optimizing)

## Profiling Workflow
1. Measure: Use cProfile to find hotspots
2. Analyze: Which function takes 90% of time?
3. Optimize: Refactor bottleneck function
4. Measure again: Verify improvement

...
```

Much better! Now it's specific, teaches methodology, has validation.

---

## Example 6: Documentation Skill (GOOD)

```yaml
---
name: docs-writer
description: |
  Create clear, maintainable documentation using best practices.
  Use when writing README, API docs, guides, or improving documentation quality.
  Triggers: documentation, README, guide, docs, user guide, API documentation
allowed-tools: Read, Write, Edit, Glob
---

# Documentation Writer: Create User-Centric Guides

## Overview
Good documentation answers the "why" and "how", not just the "what".

## Documentation Levels

### Level 0: README (Entry Point)
- What is this project?
- Quick start (< 5 minutes to hello world)
- Installation
- Common use cases
- Links to detailed guides

### Level 1: Tutorials (Learning)
- Step-by-step walk-through
- Build something concrete
- Explain each step
- Show expected output

### Level 2: Guides (How-To)
- Solve specific problems
- Best practices
- Common patterns
- Troubleshooting

### Level 3: Reference (Deep Dive)
- API reference
- Architecture explanation
- Performance details
- Security considerations

## Documentation Checklist

- [ ] README exists and is current
- [ ] Each major feature has a guide
- [ ] Code examples are runnable
- [ ] API is fully documented
- [ ] Architecture is explained
- [ ] Troubleshooting section covers common issues
- [ ] Links are working

## Tools
- Markdown for documentation
- MkDocs for documentation sites
- GitHub Pages for hosting

## Version History
- **v1.0**: Initial documentation framework
```

---

## Comparison: Good vs. Bad Skills

| Aspect | Good Skill | Bad Skill |
|--------|-----------|----------|
| **Triggers** | 5-10 specific keywords | Generic ("code", "help") |
| **Content** | 2000+ words, methodology | 200 words, vague steps |
| **Examples** | Real, from actual projects | Abstract, hypothetical |
| **Validation** | Specific checklists | None, or vague |
| **Tools** | Only what's needed | All tools "just in case" |
| **Structure** | Clear phases/steps | Random sections |
| **Teaching** | Explains WHY each step matters | Just lists steps |
| **Scope** | Solves specific problem | "Helps with code" (too broad) |

---

## Patterns Across Good Skills

### Pattern 1: Clear Problem Definition

**Good**: "Teams write inconsistent specifications, missing requirements"
**Bad**: "Help with things"

### Pattern 2: Specific Triggers

**Good**: "specification", "spec-driven", "requirements"
**Bad**: "code", "help", "write"

### Pattern 3: Methodology, Not Just Steps

**Good**: "Why each requirement needs acceptance criteria" + "How to write acceptance criteria"
**Bad**: Just "Here are the steps"

### Pattern 4: Real Examples

**Good**: A/B testing from neural-trader project (actual feature, actual code)
**Bad**: "Imagine you have a project..."

### Pattern 5: Validation Checklists

**Good**: "All FR-XXX implemented" ✓, "Tests cover acceptance criteria" ✓
**Bad**: No way to know when complete

---

## Key Takeaway

**The best skills**:
- Solve a SPECIFIC problem (not "help with code")
- Teach METHODOLOGY (phases, frameworks)
- Provide REAL EXAMPLES (from your projects)
- Include VALIDATION (checklists, success criteria)
- Are SUBSTANTIAL (2000+ words, not surface-level)

**The worst skills**:
- Are too GENERIC (trigger on every message)
- Are too SHALLOW (just list steps)
- Have no EXAMPLES (abstract only)
- Have no VALIDATION (user doesn't know when done)
- Request too much TOOL ACCESS (don't need all tools)

Use these examples as your model. When you create your next skill, ask:
- "Is this as specific as spec-kit's triggers?"
- "Is this as comprehensive as skill-creator's content?"
- "Are my examples as real as the A/B testing example?"
- "Do my checklists actually catch errors?"

---

## Version History

- **v1.0** (2025-10-24): Initial examples showing 6 skills (2 real: spec-kit, skill-creator; 3 hypothetical: testing, API docs, docs-writer; 1 anti-pattern: code-helper)
