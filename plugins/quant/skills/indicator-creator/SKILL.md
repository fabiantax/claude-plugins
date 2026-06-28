---
name: indicator-creator
description: Add a new technical indicator to nt-indicators — canonical Rust impl, tests, NAPI wiring, feature pipeline integration, and optional Python research counterpart.
argument-hint: "\"<indicator-name>\" — e.g. 'hma' or 'supertrend_v2'"
---

# /indicator-creator — add a new indicator to nt-indicators

Creates a production-ready indicator following the crate's established conventions. Covers: Rust implementation, tests, lib.rs registration, NAPI binding, feature pipeline wiring, and optional Python research copy for sweep scripts.

## When to use

- Adding any new technical indicator or filter kernel to `crates/nt-indicators/`.
- Adding a derived feature (e.g. `proximity_to_high`, `vol_range_ratio`) that follows the same function signature pattern.
- **NOT for**: regime classifiers (those go in `regime_rsx` / `regime_cpd`), multi-output indicators with complex struct returns (those are fine — just follow the pattern below).

---

## Step 1 — Check for existing implementations

```bash
# 1. Grep for the indicator name across the codebase
rg -i "<indicator>" crates/nt-indicators/src/
rg -i "<indicator>" crates/nt-ml/src/feature_universe.rs

# 2. Check if it's already a feature
rg -i "<indicator>" crates/nt-ml/src/feature_universe.rs

# 3. Check NAPI exposure
rg -i "<indicator>" crates/nt-napi/src/
```

If it already exists, **extend it** rather than creating a new file. If a Python version exists in a sweep script, that's research-only — the Rust version is canonical.

---

## Step 2 — Create the Rust file

File: `crates/nt-indicators/src/<name>.rs`

### Mandatory structure

```rust
//! <One-line description> — <citation or "from first principles">.
//!
//! <2-5 line algorithm summary. If the algorithm has non-obvious
//! interpretation choices, flag them explicitly in a numbered list.>
//!
//! Reference: <URL or paper citation>

use crate::error::{IndicatorError, IndicatorResult};

/// <One-line description of the indicator function>.
///
/// # Parameters
/// - `series` — input price or indicator series.
/// - `period` — <what it controls>.
///
/// # Errors
/// - `InvalidPeriod` when `period == 0`.
/// - `InsufficientData` when series is shorter than warmup requirement.
///
/// # Output
/// <Describe warmup behavior (NaN prefix), bounds, edge cases.>
pub fn <name>(series: &[f64], period: usize) -> IndicatorResult<Vec<f64>> {
    if period == 0 {
        return Err(IndicatorError::InvalidPeriod(0));
    }
    let n = series.len();
    // Warmup check — adjust to your algorithm's needs.
    if n < period {
        return Err(IndicatorError::InsufficientData { need: period, got: n });
    }

    let mut out = vec![f64::NAN; n];

    // ... algorithm here ...

    Ok(out)
}
```

### Critical rules for the implementation body

1. **Input type: `&[f64]`** — never `Vec<f64>` (avoids ownership transfer; caller retains the buffer).
2. **Output type: `IndicatorResult<Vec<f64>>`** — always `Vec<f64>` same length as input.
3. **Pre-allocate output**: `let mut out = vec![f64::NAN; n];` or `Vec::with_capacity(n)`.
4. **NaN warmup**: positions `0..warmup` must be `f64::NAN`. Never 0.0 — zero is a valid indicator value and silently corrupts downstream calculations.
5. **No panic**: every `series[i]` access is bounds-checked by the compiler. No `unwrap()` on user-controlled values. Use `is_finite()` guards for NaN input.
6. **No allocations in the hot loop**: pre-allocate all buffers before the main loop. No `Vec::push()` inside a tight loop unless using `with_capacity` and the push is amortized O(1).
7. **Scalar state machines**: for per-bar state (Kalman, JMA, EMA, etc.), use plain `f64` variables — NOT arrays or matrices. Inline 2×2 matrix math as individual scalar operations (see `kalman.rs` for the pattern). This eliminates per-iteration allocation overhead.
8. **`#[inline]` on helpers**: small pure functions called in the hot loop get `#[inline]`.

### Function signature variants

| Shape | When to use | Signature |
|-------|-------------|-----------|
| Single-input, single-period | Most indicators | `fn(series: &[f64], period: usize) -> IndicatorResult<Vec<f64>>` |
| Two-input | Correlation, regression | `fn(x: &[f64], y: &[f64], period: usize) -> IndicatorResult<Vec<f64>>` |
| Multi-param | Kalman (q, r), JMA (length, phase, power) | `fn(series: &[f64], p1: f64, p2: f64) -> IndicatorResult<Vec<f64>>` |
| Struct return | MACD, Bollinger, etc. | `fn(...) -> IndicatorResult<StructName>` where `StructName` has named `Vec<f64>` fields |

---

## Step 3 — Register in lib.rs

File: `crates/nt-indicators/src/lib.rs`

Add **two** lines:

```rust
// Module declaration (alphabetical within its section):
pub mod <name>;

// Re-export (alphabetical within its section):
pub use <name>::<name>;
```

For struct-returning indicators, also re-export the struct:

```rust
pub use <name>::{<name>, <StructName>};
```

---

## Step 4 — Write tests

Tests go in the same file, in a `#[cfg(test)] mod tests { ... }` block at the bottom.

### Required test cases (minimum 5)

| Test | What it verifies |
|------|-----------------|
| `<name>_output_length_matches_input` | `out.len() == input.len()` |
| `<name>_warmup_is_nan` | positions `0..warmup` are NaN |
| `<name>_deterministic` | same input → same output |
| `<name>_invalid_period` | `period == 0` returns `InvalidPeriod` error |
| `<name>_insufficient_data` | too-short input returns `InsufficientData` error |

### Additional tests for specific algorithms

| When | Add test |
|------|----------|
| Indicator has bounded output (RSI, stoch, %R) | `bounded_0_to_100` or similar |
| Indicator should follow a trend | `follows_trend` — monotone input → monotone or correctly-signed output |
| Indicator should converge on constant input | `constant_series_converges` |
| NaN input handling is non-trivial | `leading_nan_produces_finite_output`, `interspersed_nan` |
| Known reference values exist (TA-Lib, papers) | `known_dataset` with exact expected values |

### Test helper

```rust
fn approx_eq(a: f64, b: f64, tol: f64) -> bool {
    (a - b).abs() < tol
}
```

Put this inside the `mod tests` block — it's used by nearly every test.

---

## Step 5 — NAPI binding (if TypeScript needs it)

File: `crates/nt-napi/src/indicators.rs`

Add the import at the top:

```rust
use nt_indicators::<name> as ind_<name>;
```

Add the binding function:

```rust
/// <One-line description>.
///
/// Returns a `Float64Array` of the same length as `values`.
/// Warmup positions are `NaN`.
#[napi]
pub fn <name>(values: Float64Array, period: u32) -> NapiResult<Float64Array> {
    let out = ind_<name>(values.as_ref(), period as usize).map_err(indicator_err)?;
    Ok(Float64Array::new(out))
}
```

For multi-param indicators:

```rust
#[napi]
pub fn kalman_smooth(values: Float64Array, process_noise: f64, measurement_noise: f64) -> NapiResult<Float64Array> {
    let out = ind_kalman_smooth(values.as_ref(), process_noise, measurement_noise).map_err(indicator_err)?;
    Ok(Float64Array::new(out))
}
```

Rebuild:

```bash
cargo build --release -p nt-napi
```

---

## Step 6 — Feature pipeline wiring (if used in ML)

File: `crates/nt-ml/src/feature_universe.rs`

Add feature computation inside `extract_features_full()`:

```rust
// <Indicator> features
let <name>_vals = nt_indicators::<name>(&close, <period>).unwrap_or_else(|_| vec![f64::NAN; n]);
names.push(format!("<name>_{}", <period>));
cols.push(<name>_vals);
```

For percentage-from-indicator features (common for moving averages):

```rust
let <name>_pct: Vec<f64> = close.iter().zip(<name>_vals.iter())
    .map(|(&c, &v)| if c > 0.0 && v.is_finite() { (c - v) / v } else { 0.0 })
    .collect();
names.push(format!("<name>_{}_pct", <period>));
cols.push(<name>_pct);
```

Then update the feature count in the doc comment at the top of the function.

---

## Step 7 — Optional Python research copy

For sweep scripts that need a Python version (to avoid NAPI round-trips during parameter sweeps):

File: `scripts/sweep_<something>.py` (inline in the script)

### Python performance rules

1. **Scalar state machines**: for Kalman/JMA/EMA-like per-bar filters, unroll matrix math to plain `float` operations. No numpy matmul inside a per-bar loop — the array creation overhead is ~100× the math.

```python
# GOOD — scalar Kalman (from sweep_gate_params.py)
def kalman_smooth(series: np.ndarray, q: float, r: float) -> np.ndarray:
    arr = np.asarray(series, dtype=np.float64)
    n = len(arr)
    out = np.empty(n)
    level = arr[0]
    vel = 0.0
    p00, p01, p11 = 1.0, 0.0, 1.0
    for i in range(n):
        pred_level = level + vel
        pp00 = p00 + 2.0 * p01 + p11 + q
        pp01 = p01 + p11
        pp11 = p11 + q
        v = arr[i]
        if v == v:  # isfinite
            innov = v - pred_level
            S = pp00 + r
            if S > 0:
                K0 = pp00 / S
                K1 = pp01 / S
                level = pred_level + K0 * innov
                vel = vel + K1 * innov
                p00 = pp00 - K0 * pp00
                p01 = pp01 - K0 * pp01
                p11 = pp11 - K1 * pp01
            else:
                level = pred_level
                p00, p01, p11 = pp00, pp01, pp11
        else:
            level = pred_level
            p00, p01, p11 = pp00, pp01, pp11
        out[i] = level
    return out
```

2. **Vectorized windowed ops**: use `numpy.lib.stride_tricks.sliding_window_view` for rolling max/min/sum — 10-20× faster than Python for-loops.

3. **Pre-allocate**: `np.empty(n)` or `np.zeros(n, dtype=np.int32)` — never append in a loop.

4. **Explicit dtype**: always `dtype=np.float64` or `dtype=np.int32`. Never rely on default inference.

5. **Direct numpy from pyarrow**: `table.column("close").to_numpy()` not `.to_pylist()` — avoids Python list intermediate.

6. **Instrument index for parquet**: pre-build `{name: (start_row, n_rows)}` once — O(n) total, not O(n) per config.

### NOT for production

Python versions are **research-only** — they exist in sweep scripts for speed during parameter exploration. The Rust version in `nt-indicators` is always the canonical implementation. Python copies must match the Rust output (verify with known test vectors).

---

## Step 8 — Verify

```bash
# 1. Compile check
cargo check -p nt-indicators

# 2. Run indicator tests
cargo nextest run -p nt-indicators

# 3. If NAPI binding added
cargo build --release -p nt-napi

# 4. If feature pipeline changed, check downstream
cargo check -p nt-ml
cargo check -p nt-backtest

# 5. Full test suite (if touching shared code)
cargo nextest run -p nt-backtest
```

---

## Checklist (verify before committing)

- [ ] File follows naming: `crates/nt-indicators/src/<name>.rs`
- [ ] Input type is `&[f64]`, output is `IndicatorResult<Vec<f64>>` (or struct with `Vec<f64>` fields)
- [ ] NaN warmup prefix (never 0.0)
- [ ] No panics — all user-controlled values guarded
- [ ] No allocations in hot loop — pre-allocated buffers only
- [ ] Scalar state for per-bar filters (no numpy-like matrix ops)
- [ ] `#[inline]` on hot-path helpers
- [ ] Module + re-export added to `lib.rs`
- [ ] Minimum 5 test cases (length, warmup, deterministic, invalid_period, insufficient_data)
- [ ] NAPI binding in `crates/nt-napi/src/indicators.rs` (if TS needs it)
- [ ] Feature pipeline entry in `feature_universe.rs` (if ML needs it)
- [ ] Python research copy follows scalar/vectorized rules (if sweep script needs it)
- [ ] `cargo nextest run -p nt-indicators` green
