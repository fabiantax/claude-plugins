---
name: emd-optimization
description: EMD/CEEMDAN Cycle Detection Optimization
---

# EMD/CEEMDAN Cycle Detection Optimization

Skill for implementing SOTA EMD techniques in fab-trader's pullback model, based on 2024-2026 literature review.

## Quick Reference

**Benchmark script:** `scripts/emd_macro_benchmark_v2.py`
**Optimization log:** `docs/research/emd_optimization_log.md`
**Literature review:** `docs/research/emd_literature_review_2026.md`
**Training data:** `data/training_features_universe_pullback.parquet`
**EMD cache:** `data/emd_results/macro_per_imf_scores.parquet`

## Current State

- AUC: 0.8675 (+0.72% over baseline)
- WR: 51.3% at 0.50 threshold (54.7% at 0.55, 55.9% at 0.60)
- 11 macro ratios, 6 IMF slots × 5 features = 330 IMF features
- Optimal params: window=120, n_ensembles=4, max_qualifying=6

## Known Issues

1. **n_ensembles=4 has ~50% residual noise** per IMF — need 50-100
2. **No boundary correction** — last 5-10 bars unreliable (mirror extension needed)
3. **No IMF significance test** — feeding noise IMFs into model
4. **Missing Kuramoto phase coherence** — strongest missing single feature
5. **Missing freq acceleration** — leading indicator 2-5 bars before turning point

## Implementation Priority

### P0 (Critical — material AUC improvement expected)

1. **Increase CEEMDAN ensembles to 50-100**
   - Change `N_ENSEMBLES = 4` to `N_ENSEMBLES = 50` in script
   - Must recompute (remove `--skip-emd` or delete cache)
   - Runtime: ~12.5 min for 50 ensembles (vs ~2.5 min for 4)

2. **Mirror boundary extension**
   - Wrap `rolling_emd_per_imf_features()` to extend input before CEEMDAN
   - Extend by min(window//4, 50) samples each side
   - Trim IMFs back to original length after decomposition

3. **Kuramoto phase coherence**
   - Add `kuramoto_r` feature per ratio per bar
   - Formula: `r = |sum(exp(i*phase_k)) / N|` across qualifying IMFs
   - r > 0.7 = strong cycle alignment = major turning point

### P1 (High Impact)

4. **Wu-Huang significance test** — filter noise IMFs before feature extraction
5. **Frequency acceleration** — `np.diff(inst_freq)[-1]` as new feature per IMF
6. **Energy-weighted phase product** — `sum(energy_weight * -cos(phase))` per ratio

### P2 (Moderate Impact)

7. **GMM IMF grouping** — classify IMFs into high/med/low/trend, zero-crossing signals
8. **IMF lead-lag** — cross-correlation between adjacent IMFs

## Running Experiments

```bash
# Full run (recompute EMD)
cd ~/Developer/personal/fab-trader
scripts/.venv/bin/python scripts/emd_macro_benchmark_v2.py

# Skip EMD computation, use cache
scripts/.venv/bin/python scripts/emd_macro_benchmark_v2.py --skip-emd

# Custom parameters
scripts/.venv/bin/python scripts/emd_macro_benchmark_v2.py --window 120 --n-ensembles 50 --no-mlflow

# Feature selection
scripts/.venv/bin/python scripts/emd_macro_benchmark_v2.py --skip-emd --top-n 100

# More trees
scripts/.venv/bin/python scripts/emd_macro_benchmark_v2.py --skip-emd --n-estimators 1000
```

## Key Code Locations

| File | What |
|------|------|
| `scripts/emd_macro_benchmark_v2.py` | Main benchmark script |
| `scripts/emd_cycle_pipeline.py` | Original valley scanner (complementary) |
| `scripts/fetch-regime-data.ts` | Fetches ETF bars from Alpaca |
| `data/regime/*.json` | ETF OHLCV bars (GLD, XLE, TLT, etc.) |
| `data/emd_results/macro_per_imf_scores.parquet` | Cached per-IMF features |

## Feature Engineering Recipes

### Kuramoto Phase Coherence (NEW)
```python
def kuramoto_r(phases):
    return abs(sum(np.exp(1j * p) for p in phases) / len(phases))
# phases = [np.angle(hilbert(imf))[-1] for imf in qualifying_imfs]
```

### Frequency Acceleration (NEW)
```python
unwrapped = np.unwrap(phase)
inst_freq = np.diff(unwrapped) / (2 * np.pi)
freq_accel = np.diff(inst_freq)[-1]  # leading indicator
```

### Energy-Weighted Valley Score (NEW)
```python
energies = np.array([np.mean(imf[-20:]**2) for imf in imfs])
weights = energies / (energies.sum() + 1e-10)
valley_score = np.sum(weights * (-np.cos(phases)))
```

### Mirror Extension (NEW)
```python
n_ext = min(len(signal) // 4, 50)
extended = np.concatenate([signal[n_ext:0:-1], signal, signal[-1:-n_ext-1:-1]])
# Run CEEMDAN on extended, trim back
```

## Target Metrics

| Stage | WR @ 0.55 | AUC | What |
|-------|-----------|-----|------|
| Current | 54.7% | 0.8675 | Per-IMF CEEMDAN, n=4 |
| +P0 | 58-62% | 0.88? | Ensemble 100, mirror, Kuramoto |
| +P1 | 62-68% | 0.89? | Significance test, freq accel, energy product |
| +P2 | 68-75% | 0.90? | IMF reconstruction, lead-lag |
| +Architecture | 80-85% | 0.92? | Conformal prediction, per-instrument models |
