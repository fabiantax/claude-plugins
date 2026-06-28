---
name: skillopt-rust-bugfix
version: 0.3.0
description: Zero-exploration workflow for Rust CLI — enforce agent delegation for features, surgical search for bugfixes, and minimal context loading
allowed-tools: Read Bash Edit Write Grep Glob
---

# Rust Workflow (Atlas CLI)

## 🔒 Hard Rule: Agent Delegation (MANDATORY)

**Source authority: `CLAUDE.md` — "Agent Delegation MANDATORY" section.**

> **>30 LOC of new code OR >1 new file → spawn coder-agent team.**
> Zero exceptions. Inline writes for feature-scale work are the #1 cause of compile-error cascades and context-window bloat.

Why: A single agent writing 4 modules inline cannot `cargo check` until all 4 are complete. Compile errors in module 1 poison modules 2-4. Parallel coder agents each `cargo check` independently, catching errors in <2 min instead of at the end of a 35-min write.

---

## 🏗 Feature Implementation Workflow

### Step 0: Classify Scope (30 seconds)
```
if task == "new CLI subcommand" or ">1 new file":
    → Feature Workflow (this section)
elif task == "edit existing code to fix error/panic/stub":
    → Bugfix Workflow (below)
else:
    → Bugfix Workflow (below)
```

### Step 1: Decompose into Agent Units
Break the feature into **independent file-level units**. Each unit becomes one coder agent.

**Decision Tree:**

| Task Type | Agent Spawn Plan |
|-----------|-----------------|
| New CLI subcommand | 3 parallel coder agents: (1) CLI struct + clap args, (2) command impl module, (3) dispatch wiring in main.rs. Then 1 integration-test agent after merge. |
| Single new module (>30 LOC) | 1 coder agent. **Never inline.** Main context does `Read` + `grep` only, hands off to coder. |
| Multi-file refactor | 1 coder agent per independent file, parallel. 1 synthesis agent for cross-file wiring. |
| New module + existing file edits | Coder agent owns the new module. Main context does surgical edits on existing files (≤10 LOC per file). |

### Step 2: Prepare Minimal Context Per Agent
Each coder agent receives:
- Exact file path to create/edit
- Relevant struct signatures / trait bounds (copy-paste, not file references)
- Cargo.toml dependency line if new dep needed
- **One sentence** of what the module must do

**Do NOT pass the entire codebase to a coder agent.** Pass only what it needs.

### Step 3: Parallel Spawn
```
spawn coder-agent-1: "Create crates/atlas-cli/src/commands/wire/mod.rs implementing X. Use these types: {types}. Target: cargo check passes."
spawn coder-agent-2: "Create crates/atlas-cli/src/commands/wire/mcp_json.rs implementing Y..."
spawn coder-agent-3: "Create crates/atlas-cli/src/commands/wire/settings_merge.rs implementing Z..."
# All 3 run in parallel. Each runs cargo check independently.
```

### Step 4: Integrate + Verify
After coder agents return:
1. Main agent wires dispatch in `main.rs` (surgical edit, ≤15 LOC)
2. `strix-build cargo check -p atlas-cli`
3. If compile errors → fix in the specific module's coder agent, not inline

### Step 5: Commit → Push → Close
```bash
git add <specific-files>
git commit -m "feat(scope): description (#issue)"
git pull gitea main --rebase
git push gitea main
```

### 🚫 Feature Anti-Pattern
| What Happened | Why It Failed | Correct Action |
|---------------|---------------|----------------|
| **fab-swarm-83-wire-impl**: Agent wrote 906 LOC inline across `cli/wire.rs` + `commands/wire/{mod,mcp_json,settings_merge}.rs` in 35 min. Compile errors (private-module path, missing `use`) surfaced only after all 4 modules written. | Violated delegation rule. Single context = no incremental `cargo check`. | 3 parallel coder agents (one per module) + 1 integration agent for dispatch wiring. Estimated ~12 min. Errors caught per-module in <2 min. |

---

## 🐛 Bugfix Workflow (Surgical)

### Pre-Edit Checklist (Mandatory Gate)
**DO NOT EDIT UNTIL ALL CONFIRMED.**
- [ ] Identified exact error message, panic string, or failing assertion
- [ ] Ran `grep -rn` to locate: (1) manifesting file, (2) schema/contract file, (3) existing test file
- [ ] Classified bug type using the Decision Tree below
- [ ] Drafted edit: `edit <file>:<line> change <X> to <Y>`

### Fix-Type Decision Tree
| Symptom / Keyword | Bug Type | Surgical Fix Pattern |
|-------------------|----------|----------------------|
| `serde: missing field`, `TOML parse error`, `init` rejects config | `serde_default` | Add `#[serde(default)]` or `#[serde(default = "fn")]`. Do not rewrite the writer. |
| `// commented out`, `bail!("not yet implemented")`, `todo!()` | `commented_out` | Uncomment. Fix signature to match current API. Remove `bail!`/`todo!`. |
| `--quiet` ignored, `--verbose` inverted, flag not propagating | `flag_logic` | Flip boolean condition. Add early return/guard. Match CLI arg parsing to command dispatch. |
| `format!` mismatch, `Display` impl missing | `fmt` | Update format string args. Fix type conversion. |
| `panic!`, `unwrap()`, `expect()` on `None`/`Err` | `missing_guard` | Replace with `?` or `ok_or_else!()`. Add explicit error mapping. |

### Step 1: Locate (≤2 min)
```bash
grep -rn "TODO\|FIXME\|bail!\|unimplemented\|todo!" crates/atlas-cli/src/
grep -rn "exact-error-message" crates/
```
Identify exactly 3 files: (1) manifesting file, (2) schema file, (3) test file.

### Step 2: Fix (surgical edit)
Apply fix pattern from Decision Tree. Edit only necessary lines. Preserve existing style.

### Step 3: Verify
```bash
strix-build cargo check -p atlas-cli
```

### Step 4: Commit → Push → Close
```bash
git add <specific-files>
git commit -m "fix(scope): description (#issue)"
git pull gitea main --rebase
git push gitea main
```

---

## 📍 File Location Reference
| Component | Path | Key Lines |
|-----------|------|-----------|
| CLI dispatch | `crates/atlas-cli/src/main.rs` | `~1490` (match block) |
| Command impls | `crates/atlas-cli/src/commands/*.rs` | `~10-50` (entry points) |
| Config parser | `crates/atlas-config/src/lib.rs` | `~40-120` (`*Config` structs) |
| Config init writer | `crates/atlas-core/src/initialization.rs` | `~85-150` |
| GraphFusion backend | `crates/atlas-cli/src/commands/backends/graphfusion_backend.rs` | `~20-90` |
| ADE reader/writer | `crates/atlas-cli/src/ade/mod.rs` | `~15-60` |
| Scan pipeline | `crates/atlas-cli/src/commands/scan/cmd.rs` | `~30-110` |
| Tests | `crates/atlas-cli/tests/*.rs` | `~1-50` |

## 📊 Performance Targets
| Metric | Bugfix | Feature |
|--------|--------|---------|
| Time to locate | <2 min | <3 min (decompose) |
| Time to implement | <5 min | <15 min (parallel agents) |
| Files read (main context) | ≤3 | ≤5 (scan only, no writes) |
| Inline LOC written by main agent | ≤10 | **0** (delegate all) |

**Rule:** If bugfix files read >3 or time >5 min, STOP. Re-grep with a more precise pattern.

## 🔄 SkillOpt Re-optimization
Add rollout data to `scripts/skillopt-optimize-skill.py` → `python3 scripts/skillopt-optimize-skill.py` → `diff SKILL.md rust-bugfix_optimized.md` → `cp` if improved.