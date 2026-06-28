---
name: mlflow-experiments
description: MLflow Experiment Tracking
---

# MLflow Experiment Tracking

## When to Use
- Any ML/AI experiment tracking: training runs, evaluations, benchmarks
- Tracking backtest runs: metrics, params, artifacts
- Comparing model versions or strategy versions
- Visualizing metric trends, parameter sweeps, equity curves
- Syncing local experiment stores (DuckDB, SQLite) to MLflow for UI exploration
- Model registry: versioning, staging, promoting models
- Hyperparameter sweeps and analysis

## Setup

| What | Value |
|------|-------|
| Package | `mlflow>=3.11` (installed in project `.venv`) |
| Tracking store | `data/experiments/mlflow.db` (SQLite) |
| DuckDB source | `data/experiments/experiments.duckdb` |
| Bridge script | `scripts/mlflow_bridge.py` |
| Python | Must use `.venv/bin/python` (system Python 3.14 lacks deps) |
| Seed script | `scripts/seed_experiments.py` (demo data) |

## MCP Server (Claude Code Integration)

Configured in `.mcp.json` — Claude Code can query experiments, compare runs, and manage models directly.

| What | Value |
|------|-------|
| Package | `mlflow-mcp>=0.4.0` (installed in `.venv`) |
| Config | `.mcp.json` in project root |
| Binary | `.venv/bin/mlflow-mcp` |
| Source | https://github.com/kkruglik/mlflow-mcp |

Capabilities: list/search experiments, query runs, compare metrics, browse artifacts, manage model registry.

**IMPORTANT:** The MLflow server must be running first (`mlflow ui` on port 5000) for the MCP to work.

## Quick Commands

### Step 1: Start server (always first)
```bash
# Start UI (accessible from all hosts via Tailscale)
MLFLOW_TRACKING_URI="sqlite:///$(pwd)/data/experiments/mlflow.db" \
  .venv/bin/mlflow ui --host 0.0.0.0 --port 5000 --allowed-hosts "*" --cors-allowed-origins "*"

# Start UI (localhost only)
MLFLOW_TRACKING_URI="sqlite:///$(pwd)/data/experiments/mlflow.db" \
  .venv/bin/mlflow ui --port 5000
```

### Step 2: Sync DuckDB → MLflow via REST API (not direct SQLite!)
```bash
# IMPORTANT: Always sync via http:// — NOT sqlite:///
# Direct SQLite writes bypass the running server's cache

# Sync all runs
MLFLOW_TRACKING_URI="http://127.0.0.1:5000" .venv/bin/python scripts/mlflow_bridge.py

# Sync filtered
MLFLOW_TRACKING_URI="http://127.0.0.1:5000" .venv/bin/python scripts/mlflow_bridge.py --experiment v3-holdout
MLFLOW_TRACKING_URI="http://127.0.0.1:5000" .venv/bin/python scripts/mlflow_bridge.py --tag v3.4
```

### Stop
```bash
pkill -f "mlflow ui"
```

## Data Flow

```
Rust backtest (gamma_config.rs save_run)
  → DuckDB backtest_runs table (packages/core/src/db/experiments.ts)
    → MLflow bridge (scripts/mlflow_bridge.py)
      → MLflow SQLite store (data/experiments/mlflow.db)
        → MLflow UI (:5000)
```

The bridge reads from DuckDB and writes to MLflow. It's one-way: DuckDB is source of truth, MLflow is for visualization.

## MLflow Python SDK Reference

### Setup
```python
import mlflow

# SQLite local tracking
mlflow.set_tracking_uri("sqlite:///data/experiments/mlflow.db")

# Or use environment variable
# export MLFLOW_TRACKING_URI="sqlite:///data/experiments/mlflow.db"

# Set (and auto-create) experiment
mlflow.set_experiment("my-experiment")

# Check current experiment
exp = mlflow.get_experiment_by_name("my-experiment")
print(exp.experiment_id, exp.name)
```

### Log a run
```python
with mlflow.start_run(run_name="run-001", tags={"version_tag": "v3.4"}):
    # Params (immutable per run — logged once)
    mlflow.log_params({
        "learning_rate": 0.001,
        "batch_size": 32,
        "model_arch": "transformer",
    })

    # Metrics (single values — last value wins)
    mlflow.log_metrics({
        "accuracy": 0.92,
        "f1_score": 0.89,
        "loss": 0.13,
    })

    # Time series metrics (call with different steps)
    for epoch in range(10):
        train_loss = train_one_epoch()
        val_loss = validate()
        mlflow.log_metric("train_loss", train_loss, step=epoch)
        mlflow.log_metric("val_loss", val_loss, step=epoch)

    # Artifacts (files)
    mlflow.log_artifact("config.json", artifact_path="config")
    mlflow.log_artifact("results.csv", artifact_path="results")

    # Figures (matplotlib/plotly)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])
    mlflow.log_figure(fig, "plot.png")

    # Tags (mutable, searchable)
    mlflow.set_tag("framework", "pytorch")
    mlflow.set_tag("instruments", "AAPL,MSFT,GOOGL")

    # Dictionary/dataset logging
    mlflow.log_dict({"key": "value"}, "metadata.json")

    # Text logging
    mlflow.log_text("Training completed successfully", "notes.txt")
```

### Query runs
```python
import mlflow

# Pandas DataFrame with all metrics/params
df = mlflow.search_runs(
    experiment_names=["my-experiment"],
    filter_string="metrics.accuracy > 0.9",
    order_by=["metrics.accuracy DESC"],
    max_results=10,
)

# Access columns: df["metrics.accuracy"], df["params.learning_rate"], etc.
# df["run_id"], df["tags.framework"], df["status"]
```

### Advanced filtering
```python
# Filter by params
df = mlflow.search_runs(
    filter_string="params.model_arch = 'transformer' AND params.batch_size = '32'"
)

# Filter by tags
df = mlflow.search_runs(
    filter_string="tags.framework = 'pytorch'"
)

# Filter by status
df = mlflow.search_runs(
    filter_string="status = 'FINISHED'"
)

# Filter by time
df = mlflow.search_runs(
    filter_string="attributes.start_time > '2025-01-01'"
)

# Combined
df = mlflow.search_runs(
    experiment_names=["my-experiment"],
    filter_string="metrics.accuracy > 0.9 AND params.learning_rate < 0.01",
    order_by=["metrics.accuracy DESC"],
    max_results=50,
)
```

### Low-level client
```python
from mlflow.tracking import MlflowClient
client = MlflowClient()

# List experiments
experiments = client.search_experiments()
for exp in experiments:
    print(exp.experiment_id, exp.name)

# Get specific run
run = client.get_run("run-uuid-here")
print(run.data.metrics)
print(run.data.params)
print(run.info.tags)
print(run.info.status)
print(run.info.start_time, run.info.end_time)

# Download artifact
client.download_artifacts("run-uuid", "config/config.json")

# List artifacts
artifacts = client.list_artifacts("run-uuid")
for a in artifacts:
    print(a.path, a.is_dir, a.file_size)

# Delete run
client.delete_run("run-uuid")

# Search runs with client
runs = client.search_runs(
    experiment_ids=["0"],
    filter_string="metrics.accuracy > 0.9",
    order_by=["metrics.accuracy DESC"],
)
```

### Model Registry
```python
import mlflow

# Log a model (sklearn example)
mlflow.sklearn.log_model(model, "model", registered_model_name="my-classifier")

# Log a custom model with signature
from mlflow.models import infer_signature
signature = infer_signature(X_train, model.predict(X_train))
mlflow.sklearn.log_model(
    model, "model",
    signature=signature,
    registered_model_name="my-classifier",
)

# Transition model stage
client = MlflowClient()
client.transition_model_version_stage(
    name="my-classifier",
    version=1,
    stage="Staging",
)

# Load a registered model
model = mlflow.sklearn.load_model("models:/my-classifier/Staging")
model = mlflow.sklearn.load_model("models:/my-classifier/1")  # by version

# List registered models
registered_models = client.search_registered_models()
for rm in registered_models:
    print(rm.name, rm.latest_versions)

# Compare versions
versions = client.get_latest_versions("my-classifier", stages=["Production", "Staging"])
for v in versions:
    print(f"Version {v.version}: {v.status} ({v.current_stage})")
```

### PyFunc / Custom Flavors
```python
# Log any model as pyfunc
import mlflow.pyfunc

class MyModel(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input):
        return model_input * 2

mlflow.pyfunc.log_model(
    "model",
    python_model=MyModel(),
    registered_model_name="my-custom-model",
)

# Serve a model locally
# mlflow models serve -m "models:/my-classifier/1" -p 5001
```

### Autologging (quick start)
```python
import mlflow

# Enable autolog for supported frameworks
mlflow.sklearn.autolog()       # scikit-learn
mlflow.pytorch.autolog()       # PyTorch
mlflow.tensorflow.autolog()    # TensorFlow
mlflow.xgboost.autolog()       # XGBoost
mlflow.lightgbm.autolog()      # LightGBM

# Then just train — params, metrics, model are auto-logged
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)  # autolog captures everything
```

### Runs as context manager vs manual
```python
# Context manager (auto-ends run)
with mlflow.start_run(run_name="auto"):
    mlflow.log_metric("score", 0.95)
# Run ended automatically

# Manual lifecycle
run = mlflow.start_run(run_name="manual")
mlflow.log_metric("score", 0.95)
mlflow.end_run()

# Nested runs (parent/child)
with mlflow.start_run(run_name="parent") as parent_run:
    mlflow.log_param("sweep_name", "lr-sweep")
    for lr in [0.001, 0.01, 0.1]:
        with mlflow.start_run(run_name=f"lr={lr}", nested=True) as child:
            mlflow.log_param("learning_rate", lr)
            mlflow.log_metric("accuracy", train_with_lr(lr))
```

## Backtest-Specific Metrics Schema

Each backtest run logs these metrics:

| Metric | Description | Typical range |
|--------|-------------|---------------|
| `total_return` | Cumulative return % | -50 to +1200 |
| `sharpe` | Annualized Sharpe ratio | 0.5 to 3.5 |
| `sortino` | Downside deviation ratio | 1.0 to 5.0 |
| `calmar` | Return / max drawdown | 0.5 to 3.0 |
| `max_dd` | Maximum drawdown % | 5 to 30 |
| `win_rate` | Fraction of winning trades | 0.4 to 0.85 |
| `n_trades` | Total number of trades | 20 to 500 |
| `avg_hold_bars` | Average holding period (bars) | 5 to 15 |
| `profit_factor` | Gross profit / gross loss | 1.0 to 3.5 |
| `cvar95` | 95% Conditional VaR | -1 to -10 |

## Experiment Naming Convention

| Pattern | Example | Purpose |
|---------|---------|---------|
| `v{N}-baseline` | `v3-baseline` | Single-instrument baseline |
| `v{N}-holdout` | `v3-holdout` | Holdout validation runs |
| `v{N}-regime` | `v3-regime` | Regime detection experiments |
| `v{N}-features` | `v3-features` | Feature engineering experiments |
| `v{N}-universe` | `v3-universe` | Universe expansion experiments |
| `p{N}-validation` | `p0-validation` | Roadmap phase validation |
| `v{N}-sweep` | `v3-sweep` | Parameter sweeps |
| `v{N}-stress` | `v3-stress` | Stress tests (COVID, 2022 bear) |

General naming pattern: `<domain>-<experiment-type>`. Examples:
- `creatures-simulation` — creature team simulations
- `inference-benchmark` — LLM benchmarking runs
- `eval-mmlu` — evaluation harness runs

## UI Tips

- **Compare runs**: Select 2+ runs with checkboxes → click "Compare" for side-by-side charts
- **Chart metric**: Click a metric column header to see distribution chart
- **Filter**: Use search bar with `metrics.sharpe > 2.0` syntax
- **Artifacts**: Click a run → "Artifacts" tab to see logged files (configs, trades CSV, charts)
- **Time series**: Metric charts show logged time series when you click on a metric with steps
- **Run lineage**: Parent/child runs shown with indentation; use nested runs for sweeps
- **Model registry**: Navigate to "Models" tab to manage registered model versions

## Integration with Rust Pipeline

The bridge syncs existing DuckDB data. For direct MLflow logging from Rust (future):

1. Rust `save_run()` writes to DuckDB + JSON artifacts as now
2. Bridge syncs to MLflow for visualization
3. No changes needed to Rust code — bridge is a separate concern

## REST API (for programmatic access)

```bash
# List experiments
curl -s ${MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/search | jq .

# Search runs
curl -s -X POST ${MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/search \
  -H "Content-Type: application/json" \
  -d '{"experiment_ids": ["0"], "filter": "metrics.accuracy > 0.9"}' | jq .

# Get run details
curl -s ${MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/get?run_id=UUID | jq .

# Get metrics history
curl -s "${MLFLOW_TRACKING_URI}/api/2.0/mlflow/metrics/get-history?run_id=UUID&metric_key=train_loss" | jq .
```

## Programmatic Experiment Comparison

```python
import mlflow
import pandas as pd

def compare_experiments(exp_names: list[str], metric: str = "accuracy") -> pd.DataFrame:
    """Compare best runs across multiple experiments."""
    rows = []
    for name in exp_names:
        df = mlflow.search_runs(
            experiment_names=[name],
            order_by=[f"metrics.{metric} DESC"],
            max_results=1,
        )
        if not df.empty:
            rows.append({
                "experiment": name,
                "best_run": df["run_id"].iloc[0],
                metric: df[f"metrics.{metric}"].iloc[0],
                "params": {k.replace("params.", ""): v for k, v in df.iloc[0].items() if k.startswith("params.")},
            })
    return pd.DataFrame(rows)

# Usage
df = compare_experiments(["v3-holdout", "v3-features", "v3-sweep"], metric="sharpe")
print(df.to_string())
```

## Known Issues
- **CRITICAL: Always sync via REST API (`http://127.0.0.1:5000`), never via `sqlite:///` directly.** Direct SQLite writes bypass the running server's connection cache — experiments won't appear in UI until server restart.
- Python 3.14 incompatible with AIM (protobuf C extension) and ClearML — MLflow is the only option on this Python version
- `--allowed-hosts "*"` is needed for Tailscale access; localhost-only is default
- Bridge is one-way sync (DuckDB → MLflow); no reverse sync
- `uv pip install` installs into `.venv`, not system Python — always use `.venv/bin/python`
- SQLite tracking store has a write concurrency limit — use PostgreSQL backend for multi-user setups
- Artifact store defaults to `./mlruns` — set `MLFLOW_ARTIFACT_ROOT` for custom location
- MLflow MCP requires the server to be running first
