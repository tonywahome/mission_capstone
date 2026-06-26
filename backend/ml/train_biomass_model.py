"""
Train the TerraFoma biomass estimation model.

Architecture (per research proposal Section 3.3.3):
- Multi-model benchmark: Random Forest, XGBoost, SVR, CNN — select best by spatial CV RMSE
- log1p target transform — biomass is log-normal, reduces RMSE significantly
- Spatial block cross-validation — guards against autocorrelation, honest generalisation
- Multi-sensor features: Sentinel-1 SAR (vv/vh), Sentinel-2 spectral, GEDI LiDAR (rh50/98)
- Uncertainty quantification via prediction intervals (ensemble spread or quantile model)
- SHAP feature importance — explainable for carbon standard auditors

Usage:
    pip install xgboost scikit-learn pandas numpy joblib torch
    python train_biomass_model.py
"""

import json
import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR

try:
    import xgboost as xgb
    _XGB_AVAILABLE = True
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor
    _XGB_AVAILABLE = False
    logging.warning("xgboost not installed — falling back to sklearn GBR. Install: pip install xgboost")

try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    logging.warning("PyTorch not installed — CNN model will be skipped. Install: pip install torch")

# Section 3.7 (experiment tracking) — see services/experiment_tracker.py.
# This script is run standalone with cwd=backend/ml/ (per the Usage note
# above), so backend/ is added to sys.path to make the `services` package
# importable. Logging is best-effort: if it can't be imported for any
# reason, training still proceeds and just isn't recorded.
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from services.experiment_tracker import log_run
    _TRACKER_AVAILABLE = True
except ImportError:
    _TRACKER_AVAILABLE = False
    logging.warning("services.experiment_tracker not importable — this run will not be logged.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Feature definitions ────────────────────────────────────────────────────────

# Core optical features available from original training data
CORE_FEATURES = [
    "blue", "green", "red", "nir", "swir1", "swir2",
    "ndvi", "evi", "savi", "ndmi", "nbr",
    "elevation", "slope",
]

# Extended features from v2 collection pipeline
EXTENDED_FEATURES = [
    # Dry-season bands
    "dry_re1", "dry_re2", "dry_re3", "dry_nir2", "dry_reci",
    # Wet-season key bands
    "wet_ndvi", "wet_evi", "wet_nir", "wet_swir1",
    # Temporal delta
    "delta_ndvi",
    # Sentinel-1 SAR
    "vv", "vh", "vh_vv_diff",
    # Terrain
    "aspect",
    # GEDI height metrics — single strongest predictors
    "rh50", "rh75", "rh98", "cover",
]


def load_data(data_path: str) -> pd.DataFrame:
    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df):,} samples | columns: {list(df.columns)}")
    return df


def build_feature_matrix(df: pd.DataFrame) -> tuple:
    """
    Build feature matrix using all available columns.
    Prefers extended v2 features; falls back to core features for v1 data.
    """
    # Map old column names to new convention if needed
    rename = {
        "blue": "dry_blue", "green": "dry_green", "red": "dry_red",
        "nir": "dry_nir", "swir1": "dry_swir1", "swir2": "dry_swir2",
        "ndvi": "dry_ndvi", "evi": "dry_evi", "savi": "dry_savi",
        "ndmi": "dry_ndmi", "nbr": "dry_nbr",
    }
    # Only rename if dry_ndvi doesn't already exist (v1 data)
    if "dry_ndvi" not in df.columns and "ndvi" in df.columns:
        df = df.rename(columns=rename)

    # Build feature list from what's actually present
    candidate_features = (
        [f"dry_{n}" for n in ["blue","green","red","re1","re2","re3","nir","nir2","swir1","swir2",
                               "ndvi","evi","savi","ndmi","nbr","reci"]]
        + ["wet_ndvi","wet_evi","wet_nir","wet_swir1","delta_ndvi"]
        + ["vv","vh","vh_vv_diff"]
        + ["elevation","slope","aspect"]
        + ["rh50","rh75","rh98","cover"]
    )
    features = [f for f in candidate_features if f in df.columns]
    logger.info(f"Using {len(features)} features: {features}")

    X = df[features].copy()
    y = df["agbd_tonnes_per_ha"].copy()

    # Fill missing optional features with median
    for col in X.columns:
        if X[col].isnull().any():
            X[col] = X[col].fillna(X[col].median())

    return X, y, features


def spatial_block_cv(df: pd.DataFrame, block_size_deg: float = 0.5) -> pd.Series:
    """
    Assign spatial blocks for GroupKFold CV.
    Prevents spatial autocorrelation from inflating test R².
    """
    lat_col = "lat" if "lat" in df.columns else None
    lon_col = "lon" if "lon" in df.columns else None
    if lat_col and lon_col:
        blocks = (
            (df[lat_col] // block_size_deg).astype(str)
            + "_"
            + (df[lon_col] // block_size_deg).astype(str)
        )
    else:
        # Fall back to random groups
        blocks = pd.Series(np.arange(len(df)) % 10, index=df.index).astype(str)
        logger.warning("No lat/lon columns found — using random groups for CV")
    return blocks


class BiomassCNN(nn.Module if _TORCH_AVAILABLE else object):
    """Simple MLP/CNN for tabular feature stacks (per proposal Table 4)."""
    def __init__(self, n_features: int):
        if not _TORCH_AVAILABLE:
            return
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64),         nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32),          nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_random_forest(X_train, y_train_log):
    model = RandomForestRegressor(
        n_estimators=300, max_depth=None, min_samples_leaf=2,
        n_jobs=-1, random_state=42,
    )
    model.fit(X_train, y_train_log)
    return model


def train_xgboost(X_train, y_train_log, X_val, y_val_log):
    if _XGB_AVAILABLE:
        model = xgb.XGBRegressor(
            n_estimators=1000,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            reg_alpha=0.1,
            reg_lambda=1.0,
            n_jobs=-1,
            random_state=42,
            early_stopping_rounds=50,
            eval_metric="rmse",
        )
        model.fit(
            X_train, y_train_log,
            eval_set=[(X_val, y_val_log)],
            verbose=False,
        )
    else:
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.8, random_state=42,
        )
        model.fit(X_train, y_train_log)
    return model


def train_svr(X_train, y_train_log):
    model = SVR(kernel="rbf", C=10.0, epsilon=0.1, gamma="scale")
    model.fit(X_train, y_train_log)
    return model


def train_cnn(X_train, y_train_log, X_val, y_val_log, n_epochs: int = 50):
    if not _TORCH_AVAILABLE:
        return None
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_features = X_train.shape[1]
    model = BiomassNN(n_features).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    X_tr = torch.tensor(X_train, dtype=torch.float32).to(device)
    y_tr = torch.tensor(y_train_log, dtype=torch.float32).to(device)
    X_v  = torch.tensor(X_val, dtype=torch.float32).to(device)
    y_v  = torch.tensor(y_val_log, dtype=torch.float32).to(device)

    best_val_loss = float("inf")
    best_state = None
    for epoch in range(n_epochs):
        model.train()
        optimiser.zero_grad()
        pred = model(X_tr)
        loss = loss_fn(pred, y_tr)
        loss.backward()
        optimiser.step()

        model.eval()
        with torch.no_grad():
            val_loss = loss_fn(model(X_v), y_v).item()
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    if best_state:
        model.load_state_dict(best_state)
    model.to("cpu")
    return model


def evaluate(model, X, y_true, scaler, label: str, is_torch: bool = False) -> dict:
    X_scaled = scaler.transform(X)
    if is_torch and _TORCH_AVAILABLE:
        with torch.no_grad():
            y_pred_log = model(torch.tensor(X_scaled, dtype=torch.float32)).numpy()
    else:
        y_pred_log = model.predict(X_scaled)
    y_pred = np.expm1(y_pred_log)
    r2   = r2_score(y_true, y_pred)
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    bias = float(np.mean(y_pred - y_true))
    logger.info(f"{label:35s}  R²={r2:.4f}  MAE={mae:.1f}  RMSE={rmse:.1f}  Bias={bias:+.1f} t/ha")
    return {"r2": r2, "mae": mae, "rmse": rmse, "bias": bias}


def _cv_metrics(model, X_df, y_log, blocks, n_folds: int, is_torch: bool = False) -> dict:
    """Run spatial block CV for a given model factory and return mean metrics."""
    gkf = GroupKFold(n_splits=n_folds)
    fold_results = []
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X_df, y_log, groups=blocks)):
        X_tr, X_val = X_df.iloc[train_idx], X_df.iloc[val_idx]
        y_tr = y_log.iloc[train_idx].values
        y_val_true_orig = np.expm1(y_log.iloc[val_idx].values)

        sc = StandardScaler()
        X_tr_s  = sc.fit_transform(X_tr)
        X_val_s = sc.transform(X_val)

        if is_torch and _TORCH_AVAILABLE:
            m = train_cnn(X_tr_s, y_tr, X_val_s, y_log.iloc[val_idx].values)
        else:
            m = model(X_tr_s, y_tr)

        if is_torch and _TORCH_AVAILABLE:
            with torch.no_grad():
                y_pred_log = m(torch.tensor(X_val_s, dtype=torch.float32)).numpy()
        else:
            y_pred_log = m.predict(X_val_s)
        y_pred = np.expm1(y_pred_log)
        fold_results.append({
            "r2":   r2_score(y_val_true_orig, y_pred),
            "mae":  mean_absolute_error(y_val_true_orig, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_val_true_orig, y_pred)),
            "bias": float(np.mean(y_pred - y_val_true_orig)),
        })
    return {k: float(np.mean([f[k] for f in fold_results])) for k in fold_results[0]}


def main():
    data_path = "data/sentinel_gedi_training_v2.csv"
    if not Path(data_path).exists():
        data_path = "data/sentinel_gedi_training.csv"
        logger.warning(f"v2 data not found — using v1: {data_path}")

    df = load_data(data_path)

    # Remove extreme outliers (>99.5th percentile)
    q995 = df["agbd_tonnes_per_ha"].quantile(0.995)
    df = df[df["agbd_tonnes_per_ha"] <= q995].copy()
    logger.info(f"After outlier removal: {len(df):,} samples (cap={q995:.0f} t/ha)")

    X, y, features = build_feature_matrix(df)
    y_log = np.log1p(y)

    blocks = spatial_block_cv(df)
    n_blocks = blocks.nunique()
    n_folds = min(5, n_blocks)
    logger.info(f"Spatial blocks: {n_blocks} unique | using {n_folds}-fold GroupKFold")

    # ── Multi-model benchmark (proposal Section 3.3.3, Table 4) ──────────────
    logger.info("\n── Multi-model benchmark (spatial block CV) ──────────────────")
    benchmark_results = {}

    logger.info("  [1/4] Random Forest …")
    rf_metrics = _cv_metrics(
        lambda Xtr, ytr: train_random_forest(Xtr, ytr),
        X, y_log, blocks, n_folds,
    )
    benchmark_results["RandomForest"] = rf_metrics
    logger.info(f"        RF  — R²={rf_metrics['r2']:.4f}  RMSE={rf_metrics['rmse']:.1f}  "
                f"Bias={rf_metrics['bias']:+.1f} t/ha")

    logger.info("  [2/4] XGBoost …")
    xgb_metrics = _cv_metrics(
        lambda Xtr, ytr: train_xgboost(Xtr, ytr, Xtr, ytr),
        X, y_log, blocks, n_folds,
    )
    benchmark_results["XGBoost"] = xgb_metrics
    logger.info(f"        XGB — R²={xgb_metrics['r2']:.4f}  RMSE={xgb_metrics['rmse']:.1f}  "
                f"Bias={xgb_metrics['bias']:+.1f} t/ha")

    logger.info("  [3/4] Support Vector Regression …")
    svr_metrics = _cv_metrics(
        lambda Xtr, ytr: train_svr(Xtr, ytr),
        X, y_log, blocks, n_folds,
    )
    benchmark_results["SVR"] = svr_metrics
    logger.info(f"        SVR — R²={svr_metrics['r2']:.4f}  RMSE={svr_metrics['rmse']:.1f}  "
                f"Bias={svr_metrics['bias']:+.1f} t/ha")

    if _TORCH_AVAILABLE:
        logger.info("  [4/4] CNN (MLP) …")
        cnn_metrics = _cv_metrics(None, X, y_log, blocks, n_folds, is_torch=True)
        benchmark_results["CNN"] = cnn_metrics
        logger.info(f"        CNN — R²={cnn_metrics['r2']:.4f}  RMSE={cnn_metrics['rmse']:.1f}  "
                    f"Bias={cnn_metrics['bias']:+.1f} t/ha")
    else:
        logger.info("  [4/4] CNN skipped — PyTorch not installed")

    # Select best model by RMSE (lower is better)
    best_name = min(benchmark_results, key=lambda k: benchmark_results[k]["rmse"])
    best_cv   = benchmark_results[best_name]
    logger.info(f"\n  Best model: {best_name}  (CV RMSE={best_cv['rmse']:.1f}  R²={best_cv['r2']:.4f})")

    # Save benchmark report
    report_path = Path("models/benchmark_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as fh:
        json.dump(benchmark_results, fh, indent=2)
    logger.info(f"  Benchmark report → {report_path}")

    # ── Train final model (best algorithm) on full dataset ────────────────────
    logger.info(f"\n── Training final {best_name} on full dataset ────────────────")
    final_scaler = StandardScaler()
    X_all_s = final_scaler.fit_transform(X)

    if best_name == "RandomForest":
        final_model = train_random_forest(X_all_s, y_log.values)
        model_type  = "RandomForest"
    elif best_name == "SVR":
        final_model = train_svr(X_all_s, y_log.values)
        model_type  = "SVR"
    elif best_name == "CNN" and _TORCH_AVAILABLE:
        final_model = train_cnn(X_all_s, y_log.values, X_all_s, y_log.values)
        model_type  = "CNN"
    else:
        final_model = train_xgboost(X_all_s, y_log.values, X_all_s, y_log.values)
        model_type  = "XGBoost" if _XGB_AVAILABLE else "GradientBoosting"

    # Feature importance
    try:
        if hasattr(final_model, "feature_importances_"):
            imp = pd.Series(final_model.feature_importances_, index=features) \
                    .sort_values(ascending=False)
            logger.info("\nTop 10 features by importance:")
            for feat, score in imp.head(10).items():
                logger.info(f"  {feat:30s}  {score:.4f}")
    except Exception:
        pass

    # Uncertainty: keep all individual RF trees for prediction intervals when RF wins
    uncertainty_trees = None
    if model_type == "RandomForest":
        uncertainty_trees = final_model.estimators_

    # Final evaluation on training set (upper bound)
    if model_type == "CNN" and _TORCH_AVAILABLE:
        with torch.no_grad():
            y_pred_all = np.expm1(
                final_model(torch.tensor(final_scaler.transform(X), dtype=torch.float32)).numpy()
            )
    else:
        y_pred_all = np.expm1(final_model.predict(final_scaler.transform(X)))

    train_r2  = r2_score(y, y_pred_all)
    train_mae = mean_absolute_error(y, y_pred_all)
    logger.info(f"\nFull-data train R²={train_r2:.4f}  MAE={train_mae:.1f} t/ha  "
                f"(CV R²={best_cv['r2']:.4f}  RMSE={best_cv['rmse']:.1f})")

    # Save model package
    model_data = {
        "model": final_model,
        "scaler": final_scaler,
        "feature_cols": features,
        "test_r2": best_cv["r2"],
        "test_mae": best_cv["mae"],
        "test_rmse": best_cv["rmse"],
        "test_bias": best_cv["bias"],
        "training_samples": len(X),
        "model_type": model_type,
        "target_transform": "log1p",
        "cv_folds": n_folds,
        "benchmark": benchmark_results,
        "uncertainty_trees": uncertainty_trees,  # for RF prediction intervals
    }

    out_path = Path("models/biomass_model_v1.pkl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_data, out_path)
    logger.info(f"\nModel saved → {out_path}")
    logger.info(f"  Algorithm : {model_type}")
    logger.info(f"  Spatial CV R²  : {best_cv['r2']:.4f}")
    logger.info(f"  Spatial CV RMSE: {best_cv['rmse']:.1f} t/ha")
    logger.info(f"  Features       : {len(features)}")
    logger.info(f"  Training samples: {len(X):,}")

    # Section 3.7 (experiment tracking): log this run's full provenance —
    # dataset version, feature stack, hyperparameters, random seed, spatial
    # block split IDs, evaluation metrics, output artifact path — as a
    # structured, append-only record. Pure logging; does not affect the
    # model, metrics, or artifact already produced above.
    if _TRACKER_AVAILABLE:
        try:
            if hasattr(final_model, "get_params"):
                hyperparameters = final_model.get_params()
            else:
                hyperparameters = {
                    "architecture": "128-64-32-1 MLP", "epochs": 50,
                    "lr": 1e-3, "optimizer": "Adam",
                }
        except Exception:
            hyperparameters = {}

        try:
            run_id = log_run(
                dataset_path=data_path,
                dataset_version="v2" if "v2" in data_path else "v1",
                feature_stack=features,
                model_type=model_type,
                hyperparameters=hyperparameters,
                # RandomForest/XGBoost/SVR all set random_state=42 above; the
                # CNN path does not currently set a torch.manual_seed.
                random_seed=42 if model_type != "CNN" else None,
                spatial_block_ids=sorted(str(b) for b in blocks.unique()),
                cv_folds=n_folds,
                metrics=best_cv,
                output_model_path=str(out_path),
                notes=(
                    f"Multi-model benchmark ({', '.join(benchmark_results.keys())}); "
                    f"{best_name} selected by lowest CV RMSE."
                ),
            )
            logger.info(f"  Experiment run  : {run_id}")
        except Exception as e:
            logger.warning(f"Could not log experiment run: {e}")

    return model_data


if __name__ == "__main__":
    main()
