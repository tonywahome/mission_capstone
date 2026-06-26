# TerraFoma ML — Data Collection & Training

This directory contains the scripts that collect satellite/LiDAR training data and train the biomass estimation model described in the capstone proposal (Section 3.3). It is a standalone pipeline — these scripts have their own dependency footprint (`requirements_data_collection.txt`, plus `xgboost`/`torch` as optional extras) separate from the FastAPI backend's `requirements.txt`, which only needs `joblib` to load the already-trained artifact at inference time.

**This file replaces an earlier version that described Aberdare Forest, Kenya as the default study region and a `train_real_model.py` script that does not exist in this repository.** The capstone's actual validation geography is **Bugesera** (savanna/grassland) and **Rulindo** (agroforestry), Rwanda — see the top-level `README.md`'s "Validation Geography and Model Status" section. The scripts below are a mix of an earlier Kenya-era pipeline (still functional, but pointed at the wrong region by default) and a newer Rwanda-targeted export script; this document is honest about which is which rather than presenting either as fully matching the current scope.

---

## Prerequisites

1. **Google Earth Engine account** — [sign up](https://signup.earthengine.google.com/), then `earthengine authenticate`
2. **NASA Earthdata account** — [sign up](https://urs.earthdata.nasa.gov/users/new) (only needed for `collect_gedi_data.py`'s direct NASA download path; `gee_export_rwanda.py` sources GEDI through Earth Engine instead and doesn't need this)
3. Python 3.8+

```bash
pip install -r requirements_data_collection.txt
earthengine authenticate
```

---

## Current Pipeline (Rwanda)

```
gee_export_rwanda.py  →  Google Drive CSV  →  backend/ml/data/sentinel_gedi_training_v2.csv  →  train_biomass_model.py (or .ipynb)  →  models/biomass_model_v1.pkl
```

1. **`python gee_export_rwanda.py`** — pulls GEDI L4A biomass points (quality-filtered) plus Sentinel-2 dry/wet-season composites, Sentinel-1 SAR, and SRTM terrain for the area of interest, samples all layers at the GEDI points, and submits a Drive export task (`TerraFoma/sentinel_gedi_training_v2.csv`).

   **Known gap, not yet fixed:** the script's `rwanda` AOI is currently the *whole country* (`FAO/GAUL/2015/level0` filtered to `ADM0_NAME = 'Rwanda'`), not Bugesera/Rulindo specifically. Narrowing this to the two pilot districts — e.g. by switching to `FAO/GAUL/2015/level2` and filtering on `ADM2_NAME` — is outstanding fieldwork-pipeline work, not yet done. Running the script today collects a Rwanda-wide sample, which is broader than (but not equivalent to) the capstone's two-district validation sample.

2. Download the exported CSV from Drive and copy it to `backend/ml/data/sentinel_gedi_training_v2.csv`.

3. **`python train_biomass_model.py`** (run with `cwd=backend/ml/`) — loads `data/sentinel_gedi_training_v2.csv` if present, falling back to `data/sentinel_gedi_training.csv` (the older v1 format) otherwise. Implements proposal Section 3.3.3: a multi-model benchmark (Random Forest, XGBoost, SVR, and a CNN/MLP if PyTorch is installed) selected by 5-fold spatial-block cross-validation RMSE, with a log1p target transform. Saves the winning model to `models/biomass_model_v1.pkl` and a full benchmark report to `models/benchmark_report.json`, and — if `backend/services/experiment_tracker.py` is importable — logs the run's full provenance under `backend/ml/experiment_runs/` per Section 3.7. A notebook version of the same pipeline exists at `train_biomass_model.ipynb`.

The model currently shipped at `models/biomass_model_v1.pkl` was trained this way on a Bugesera + Kigali City sample (pre-revision geography, 1,990 points) — see the top-level README for the full benchmark table and the explanation of why it's retained as v1/legacy rather than discarded.

---

## Earlier Scripts (Kenya-era, superseded for current scope)

These still run, but were written before the Rwanda pivot and default to Kenya regions:

- **`collect_gedi_data.py`** — direct NASA Earthdata download of GEDI L4A points. Its built-in `regions` dict defaults to Kenya bounding boxes (Aberdare/Mt Kenya highlands, Mau Forest); pass a different `bbox` or add a Rwanda entry before using it for this capstone. Outputs `gedi_data/gedi_<region>_biomass.csv`.
- **`collect_sentinel_data.py`** — matches a GEDI CSV against Sentinel-2 imagery to produce the v1 feature/label CSV (`blue, green, red, nir, swir1, swir2, ndvi, evi, savi, ndmi, nbr, elevation, slope, agbd_tonnes_per_ha`). Its example `__main__` block points at a Congo Basin GEDI file by default — also not Rwanda-specific; intended to be called with explicit `gedi_csv`/`output_csv` arguments.
- **`improve_model.py`** — an earlier exploratory tuning script (stacking/Ridge ensembles, baseline R²=0.53 → target R²=0.65) that predates `train_biomass_model.py`'s multi-model benchmark (which already reaches CV R²=0.888 on XGBoost). Superseded; kept for reference, not part of the current training path.

If reusing these for Rulindo data collection, the region/bounding-box values need to be replaced with Rulindo's coordinates before they produce relevant output — that substitution has not been made in this repository, per the binding decision not to fabricate new training data.

---

## Data Format

### v1 (`collect_sentinel_data.py` output)
```csv
lat,lon,blue,green,red,nir,swir1,swir2,ndvi,evi,savi,ndmi,nbr,elevation,slope,agbd_tonnes_per_ha
-0.3456,36.7123,520,680,450,3200,2100,1500,0.75,0.62,0.68,0.21,0.35,2100,12.5,145.3
```
13 features (10 spectral bands/derived already counted above + elevation/slope), single Sentinel-2 composite, no SAR or GEDI height metrics.

### v2 (`gee_export_rwanda.py` output — what `biomass_model_v1.pkl` actually expects)
Adds dry/wet-season band pairs (`dry_*`/`wet_*`), `delta_ndvi`, Sentinel-1 SAR (`vv`, `vh`, `vh_vv_diff`), terrain `aspect`, and GEDI height/cover metrics (`rh50`, `rh75`, `rh98`, `cover`) when available from the GEDI L4A product used. `train_biomass_model.py`'s `build_feature_matrix()` auto-detects which columns are present and renames v1 column names to the `dry_*` convention if no v2 columns exist, so both formats are accepted, but only the v2-style export reflects the proposal's full multi-sensor fusion (Sentinel-1 + Sentinel-2 + GEDI).

---

## Customization

### Study region

For the current pipeline, edit the AOI filter near the top of `gee_export_rwanda.py` — see the "Known gap" note above for what district-level scoping would require. For the older scripts, edit the `bbox`/region dict in `collect_gedi_data.py` or the `gedi_csv` argument passed to `collect_sentinel_data.py`.

### Model hyperparameters

Edit the relevant `train_*` function in `train_biomass_model.py`, e.g.:
```python
def train_random_forest(X_train, y_train_log):
    model = RandomForestRegressor(
        n_estimators=300, max_depth=None, min_samples_leaf=2,
        n_jobs=-1, random_state=42,
    )
```
`train_xgboost`, `train_svr`, and `train_cnn` follow the same pattern; the model actually selected and saved is whichever wins lowest CV RMSE in the benchmark, not necessarily the one you edit.

---

## Troubleshooting

**"Earth Engine not initialized"** — run `earthengine authenticate` again.

**"No GEDI data found"** — check the bounding box is within ±51.6° latitude (GEDI's coverage limit); try a larger area or wider date range.

**Too few Sentinel-2 images** — widen the date filter or relax `CLOUDY_PIXEL_PERCENTAGE` in the relevant script.

**GEE memory/timeout errors** — reduce sample point count, or split the export into smaller date ranges.

---

## Data Sources

| Dataset | Source | Resolution | Used by |
|---|---|---|---|
| GEDI L4A | NASA (via GEE or direct Earthdata) | 25 m footprints | Biomass ground truth, all scripts |
| Sentinel-2 SR | ESA/Copernicus | 10 m | Spectral bands/indices, all scripts |
| Sentinel-1 GRD | ESA/Copernicus | ~10 m | SAR (`vv`/`vh`), `gee_export_rwanda.py` only |
| SRTM | NASA | 30 m | Elevation/slope/aspect, all scripts |

---

## Measured Performance

See the top-level `README.md`'s "Machine Learning Pipeline" section for the actual multi-model benchmark table (XGBoost selected, CV R²=0.8879±0.0067, CV RMSE=20.0±0.5 t/ha, on the Bugesera + Kigali City sample). This file previously speculated about expected R²/MAE/RMSE at various sample sizes without measured results behind those numbers; those speculative figures have been removed rather than carried forward.

---

## Integration with Backend

`backend/services/biomass_estimator.py` is the actual integration point — it loads the pickled dict once at import time and exposes `predict_biomass_from_features(feature_dict)`:

```python
model_data = joblib.load("ml/models/biomass_model_v1.pkl")
feature_cols = model_data["feature_cols"]          # exact column order used at training time
X = scaler_transform_row(feature_dict, feature_cols, model_data["scaler"])
raw_pred = model_data["model"].predict(X)[0]
biomass_mean = np.expm1(raw_pred) if model_data.get("target_transform") == "log1p" else raw_pred
# 90% prediction interval from RF tree spread when uncertainty_trees is present —
# see predict_biomass_from_features() for the full implementation.
```

---

## Next Steps

These reflect the capstone's actual remaining work, not aspirational claims:

1. Scope `gee_export_rwanda.py`'s AOI down to Bugesera + Rulindo district boundaries (currently country-wide).
2. Collect a real Rulindo field/training sample and retrain — the model currently shipped has never seen Rulindo data.
3. Per-stratum evaluation (savanna/grassland vs. agroforestry) once Rulindo data exists, per proposal Section 3.5.
4. Replace `feature_importances_`-based ranking with true SHAP values if auditor-facing explainability output is required — `train_biomass_model.py`'s docstring references SHAP as an architectural intent, but the script currently only computes built-in tree feature importances.

---

## References

- [GEDI L4A Documentation](https://lpdaac.usgs.gov/products/gedi04_av002/)
- [Sentinel-2 User Guide](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi)
- [Sentinel-1 User Guide](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-1-sar)
- [Google Earth Engine Guides](https://developers.google.com/earth-engine/guides)
