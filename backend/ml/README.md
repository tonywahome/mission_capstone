# TerraFoma ML Data Collection & Training

This directory contains scripts for collecting real satellite and biomass data, then training your biomass estimation model.

## Quick Start

### Prerequisites
1. **Google Earth Engine Account**: [Sign up here](https://signup.earthengine.google.com/)
2. **NASA Earthdata Account**: [Sign up here](https://urs.earthdata.nasa.gov/users/new)
3. Python 3.8+

### Installation

```bash
# Install data collection dependencies
pip install -r ml/requirements_data_collection.txt

# Authenticate with Google Earth Engine
earthengine authenticate

# Follow browser prompts to authorize
```

### Data Collection Workflow

#### Step 1: Collect GEDI Biomass Data (Ground Truth)

```bash
python ml/collect_gedi_data.py
```

This script:
- Connects to NASA's GEDI L4A dataset (LiDAR-based biomass)
- Downloads data for your study region (default: Aberdare Forest, Kenya)
- Filters for high-quality shots (quality_flag=1, sensitivity>0.9)
- Outputs: `ml/gedi_data/gedi_biomass_samples.csv`

**Expected output**: ~1,000-10,000 biomass points per region

#### Step 2: Extract Sentinel-2 Features (Satellite Imagery)

```bash
python ml/collect_sentinel_data.py
```

This script:
- For each GEDI point, queries Sentinel-2 imagery
- Calculates vegetation indices (NDVI, EVI, SAVI, etc.)
- Extracts terrain data (elevation, slope)
- Matches satellite features with GEDI biomass labels
- Outputs: `ml/sample_data/sentinel_gedi_training.csv`

**Expected output**: ~80% match rate (some GEDI points have cloudy Sentinel-2)

**Processing time**: ~1-2 minutes per 100 samples (GEE API limits)

#### Step 3: Train Biomass Model

```bash
python ml/train_real_model.py
```

This script:
- Loads matched training data
- Trains Random Forest model
- Performs cross-validation
- Evaluates on test set
- Saves trained model: `ml/biomass_model_v1.pkl`

**Expected performance**:
- R² > 0.70 (with 10,000+ samples)
- MAE < 30 tonnes/ha
- RMSE < 40 tonnes/ha

## Data Format

### GEDI Output (`gedi_biomass_samples.csv`)
```csv
lat,lon,agbd_tonnes_per_ha,quality_flag,sensitivity,beam
-0.3456,36.7123,145.3,1,0.95,BEAM0101
```

### Training Data (`sentinel_gedi_training.csv`)
```csv
lat,lon,blue,green,red,nir,swir1,swir2,ndvi,evi,savi,ndmi,nbr,elevation,slope,agbd_tonnes_per_ha
-0.3456,36.7123,520,680,450,3200,2100,1500,0.75,0.62,0.68,0.21,0.35,2100,12.5,145.3
```

## Customization

### Change Study Region

Edit the bounding box in `collect_gedi_data.py`:

```python
# Example regions
bbox_aberdare = (36.5, -0.6, 36.9, -0.2)  # Kenya
bbox_congo = (20.0, -2.0, 25.0, 2.0)      # DRC
bbox_ethiopia = (37.0, 7.0, 40.0, 10.0)   # Ethiopia
```

### Adjust Time Window

Edit the date range in `collect_sentinel_data.py`:

```python
start_date = "2020-01-01"  # Dry season
end_date = "2020-06-30"    # Wet season
```

### Model Hyperparameters

Edit in `train_real_model.py`:

```python
trainer.train_random_forest(
    n_estimators=300,    # More trees = better but slower
    max_depth=25,        # Deeper = more complex patterns
    min_samples_split=5  # Regularization
)
```

## Troubleshooting

### "Earth Engine not initialized"
```bash
earthengine authenticate
```

### "No GEDI data found"
- Check your bounding box (ensure it's in tropics: ±51.6° latitude)
- Try a larger area or different time range
- Verify NASA Earthdata credentials

### "Too few Sentinel-2 images"
- Increase time window (e.g., 1 year instead of 6 months)
- Relax cloud cover threshold: `.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))`

### GEE Memory Errors
- Reduce `buffer_m` parameter (default: 50m)
- Process samples in batches
- Use `.median()` instead of `.mean()` for composites

## Data Sources

| Dataset | Source | Resolution | Coverage | Purpose |
|---------|--------|-----------|----------|---------|
| **GEDI L4A** | NASA | 25m footprints | ±51.6° lat | Biomass ground truth |
| **Sentinel-2** | ESA/Copernicus | 10m | Global | Optical imagery |
| **SRTM DEM** | NASA | 30m | Global | Terrain (elevation, slope) |

## Performance Benchmarks

With **10,000 training samples**:
- Training time: ~5 minutes (Random Forest)
- Inference: <1ms per plot
- Model size: ~100MB

With **100,000 training samples** (recommended for production):
- Training time: ~30 minutes
- Better generalization across ecosystems
- R² typically > 0.75

## Integration with Backend

After training, use the model in your FastAPI backend:

```python
import joblib
import ee

# Load model
model_data = joblib.load("ml/biomass_model_v1.pkl")
model = model_data['model']
scaler = model_data['scaler']

# In your /scan endpoint
def estimate_biomass(lat: float, lon: float):
    # Get Sentinel-2 features
    features = get_sentinel_features(lat, lon)
    
    # Normalize
    features_scaled = scaler.transform([features])
    
    # Predict
    biomass = model.predict(features_scaled)[0]
    
    return biomass
```

## Next Steps

1. ✅ Collect data for multiple regions (Kenya, Tanzania, Uganda)
2. ✅ Train model with >50,000 samples
3. 🔲 Implement time-series change detection
4. 🔲 Add uncertainty quantification (prediction intervals)
5. 🔲 Deploy model as API endpoint
6. 🔲 Create validation dashboard

## References

- [GEDI L4A Documentation](https://lpdaac.usgs.gov/products/gedi04_av002/)
- [Sentinel-2 User Guide](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi)
- [Google Earth Engine Guides](https://developers.google.com/earth-engine/guides)
