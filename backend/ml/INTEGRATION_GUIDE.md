# Carbon Credit Engine Integration Guide

## Overview

This document explains how your trained Random Forest biomass model integrates into the complete carbon credit issuance pipeline.

## Architecture

```
Satellite Imagery (Sentinel-2)
         ↓
[1] Forest Segmentation → Binary mask (forest/non-forest)
         ↓
[2] Biomass Estimation → Your trained RF model → AGB (tonnes/ha)
         ↓
[3] Carbon Calculation → AGB × 0.47 × 3.667 → tCO₂e
         ↓
[4] Risk Assessment → Climate + Fire + Deforestation → Risk Factor
         ↓
[5] Credit Issuance → tCO₂e × (1 - risk) → Final Credits
```

## Implementation Status

### ✅ Completed
- [x] GEDI biomass data collection (1.5M samples)
- [x] Sentinel-2 feature extraction (in progress: 4000 samples)
- [x] Random Forest model training script
- [x] Complete integration pipeline (`carbon_credit_engine.py`)
- [x] Carbon calculation formulas (IPCC methodology)
- [x] Risk assessment framework

### 🚧 In Progress
- [ ] Collecting 4000 training samples (~3 hours remaining)
- [ ] Training final biomass model
- [ ] Testing complete pipeline end-to-end

### 📋 TODO for Production

#### Phase 1: Improve Biomass Model (Current)
1. **Complete training data collection** (running now)
2. **Train final model**: `python backend/ml/train_real_model.py`
3. **Validate performance**: Ensure R² > 0.70
4. **Deploy model**: Copy `biomass_model_v1.pkl` to production

#### Phase 2: Enhance Forest Segmentation
**Current**: Simple NDVI threshold (NDVI > 0.4 = forest)
**Upgrade options**:
- **Option A**: Use Google's Dynamic World dataset (pre-trained, free)
  ```python
  dynamic_world = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  forest_prob = dynamic_world.select('trees')
  ```
- **Option B**: Train U-Net for semantic segmentation
  - Requires 10,000+ labeled image patches
  - GPU training infrastructure
  - ~2-3 weeks development time

**Recommendation**: Start with Dynamic World (Option A) - it's production-ready

#### Phase 3: Integrate Real Risk Data
**Current**: Mock data and simplified calculations
**Upgrade to**:

1. **ERA5 Climate Data** (drought/temperature trends)
   ```python
   era5 = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
   precip = era5.select('total_precipitation_sum')
   ```

2. **MODIS Fire Alerts** (already implemented)
   - MOD14A1 fire detections
   - Historical fire frequency

3. **Hansen Global Forest Change** (deforestation)
   ```python
   hansen = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
   loss_year = hansen.select('lossyear')
   ```

4. **VIIRS Nighttime Lights** (illegal logging proxy)
   ```python
   viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')
   ```

#### Phase 4: Add Temporal Monitoring
Track changes over time for permanence verification:
- Annual biomass updates
- Fire event detection
- Deforestation alerts
- Carbon stock trends

## Current vs Production Comparison

| Component | Current Status | Production Target |
|-----------|---------------|-------------------|
| **Forest Segmentation** | NDVI threshold | Dynamic World or U-Net |
| **Biomass Model** | Random Forest (training) | Validated RF (R²>0.70) |
| **Training Data** | 4000 samples | 10,000+ samples |
| **Risk Assessment** | Simplified | Full ERA5 + FIRMS data |
| **Temporal Tracking** | Single snapshot | Multi-year monitoring |
| **Validation** | Basic CV | Independent holdout set |

## How to Use the Complete Pipeline

### 1. After Training Finishes

```bash
# Check if collection is complete
./backend/ml/check_collection.sh

# Train the model
python backend/ml/train_real_model.py

# This creates: backend/ml/biomass_model_v1.pkl
```

### 2. Test the Complete Engine

```python
from backend.services.carbon_credit_engine import CarbonCreditEngine

# Initialize with your trained model
engine = CarbonCreditEngine(
    biomass_model_path="backend/ml/biomass_model_v1.pkl"
)

# Analyze a plot
result = engine.process_plot(
    lat=-1.234,      # Your plot location
    lon=36.789,
    buffer_m=5000,   # 5km radius
    project_name="My Forest Project"
)

print(result['final_credits'])
# Output:
# {
#   'gross_credits_tco2e': 12345.67,
#   'net_credits_tco2e': 10493.82,  # After risk adjustment
#   'credits_per_hectare': 13.42
# }
```

### 3. Integrate with Your API

```python
# Add to backend/main.py
from backend.routers import plots_enhanced

app.include_router(plots_enhanced.router)
```

Test the API:
```bash
curl -X POST http://localhost:8000/api/plots/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "lat": -1.234,
    "lon": 36.789,
    "buffer_m": 5000,
    "project_name": "Test Project"
  }'
```

## Model Performance Expectations

### With 4000 Training Samples
- **R² Score**: 0.65-0.75
- **MAE**: 30-40 tonnes/ha
- **RMSE**: 40-50 tonnes/ha
- **Coverage**: Congo Basin region

### To Improve (10,000+ samples)
- **R² Score**: 0.75-0.85
- **MAE**: 20-30 tonnes/ha
- **RMSE**: 30-40 tonnes/ha
- **Coverage**: Multiple regions

## Carbon Calculation Details

### IPCC Methodology
```
Biomass (AGB) → Carbon → CO₂ Equivalent
     ↓             ↓          ↓
  tonnes/ha    × 0.47    × 3.667
                ↓
            tCO₂e/ha
```

**Example**:
- Forest area: 100 ha
- Mean biomass: 150 tonnes/ha
- Total biomass: 15,000 tonnes
- Carbon content: 15,000 × 0.47 = 7,050 tonnes C
- CO₂ equivalent: 7,050 × 3.667 = 25,852 tCO₂e
- After risk adjustment (15%): 21,974 tCO₂e **final credits**

## Risk Adjustment Framework

### Risk Factors
1. **Fire Risk** (weight: 40%)
   - Historical fire events
   - Dry season severity
   - Proximity to fire hotspots

2. **Drought Risk** (weight: 30%)
   - NDVI temporal variation
   - Precipitation trends
   - Temperature anomalies

3. **Deforestation Risk** (weight: 30%)
   - Distance to deforestation frontier
   - Road proximity
   - Population pressure

### Risk Score → Credit Adjustment
- **Low Risk (0-0.3)**: 95-100% of credits issued
- **Medium Risk (0.3-0.6)**: 80-95% of credits issued
- **High Risk (0.6-1.0)**: 70-80% of credits issued

## Next Steps

1. **Wait for data collection to complete** (~3 hours)
2. **Train the model**: Check model performance metrics
3. **Test the engine**: Run sample plots through pipeline
4. **Validate outputs**: Compare with ground truth if available
5. **Deploy to API**: Integrate with your backend
6. **Monitor performance**: Track prediction accuracy over time

## Questions & Debugging

### How do I know if my model is good enough?
- R² > 0.70 → Good for production
- R² 0.60-0.70 → Acceptable, collect more data
- R² < 0.60 → Need more samples or feature engineering

### What if Earth Engine fails?
- Check authentication: `earthengine authenticate`
- Check project: `earthengine set_project YOUR_PROJECT`
- Fallback: Use pre-computed vegetation indices

### How to handle different forest types?
- Train separate models per region/biome
- Add forest type as feature
- Use transfer learning from base model

### Can I use this without the trained model?
- Yes! The engine has fallback NDVI-based estimation
- Less accurate but functional for testing
- Replace with trained model for production

## Resources

- **IPCC Carbon Accounting**: https://www.ipcc-nggip.iges.or.jp/
- **Google Earth Engine**: https://earthengine.google.com/
- **GEDI Biomass Data**: https://daac.ornl.gov/GEDI/
- **Sentinel-2 Docs**: https://sentinel.esa.int/web/sentinel/missions/sentinel-2
