---
name: rust-decouple
description: Rust Decouple — Trait-Based Module Extraction
---

# Rust Decouple — Trait-Based Module Extraction

## When to use
When extracting a tightly-coupled Rust module from a crate into a standalone crate (e.g., for the fabrik org). Use when a module depends on types from sibling modules that can't simply move together.

## Activation keywords
decouple, extract, untangle, standalone crate, trait-based extraction

## Process

### 1. Map the dependency graph

For each source file, list all `use crate::` imports. Categorize into:

- **Own types** — types defined in the module being extracted (move WITH it)
- **Shared types** — types used by multiple modules, not owned by any one (move to a core/types sub-module)
- **External traits** — behavior that varies by consumer (define trait interface)
- **Error types** — replace with crate-local error enum

### 2. Identify trait boundaries

For each "External traits" dependency, define a trait in the new crate:

```rust
/// Data source trait — consumer provides the data shape
pub trait DataSource {
    type Row;
    fn rows(&self) -> &[Self::Row];
    fn features(&self, idx: usize) -> &[f64];
    fn label(&self, idx: usize) -> f64;
}
```

Rules for traits:
- **Keep them minimal** — 2-5 methods max
- **Name after capability, not consumer** — `FeatureSource`, not `NtMlFeatureSource`
- **Use associated types** for domain-specific types that vary
- **Provide blanket impls** for common cases (e.g., `impl DataSource for Vec<LabeledRow>`)

### 3. Move shared types

Types that both the new crate and the old crate need:
- Move to the new crate if the new crate is the primary owner
- Move to a separate `fab-xyz-types` crate if truly shared
- Re-export from old location for backward compat

### 4. Error handling

Replace `crate::error::MlError` with a local error enum:

```rust
#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("invalid input: {0}")]
    InvalidInput(String),
    #[error("training failed: {0}")]
    TrainingFailed(String),
    #[error("{0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, Error>;
```

### 5. Extraction order

Follow the dependency DAG bottom-up:

```
Level 0 (no deps):  model types, error types, utils
Level 1 (deps on 0): gbdt training
Level 2 (deps on 0-1): conformal calibration
Level 3 (deps on 0-2): discovery pipeline
Level 4 (deps on 0-3): feature GA
```

Extract level 0 first, then level 1, etc. Each level must compile independently before moving to the next.

### 6. Verification

After extraction:
- New crate: `cargo clippy -- -W clippy::all -D warnings && cargo test`
- Old crate: `cargo check` + `cargo nextest run` (all existing tests pass)
- No public API changes in the old crate (re-exports maintain compatibility)

### 7. SOLID principles applied

- **S** (Single Responsibility): Each extracted crate owns one algorithm domain
- **O** (Open/Closed): Traits allow new consumers without modifying the crate
- **L** (Liskov): Trait impls must satisfy the trait's contract (test with generic consumers)
- **I** (Interface Segregation): Small, focused traits (not one mega-trait)
- **D** (Dependency Inversion): New crate depends on abstractions (traits), not concrete types

## Anti-patterns to avoid

- **God trait** — one trait with 20 methods. Split into focused traits.
- **Moving too much** — if you move LabeledRow, scorer, and feature_params, you've moved the whole crate. Stop and reconsider the boundary.
- **Stringly-typed errors** — don't use `String` everywhere. Use proper error variants.
- **Breaking the old API** — re-exports must preserve type identities. If nt-backtest uses `nt-ml::GbdtModel`, it must still compile.
