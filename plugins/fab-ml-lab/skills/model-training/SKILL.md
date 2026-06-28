---
name: model-training
description: Model Training — Canonical Workflow
---

# Model Training — Canonical Workflow

How to train, export, log, backtest, and compare ML models in fab-trader.

## Repos

| Repo | Location | What |
|------|----------|------|
| fab-trainer | `~/Developer/personal/fab-trainer/` | Python ML training, ONNX/GBDT export, experiment logging |
| fab-trader | `~/Developer/personal/fab-trader/` | Rust inference, backtesting, API, CLI |

Both share `data/experiments/experiments.duckdb` (training_runs + backtest_runs tables).

## Available training scripts

| Script | What | When to use |
|--------|------|-------------|
| `fab-trainer/scripts/train_lgbm_parquet.py` | Primary pullback model trainer (per-instrument + universal) | Default for pullback signal models |
| `fab-trainer/scripts/train_lightgbm.py` | General LGB + XGB trainer | Quick experiments, non-pullback targets |
| `fab-trainer/scripts/train_regime_classifier.py` | Regime (bull/bear) classifier | Regime gate models |
| `fab-trainer/scripts/train_cpd_meta.py` | CPD meta-learner | Change point detection tuning |
| `fab-trainer/scripts/shap_ablation.py` | SHAP feature importance + ablation | Feature selection validation |
| `fab-trainer/scripts/tail_gan_v3.py` | Tail-GAN stress scenarios | VaR/ES stress testing |
| `fab-trainer/scripts/emd_macro_benchmark_v2.py` | EMD cycle detection benchmark | IMF feature experiments |

## Canonical training command

```bash
cd ~/Developer/personal/fab-trainer
source .venv/bin/activate

# Train pullback model (primary)
python scripts/train_lgbm_parquet.py \
  --input data/training_features_universe_pullback.parquet \
  --output-dir models/ \
  --name my_experiment \
  --n-estimators 500 \
  --mi-filter 0.5

# Results auto-logged to data/experiments/experiments.duckdb
```

## Experiment store operations (fab-trader CLI)

```bash
# View training runs
fab experiment training-list
fab experiment training-list --experiment my_experiment

# View training run details
fab experiment training-show <run-id>

# Save a backtest run (links to training via model_version)
fab experiment save --metrics metrics.json --experiment my_exp --tag v3.5

# Compare training metrics vs backtest results
fab experiment compare-versions
fab experiment compare-versions --experiment my_exp

# Compare backtest runs directly
fab experiment compare run1,run2
fab experiment list
fab experiment show <run-id>
```

## API endpoints (HQ Dashboard)

```
GET /hq/data/training           → list training runs
GET /hq/data/training/:runId    → single training run
GET /hq/data/model-comparison   → training AUC vs backtest Sharpe/Return
GET /hq/data/runs               → backtest runs (top by Sharpe)
GET /hq/data/runs/:runId        → single backtest run
```

## Rules

1. **Never create a new training script.** Use one from the table above. If none fits, extend an existing one.
2. **Never skip `save_training_run()`.** Every training run must be logged.
3. **Never skip `fab experiment save`.** Every backtest run must be persisted.
4. **Temporal splits only.** Never random train/test on time series.
5. **Compare before concluding.** Use `fab experiment compare-versions` before declaring improvement.
6. **OOS mandatory.** Never deploy IS-only results. Always show IS + OOS side by side.

## fab_ml library modules

| Module | Key functions |
|--------|---------------|
| `fab_ml/paths.py` | `DATA_DIR`, `MODELS_DIR`, `EXPERIMENTS_DB` |
| `fab_ml/data.py` | `temporal_split()`, `stock_oos_split()`, `load_parquet()` |
| `fab_ml/train.py` | `train_lgb()`, `train_xgb()` |
| `fab_ml/features.py` | `mi_rank()`, `filter_features()` |
| `fab_ml/evaluate.py` | `compute_metrics()`, `classification_report()` |
| `fab_ml/export.py` | `export_gbdt_json()`, `export_onnx()` |
| `fab_ml/experiment_store.py` | `save_training_run()`, `query_training_runs()`, `compare_with_baseline()` |
| `fab_ml/forecasting.py` | Foundation model fine-tuning utilities |
