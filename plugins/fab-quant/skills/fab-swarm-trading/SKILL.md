---
name: fab-swarm-trading
description: fab-swarm Trading Integration
---

# fab-swarm Trading Integration

Reference for using fab-swarm's ML/analysis crates in the fab-trader backtest and signal pipeline.

## Dependency setup

Add to `crates/nt-ml/Cargo.toml` or `crates/nt-backtest/Cargo.toml`:

```toml
fab-learn = { path = "../../vendor/fab-swarm/fab-learn" }
fab-sheaf = { path = "../../vendor/fab-swarm/fab-sheaf" }
```

Transitive deps pulled in: `fab-sheaf`, `fab-brain`, `fab-types`. No NAPI needed for Rust-only usage.

## Module mapping to trading use cases

### 1. Conformal Prediction (`fab_learn::conformal`)

**Trading use case:** Calibrated confidence intervals on LightGBM forecasts for position sizing.

```rust
use fab_learn::{VacpPredictor, NonconformityScore, PredictionSet};

let mut predictor = VacpPredictor::new(0.1, 200); // alpha=0.1, 200-bar calibration window

// During backtest: calibrate on realized returns vs forecast
predictor.calibrate(NonconformityScore {
    value: (realized_return - forecast).abs(), // nonconformity score
    label: symbol.to_string(),
    actual: Some(realized_return),
    timestamp: bar_ts as u64,
});

// Before entry: get prediction interval
if let Some(pred) = predictor.predict(forecast, residual_estimate) {
    // pred.lower, pred.upper = 90% confidence interval
    // pred.confidence = 1 - alpha
    // pred.set_size = interval width (efficiency metric)
    //
    // Position sizing: scale by confidence, widen stop for wide intervals
    let size_mult = if pred.set_size > threshold { 0.5 } else { 1.0 };
}
```

**Key types:**
- `VacpPredictor::new(alpha, window)` — alpha=0.1 gives 90% coverage
- `PredictionSet { point_estimate, lower, upper, confidence, set_size, p_value }`
- `VacpState { calibration_size, empirical_coverage, is_well_calibrated }`

### 2. Drift Detection (`fab_learn::drift`)

**Trading use case:** Detect when the ML model's forecast accuracy degrades — trigger risk reduction or retraining.

```rust
use fab_learn::{DriftDetector, DriftAlert, DriftType};
use fab_learn::drift::MultiSiteDriftMonitor;

// Single metric drift
let mut detector = DriftDetector::new(0.15); // initial threshold
let alert = detector.check_for_drift(forecast_error);
if alert.drift_type.is_some() {
    // Drift detected! alert.severity 0.0-1.0
    // alert.requires_retraining() when severity > 0.7
}

// Per-instrument drift monitoring
let mut monitor = MultiSiteDriftMonitor::new();
monitor.register_site("AAPL".into(), 0.15);
monitor.register_site("MSFT".into(), 0.15);
// ...
if let Some(alert) = monitor.check_site_drift("AAPL", error) {
    if alert.requires_retraining() { /* reduce sizing */ }
}
```

**Key types:**
- `DriftDetector::new(threshold)` — ADWIN-based adaptive windowing
- `DriftAlert { drift_type: Option<DriftType>, severity, metric_name, previous_value, current_value }`
- `DriftType::{Real, Virtual, Seasonal, Novelty, Temporal}`
- `MultiSiteDriftMonitor` — per-instrument drift tracking

### 3. Uncertainty Quantification (`fab_learn::uncertainty`)

**Trading use case:** Gate auto-execution on signal confidence. Decompose epistemic (model) vs aleatoric (market noise) uncertainty.

```rust
use fab_learn::{UncertaintyEstimate, ContextualUncertainty, ApplicationContext};

let est = UncertaintyEstimate::new(
    forecast,        // point estimate
    epistemic_std,   // model uncertainty (reducible)
    aleatoric_std,   // market noise (irreducible)
    sample_count,
);

let ctx = ContextualUncertainty::from_estimate(est, ApplicationContext::FastDecisions);
// FastDecisions: acceptable_uncertainty = 0.5, weight = 0.5

if ctx.is_safe_for_automation() {
    // Auto-trade: confidence > 0.7 AND uncertainty acceptable
}

// Defer to human if:
// - epistemic dominant (model doesn't know) → gather more data
// - aleatoric dominant (market noisy) → accept wider stops
if est.is_epistemic_dominant() { /* skip or reduce size */ }
```

**Key types:**
- `UncertaintyEstimate::new(point, epistemic, aleatoric, n)` — auto-computes 95% CI
- `ContextualUncertainty::from_estimate(est, ApplicationContext::FastDecisions)`
- `ApplicationContext::{SafetyCritical, FastDecisions, Research, LongHorizon}`
- `is_safe_for_automation()` — combined check for auto-trade gating

### 4. Information Theory (`fab_sheaf::information`)

**Trading use case:** MI-based feature selection, ensemble weight rebalancing, signal redundancy detection.

```rust
use fab_sheaf::{entropy, kl_divergence, js_divergence, mutual_information};

// Feature selection: MI(feature, forward_return)
let mi = mutual_information(&feature_dist, &return_dist, &joint_dist).unwrap();

// Ensemble weight rebalancing: KL divergence between signal distributions
let divergence = kl_divergence(&current_signal_dist, &training_signal_dist).unwrap();
// High divergence → signal has shifted, reduce weight

// Signal redundancy: JS divergence between two signals
let redundancy = js_divergence(&signal_a_dist, &signal_b_dist).unwrap();
// Low JS → signals carry similar information → combine or drop one
```

**Key functions:**
- `entropy(dist)` — Shannon entropy in nats
- `kl_divergence(p, q)` — asymmetric, f64::INFINITY if q has zeros
- `js_divergence(p, q)` — symmetric, bounded [0, ln(2)]
- `mutual_information(px, py, pxy)` — pxy is flattened joint P(X=i, Y=j)

### 5. Signal Composition (`fab_sheaf::signal_composition`)

**Trading use case:** Replace fixed ensemble weights (0.50/0.20/0.15/0.15) with adaptive, confidence-aware multi-signal fusion.

```rust
use fab_sheaf::signal_composition::*;
use std::collections::HashMap;

// Define trading signals
let mut registry = SignalRegistry::new();
registry.register(SignalDefinition {
    key: "ml.forecast".into(),
    description: "LightGBM tabular forecast score".into(),
    normalizer: Normalizer::Identity,
    default_weight: 0.50,
});
registry.register(SignalDefinition {
    key: "momentum.rs".into(),
    description: "Relative strength momentum".into(),
    normalizer: Normalizer::MinMax { min: -1.0, max: 1.0 },
    default_weight: 0.20,
});
registry.register(SignalDefinition {
    key: "fundamental.score".into(),
    description: "Fundamental composite score".into(),
    normalizer: Normalizer::Identity,
    default_weight: 0.15,
});
registry.register(SignalDefinition {
    key: "llm.rank".into(),
    description: "LLM ranker score".into(),
    normalizer: Normalizer::Identity,
    default_weight: 0.15,
});

// Score with confidence
let mut measurements = HashMap::new();
measurements.insert("ml.forecast".into(), (0.72, 0.9));    // (value, confidence)
measurements.insert("momentum.rs".into(), (0.65, 0.8));
measurements.insert("fundamental.score".into(), (0.55, 0.7));
measurements.insert("llm.rank".into(), (0.80, 0.6));

let scorer = TaskFitnessScorer::new(registry, FitnessScorerConfig::default());
let (composite, explanation) = scorer.score(&measurements);
let agg_score = composite.aggregate(scorer.registry());

// Quality gate: reject weak entries
let judge = QualityGateJudge::new(GateConfig {
    min_composite_score: 0.5,
    thresholds: vec![GateThreshold {
        signal_key: "ml.forecast".into(),
        min_value: 0.3,
        hard: true,
        description: "ML forecast must exceed minimum".into(),
    }],
});
let decision = judge.judge(&composite, scorer.registry());
if decision.is_acceptable() { /* enter trade */ }
```

**Key types:**
- `SignalRegistry` — register signals with normalizers and default weights
- `Normalizer::{Identity, Invert, MinMax{min,max}, MinMaxInvert, Sigmoid{midpoint,steepness}}`
- `TaskFitnessScorer` — score measurements with confidence weighting
- `QualityGateJudge` — accept/reject based on thresholds
- `GateDecision::{Accept, ConditionalAccept, Reject}`

## Integration points in fab-trader

| fab-swarm module | fab-trader location | What changes |
|---|---|---|
| `conformal` | `run_backtest_gamma` sizing loop | Replace Kelly sizing with VACP confidence intervals |
| `drift` | `run_backtest_gamma` per-bar loop | Replace static regime_gate with adaptive drift detection |
| `uncertainty` | Entry gating in gamma backtest | Skip entries when epistemic uncertainty is high |
| `information` | `packages/screener` ensemble weights | Replace fixed weights with MI-optimized dynamic weights |
| `signal_composition` | Daily pick ensemble | Replace hardcoded weights with SignalRegistry + FitnessScorer |

## Build

```bash
# Check compilation with fab-learn/fab-sheaf
cargo check -p nt-backtest --features onnx --test gamma_config

# Run bear validation with new features
cargo nextest run -p nt-backtest --features onnx --test gamma_config gamma_u66_bear_validation -- --nocapture
```
