"""
Carbon Credit Engine - Integrates all components for credit issuance.

This module orchestrates:
1. Forest segmentation (identifying forest cover)
2. Biomass estimation (using trained RF model)
3. Carbon stock calculation (AGB → tCO₂e)
4. Risk & permanence scoring
5. Final credit issuance with adjustments
"""

import ee
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CarbonCreditEngine:
    """
    End-to-end pipeline for carbon credit calculation from satellite imagery.
    """
    
    def __init__(self, biomass_model_path: str = None):
        """
        Initialize the engine.
        
        Args:
            biomass_model_path: Path to trained biomass model (pkl file)
        """
        # Initialize Earth Engine
        try:
            from services.gee_init import initialize_gee
            initialize_gee()
        except Exception as _gee_err:
            logger.warning(f"Earth Engine not initialized — some features unavailable: {_gee_err}")
        
        # Load trained biomass model
        self.biomass_model = None
        if biomass_model_path and Path(biomass_model_path).exists():
            self.biomass_model = joblib.load(biomass_model_path)
            logger.info(f"Loaded biomass model from {biomass_model_path}")
        else:
            logger.warning("No biomass model loaded - will use fallback estimation")
    
    # ========================================================================
    # STEP 1: FOREST SEGMENTATION
    # ========================================================================
    
    def segment_forest(
        self, 
        geometry: ee.Geometry,
        start_date: str = "2023-01-01",
        end_date: str = "2023-12-31",
        ndvi_threshold: float = 0.4
    ) -> Dict:
        """
        Identify forest pixels using NDVI threshold.
        
        For production: Replace with semantic segmentation model (U-Net)
        For now: Simple NDVI-based classification
        
        Args:
            geometry: Area of interest
            start_date: Start date for imagery
            end_date: End date for imagery
            ndvi_threshold: NDVI threshold for forest classification
            
        Returns:
            dict with forest_area_ha, forest_fraction, forest_mask
        """
        try:
            # Get Sentinel-2 composite
            s2 = (
                ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            )
            
            # Calculate NDVI
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            composite = s2.map(add_ndvi).median()
            ndvi = composite.select('NDVI')
            
            # Binary forest mask (NDVI > threshold)
            forest_mask = ndvi.gt(ndvi_threshold)
            
            # Calculate forest area
            pixel_area = forest_mask.multiply(ee.Image.pixelArea())
            stats = pixel_area.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=10,
                maxPixels=1e9
            )
            
            forest_area_m2 = stats.get('NDVI').getInfo()
            forest_area_ha = forest_area_m2 / 10000
            
            # Total area
            total_area_m2 = geometry.area().getInfo()
            total_area_ha = total_area_m2 / 10000
            
            return {
                'forest_area_ha': round(forest_area_ha, 2),
                'total_area_ha': round(total_area_ha, 2),
                'forest_fraction': round(forest_area_ha / total_area_ha, 3),
                'forest_mask': forest_mask,
                'composite': composite
            }
            
        except Exception as e:
            logger.error(f"Forest segmentation failed: {e}")
            return None
    
    # ========================================================================
    # STEP 2: BIOMASS ESTIMATION
    # ========================================================================
    
    def estimate_biomass(
        self,
        composite: ee.Image,
        forest_mask: ee.Image,
        geometry: ee.Geometry
    ) -> Dict:
        """
        Estimate Above-Ground Biomass using trained Random Forest model.
        
        Args:
            composite: Sentinel-2 composite image
            forest_mask: Binary forest mask
            geometry: Area of interest
            
        Returns:
            dict with mean_biomass_tonnes_per_ha, total_biomass_tonnes
        """
        try:
            # Calculate vegetation indices
            ndvi = composite.normalizedDifference(['B8', 'B4']).rename('NDVI')
            evi = composite.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
                {
                    'NIR': composite.select('B8'),
                    'RED': composite.select('B4'),
                    'BLUE': composite.select('B2')
                }
            ).rename('EVI')
            
            savi = composite.expression(
                '((NIR - RED) / (NIR + RED + 0.5)) * 1.5',
                {
                    'NIR': composite.select('B8'),
                    'RED': composite.select('B4')
                }
            ).rename('SAVI')
            
            ndmi = composite.normalizedDifference(['B8', 'B11']).rename('NDMI')
            nbr = composite.normalizedDifference(['B8', 'B12']).rename('NBR')
            
            # Get elevation and slope
            dem = ee.Image('USGS/SRTMGL1_003')
            elevation = dem.select('elevation')
            slope = ee.Terrain.slope(dem)
            
            # Combine all features
            features = ee.Image.cat([
                composite.select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12']),
                ndvi, evi, savi, ndmi, nbr,
                elevation, slope
            ]).rename([
                'blue', 'green', 'red', 'nir', 'swir1', 'swir2',
                'ndvi', 'evi', 'savi', 'ndmi', 'nbr',
                'elevation', 'slope'
            ])
            
            # Mask to forest only
            forest_features = features.updateMask(forest_mask)
            
            # Sample forest pixels
            sample = forest_features.sample(
                region=geometry,
                scale=10,
                numPixels=500,  # Sample 500 points
                geometries=False
            )
            
            # Get feature values
            sample_data = sample.getInfo()['features']
            
            if len(sample_data) == 0:
                logger.warning("No forest pixels sampled")
                return None
            
            # Extract feature arrays
            feature_names = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2',
                           'ndvi', 'evi', 'savi', 'ndmi', 'nbr', 'elevation', 'slope']
            
            X = []
            for point in sample_data:
                props = point['properties']
                X.append([props.get(f, 0) for f in feature_names])
            
            X = np.array(X)
            
            # Predict biomass
            if self.biomass_model:
                biomass_predictions = self.biomass_model.predict(X)
            else:
                # Fallback: Simple NDVI-based estimation
                ndvi_values = X[:, feature_names.index('ndvi')]
                biomass_predictions = ndvi_values * 300  # Rough approximation
            
            mean_biomass = float(np.mean(biomass_predictions))
            std_biomass = float(np.std(biomass_predictions))
            
            return {
                'mean_biomass_tonnes_per_ha': round(mean_biomass, 2),
                'std_biomass_tonnes_per_ha': round(std_biomass, 2),
                'min_biomass': round(float(np.min(biomass_predictions)), 2),
                'max_biomass': round(float(np.max(biomass_predictions)), 2),
                'n_samples': len(biomass_predictions)
            }
            
        except Exception as e:
            logger.error(f"Biomass estimation failed: {e}")
            return None
    
    # ========================================================================
    # STEP 3: CARBON CALCULATION
    # ========================================================================
    
    def calculate_carbon_stock(
        self,
        mean_biomass_tonnes_per_ha: float,
        forest_area_ha: float
    ) -> Dict:
        """
        Convert Above-Ground Biomass to Carbon Stock (tCO₂e).
        
        Uses IPCC methodology:
        - Carbon content = 47% of dry biomass
        - CO₂ equivalent = Carbon × (44/12) molecular weight ratio
        
        Args:
            mean_biomass_tonnes_per_ha: Average biomass density
            forest_area_ha: Forest area in hectares
            
        Returns:
            dict with carbon_stock_tco2e
        """
        CARBON_FRACTION = 0.47  # IPCC default for tropical forests
        CO2_RATIO = 44 / 12  # Molecular weight ratio CO₂/C
        
        # Total biomass
        total_biomass_tonnes = mean_biomass_tonnes_per_ha * forest_area_ha
        
        # Carbon content
        carbon_tonnes = total_biomass_tonnes * CARBON_FRACTION
        
        # CO₂ equivalent
        co2_equivalent_tonnes = carbon_tonnes * CO2_RATIO
        
        return {
            'total_biomass_tonnes': round(total_biomass_tonnes, 2),
            'carbon_tonnes': round(carbon_tonnes, 2),
            'carbon_stock_tco2e': round(co2_equivalent_tonnes, 2),
            'biomass_per_ha': round(mean_biomass_tonnes_per_ha, 2),
            'carbon_per_ha': round(mean_biomass_tonnes_per_ha * CARBON_FRACTION * CO2_RATIO, 2)
        }
    
    # ========================================================================
    # STEP 4: RISK & PERMANENCE SCORING
    # ========================================================================
    
    def assess_risk(
        self,
        geometry: ee.Geometry,
        years_lookback: int = 5
    ) -> Dict:
        """
        Assess risk factors affecting carbon permanence.
        
        Analyzes:
        - Drought trends (ERA5 climate data)
        - Wildfire probability (MODIS fire alerts)
        - Deforestation proximity
        - Land cover change
        
        Args:
            geometry: Area of interest
            years_lookback: Years of historical data to analyze
            
        Returns:
            dict with risk scores and overall risk_adjustment_factor
        """
        try:
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_lookback*365)
            
            # 1. FIRE RISK (MODIS fire detections)
            fires = ee.ImageCollection('MODIS/006/MOD14A1') \
                .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                .filterBounds(geometry) \
                .select('FireMask')
            
            fire_count = fires.size().getInfo()
            fire_risk = min(fire_count / 50.0, 1.0)  # Normalize to 0-1
            
            # 2. DROUGHT RISK (simplified - would use ERA5 in production)
            # For now, use NDVI temporal variation as proxy
            ndvi_collection = ee.ImageCollection('MODIS/006/MOD13A2') \
                .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                .filterBounds(geometry) \
                .select('NDVI')
            
            ndvi_std = ndvi_collection.reduce(ee.Reducer.stdDev())
            ndvi_var = ndvi_std.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=1000
            ).get('NDVI_stdDev').getInfo()
            
            drought_risk = min((ndvi_var or 0) / 2000.0, 1.0)  # Normalize
            
            # 3. DEFORESTATION PROXIMITY
            # Check distance to recent deforestation
            # (Simplified - would use Hansen Global Forest Change)
            deforestation_proximity_risk = 0.3  # Placeholder
            
            # 4. OVERALL RISK SCORE
            weights = {
                'fire': 0.4,
                'drought': 0.3,
                'deforestation': 0.3
            }
            
            overall_risk = (
                fire_risk * weights['fire'] +
                drought_risk * weights['drought'] +
                deforestation_proximity_risk * weights['deforestation']
            )
            
            # Risk adjustment factor (reduces credits for high-risk areas)
            risk_adjustment_factor = 1.0 - (overall_risk * 0.3)  # Max 30% reduction
            
            return {
                'fire_risk': round(fire_risk, 3),
                'drought_risk': round(drought_risk, 3),
                'deforestation_proximity_risk': round(deforestation_proximity_risk, 3),
                'overall_risk_score': round(overall_risk, 3),
                'risk_adjustment_factor': round(risk_adjustment_factor, 3),
                'fire_events_detected': fire_count
            }
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            # Return conservative default
            return {
                'fire_risk': 0.5,
                'drought_risk': 0.5,
                'deforestation_proximity_risk': 0.5,
                'overall_risk_score': 0.5,
                'risk_adjustment_factor': 0.85,
                'fire_events_detected': 0
            }
    
    # ========================================================================
    # COMPLETE PIPELINE
    # ========================================================================
    
    def process_plot(
        self,
        lat: float,
        lon: float,
        buffer_m: float = 1000,
        project_name: str = "Unnamed Project"
    ) -> Dict:
        """
        Complete end-to-end processing for a plot.
        
        Args:
            lat: Latitude of plot center
            lon: Longitude of plot center
            buffer_m: Radius around center point (meters)
            project_name: Name of the project
            
        Returns:
            Complete analysis with all components
        """
        logger.info(f"Processing plot: {project_name} at ({lat}, {lon})")
        
        # Create geometry
        point = ee.Geometry.Point([lon, lat])
        geometry = point.buffer(buffer_m)
        
        results = {
            'project_name': project_name,
            'location': {'lat': lat, 'lon': lon},
            'area_analyzed_ha': round((buffer_m ** 2 * 3.14159) / 10000, 2)
        }
        
        # Step 1: Forest Segmentation
        logger.info("Step 1/4: Forest segmentation...")
        forest_data = self.segment_forest(geometry)
        if forest_data:
            results['forest_segmentation'] = {
                'forest_area_ha': forest_data['forest_area_ha'],
                'forest_fraction': forest_data['forest_fraction']
            }
        else:
            return {'error': 'Forest segmentation failed'}
        
        # Step 2: Biomass Estimation
        logger.info("Step 2/4: Biomass estimation...")
        biomass_data = self.estimate_biomass(
            forest_data['composite'],
            forest_data['forest_mask'],
            geometry
        )
        if biomass_data:
            results['biomass_estimation'] = biomass_data
        else:
            return {'error': 'Biomass estimation failed'}
        
        # Step 3: Carbon Calculation
        logger.info("Step 3/4: Carbon stock calculation...")
        carbon_data = self.calculate_carbon_stock(
            biomass_data['mean_biomass_tonnes_per_ha'],
            forest_data['forest_area_ha']
        )
        results['carbon_stock'] = carbon_data
        
        # Step 4: Risk Assessment
        logger.info("Step 4/4: Risk assessment...")
        risk_data = self.assess_risk(geometry)
        results['risk_assessment'] = risk_data
        
        # Final Credit Calculation
        adjusted_credits = carbon_data['carbon_stock_tco2e'] * risk_data['risk_adjustment_factor']
        
        results['final_credits'] = {
            'gross_credits_tco2e': carbon_data['carbon_stock_tco2e'],
            'risk_adjustment_factor': risk_data['risk_adjustment_factor'],
            'net_credits_tco2e': round(adjusted_credits, 2),
            'credits_per_hectare': round(adjusted_credits / forest_data['forest_area_ha'], 2)
        }
        
        # Integrity Score (simplified)
        integrity_score = 70 + (1 - risk_data['overall_risk_score']) * 30
        results['integrity_score'] = round(integrity_score, 1)
        
        logger.info(f"✓ Processing complete: {adjusted_credits:.2f} tCO₂e credits")
        
        return results


# Example usage
if __name__ == "__main__":
    # Initialize engine with trained model
    engine = CarbonCreditEngine(
        biomass_model_path="backend/ml/models/biomass_model_v1.pkl"
    )
    
    # Process a plot (example: Congo Basin location)
    result = engine.process_plot(
        lat=-18.213,
        lon=12.770,
        buffer_m=5000,  # 5km radius
        project_name="Congo Basin Pilot"
    )
    
    print("\n" + "="*60)
    print("CARBON CREDIT ANALYSIS RESULTS")
    print("="*60)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\nProject: {result['project_name']}")
        print(f"Location: {result['location']}")
        print(f"\n1. FOREST SEGMENTATION:")
        print(f"   Forest Area: {result['forest_segmentation']['forest_area_ha']:.2f} ha")
        print(f"   Forest Fraction: {result['forest_segmentation']['forest_fraction']:.1%}")
        
        print(f"\n2. BIOMASS ESTIMATION:")
        print(f"   Mean AGB: {result['biomass_estimation']['mean_biomass_tonnes_per_ha']:.2f} tonnes/ha")
        print(f"   Range: {result['biomass_estimation']['min_biomass']:.2f} - {result['biomass_estimation']['max_biomass']:.2f} tonnes/ha")
        
        print(f"\n3. CARBON STOCK:")
        print(f"   Total CO₂e: {result['carbon_stock']['carbon_stock_tco2e']:.2f} tonnes")
        print(f"   Carbon/ha: {result['carbon_stock']['carbon_per_ha']:.2f} tCO₂e/ha")
        
        print(f"\n4. RISK ASSESSMENT:")
        print(f"   Fire Risk: {result['risk_assessment']['fire_risk']:.2f}")
        print(f"   Drought Risk: {result['risk_assessment']['drought_risk']:.2f}")
        print(f"   Overall Risk: {result['risk_assessment']['overall_risk_score']:.2f}")
        print(f"   Adjustment Factor: {result['risk_assessment']['risk_adjustment_factor']:.2f}")
        
        print(f"\n5. FINAL CREDITS:")
        print(f"   Gross Credits: {result['final_credits']['gross_credits_tco2e']:.2f} tCO₂e")
        print(f"   Net Credits: {result['final_credits']['net_credits_tco2e']:.2f} tCO₂e")
        print(f"   Credits/ha: {result['final_credits']['credits_per_hectare']:.2f} tCO₂e/ha")
        
        print(f"\n6. INTEGRITY SCORE: {result['integrity_score']}/100")
        print("="*60)
