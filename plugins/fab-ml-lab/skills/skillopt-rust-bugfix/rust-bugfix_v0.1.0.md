---
name: rust-bugfix-surgical
version: 0.2.0
description: Zero-exploration bugfix workflow for Atlas CLI — enforce surgical search, precise edits, and minimal context loading
---

# Rust Bugfix Workflow (Atlas CLI)

## Purpose
Fix bugs in the Atlas Rust CLI with **zero unnecessary exploration**. This skill enforces a surgical workflow: locate the exact failure point, apply a targeted fix, verify with `cargo check`, and commit. Vague prompts cause 17-min/18-file bloat; precise prompts achieve 30-sec/1-file fixes.

## 🔒 Pre-Edit Checklist (Mandatory Gate)
**DO NOT EDIT UNTIL ALL CHECKBOXES ARE CONFIRMED.**
- [ ] Identified exact error message, panic string, or failing assertion
- [ ] Ran `grep -rn` to locate: (1) manifesting file, (2) schema/contract file, (3) existing test file
- [ ] Classified bug type using the Fix-Type Decision Tree below
- [ ] Drafted precise edit instruction: `edit <file>:<line> change <X> to <Y>`
- [ ] Verified no other agents are modifying the same file (sequential for shared files)

## 🌲 Fix-Type Decision Tree
Match the symptom to the pattern. Apply **only** the corresponding fix. Do not refactor or add boilerplate.

| Symptom / Keyword | Bug Type | Surgical Fix Pattern |
|-------------------|----------|----------------------|
| `serde: missing field`, `TOML parse error`, `init` rejects config | `serde_default` | Add `#[serde(default)]` or `#[serde(default = "fn")]` to the parser struct. **Do not** rewrite the writer. |
| `// commented out`, `bail!("not yet implemented")`, `todo!()` | `commented_out` | Uncomment block. Fix signature to match current API. Remove `bail!`/`todo!`. |
| `--quiet` ignored, `--verbose` inverted, flag not propagating | `flag_logic` | Flip boolean condition. Add early return/guard. Match CLI arg parsing to command dispatch. |
| `format!` mismatch, `Display` impl missing, string truncation | `fmt` | Update format string args. Fix type conversion. Ensure `Debug`/`Display` impl matches struct fields. |
| `panic!`, `unwrap()`, `expect()` on `None`/`Err` | `missing_guard` | Replace with `?` or `ok_or_else!()`. Add explicit error mapping to match CLI error type. |

## 🛠 Workflow

### Step 1: Locate (≤2 minutes)
**NEVER read entire files.** Use surgical searches only:
```bash
# Find the bug location — grep for error messages, function names, or config keys
grep -rn "TODO\|FIXME\|bail!\|unimplemented\|todo!" crates/atlas-cli/src/
grep -rn "exact-error-message" crates/
```
For each bug, identify exactly three files:
1. **Manifesting file** — where the error/panic occurs
2. **Schema file** — what the code should match (config structs, API contracts)
3. **Test file** — existing tests that should catch it

### Step 2: Fix (surgical edit)
**Match the surrounding code's style exactly.** Do not reformat, do not add unused imports, do not extract functions.
- Apply the fix pattern from the Decision Tree
- Edit only the necessary lines
- Preserve existing comments and structure

### Step 3: Verify (cargo check only)
```bash
strix-build cargo check -p atlas-cli
```
**Do NOT run full tests locally.** `cargo check` is sufficient. Tests run in CI.

### Step 4: Commit → Push → Close
```bash
git add <specific-files>
git commit -m "fix(scope): description (#issue)"
git pull gitea main --rebase  # auto-version bump
git push gitea main
```
Close the Gitea issue via API.

## 📍 File Location Reference (with Line Ranges)
| Component | Path | Key Line Range |
|-----------|------|----------------|
| CLI command dispatch | `crates/atlas-cli/src/main.rs` | `~line 1490` (match block) |
| Command implementations | `crates/atlas-cli/src/commands/*.rs` | `~line 10-50` (entry points) |
| Config parser | `crates/atlas-config/src/lib.rs` | `~line 40-120` (`*Config` structs) |
| Config init writer | `crates/atlas-core/src/initialization.rs` | `~line 85-150` (`generate_config_content_fast`) |
| GraphFusion backend | `crates/atlas-cli/src/commands/backends/graphfusion_backend.rs` | `~line 20-90` |
| ADE reader/writer | `crates/atlas-cli/src/ade/mod.rs` | `~line 15-60` |
| Scan pipeline | `crates/atlas-cli/src/commands/scan/cmd.rs` | `~line 30-110` |
| Unit/Integration tests | `crates/atlas-cli/tests/*.rs` | `~line 1-50` (assert_cmd + tempfile patterns) |

## 🚫 Anti-Patterns (Concrete Examples)
| Anti-Pattern | Why It Fails | Correct Action |
|--------------|--------------|----------------|
| `"Fix the init bug"` | Agent reads 18 files, spends 15 min exploring | `"Edit crates/atlas-core/src/initialization.rs:112, change config_key to config_key_v2"` |
| Reading full files to "understand" | 5+ min per file, context window bloat | `grep -rn "error_marker" crates/` → jump to line |
| Running `cargo nextest run` locally | 2-10 min, flaky CI parity, wastes time | `cargo check -p atlas-cli` → CI runs full suite |
| Vague agent prompts | Agent reads 20+ files, guesses architecture | Precise: `"edit file.rs line 42, change X to Y"` |
| Multiple parallel agents on shared files | Merge conflicts, build contention, rollback loops | Sequential for shared files; parallel only for isolated modules |

## 📊 Performance & Rollout Baseline
| Metric | Target |
|--------|--------|
| Time to locate bug | <2 min |
| Time to fix | <5 min |
| Time to verify | <2 min (`cargo check`) |
| Total per fix | <10 min |
| Files read per fix | ≤3 |

**Historical Agent Rollout Data:**
- `atlas-127: Fix query --quiet` → 17min, 18 files read (vague prompt, 15 min exploration)
- `atlas-143: Fix atlas stats stub` → 0.5min, 1 file read (surgical, uncommented 1 line)
- `atlas-113: Fix atlas init TOML` → 2min, 3 files read (grep found mismatch instantly)
- `atlas-132: Smoke test init && scan && query` → 3min, 2 files read (reused existing test patterns)

**Rule:** If files read > 3 or time > 5 min, STOP. Re-run Step 1 with a more precise grep pattern.