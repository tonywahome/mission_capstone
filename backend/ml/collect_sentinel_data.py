"""
Collect multi-sensor training data from Google Earth Engine (proposal Section 3.3.1).

Sources collected per sample location:
  - Sentinel-2 optical: spectral bands (B2–B12) + vegetation indices
  - Sentinel-1 SAR: VV and VH backscatter at 10 m (IW mode)
  - SRTM terrain: elevation and slope

Setup:
    1. Sign up for Google Earth Engine: https://signup.earthengine.google.com/
    2. Install: pip install earthengine-api geemap
    3. Authenticate: earthengine authenticate
"""

import ee
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import logging
from datetime import datetime, timedelta
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentinelCollector:
    """Collect Sentinel-2 features for GEDI sample locations."""
    
    def __init__(self):
        """Initialize Earth Engine."""
        try:
            ee.Initialize()
            logger.info("Earth Engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Earth Engine: {e}")
            logger.error("Run 'earthengine authenticate' first")
            raise
            
    def calculate_indices(self, image: ee.Image) -> ee.Image:
        """
        Calculate vegetation indices from Sentinel-2 bands.
        
        Sentinel-2 bands:
        - B2: Blue
        - B3: Green
        - B4: Red
        - B8: NIR
        - B11: SWIR1
        - B12: SWIR2
        """
        # Normalized Difference Vegetation Index
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Enhanced Vegetation Index
        evi = image.expression(
            '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
            {
                'NIR': image.select('B8'),
                'RED': image.select('B4'),
                'BLUE': image.select('B2')
            }
        ).rename('EVI')
        
        # Soil-Adjusted Vegetation Index (L=0.5 for typical vegetation)
        savi = image.expression(
            '((NIR - RED) / (NIR + RED + 0.5)) * 1.5',
            {
                'NIR': image.select('B8'),
                'RED': image.select('B4')
            }
        ).rename('SAVI')
        
        # Normalized Difference Moisture Index
        ndmi = image.normalizedDifference(['B8', 'B11']).rename('NDMI')
        
        # Normalized Burn Ratio (for fire detection)
        nbr = image.normalizedDifference(['B8', 'B12']).rename('NBR')
        
        return image.addBands([ndvi, evi, savi, ndmi, nbr])
        
    def get_sentinel_features(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        buffer_m: int = 50
    ) -> Dict:
        """
        Extract Sentinel-2 features for a point location.
        
        Args:
            lat: Latitude
            lon: Longitude
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            buffer_m: Buffer radius around point (meters)
            
        Returns:
            Dictionary with extracted features
        """
        point = ee.Geometry.Point([lon, lat])
        region = point.buffer(buffer_m)
        
        # Load Sentinel-2 Surface Reflectance collection
        collection = (
            ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(point)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            .map(self.calculate_indices)
        )
        
        # Check if any images available
        count = collection.size().getInfo()
        if count == 0:
            logger.warning(f"No Sentinel-2 images found for ({lat}, {lon})")
            return None
            
        # Create cloud-free composite (median)
        composite = collection.median()
        
        # Extract values at the point
        bands_to_extract = [
            'B2', 'B3', 'B4', 'B8', 'B11', 'B12',  # Spectral bands
            'NDVI', 'EVI', 'SAVI', 'NDMI', 'NBR'   # Indices
        ]
        
        try:
            # Sample the composite at the point
            sample = composite.select(bands_to_extract).sample(
                region=region,
                scale=10,  # 10m resolution
                geometries=False
            ).first()
            
            # Extract feature values
            features = sample.getInfo()['properties']
            
            # Add metadata
            features['lat'] = lat
            features['lon'] = lon
            features['n_images'] = count
            
            return features
            
        except Exception as e:
            logger.warning(f"Error extracting features for ({lat}, {lon}): {e}")
            return None
            
    def get_sentinel1_features(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        buffer_m: int = 50,
    ) -> Dict:
        """
        Extract Sentinel-1 SAR backscatter features (VV, VH) for a point.
        Returns empty dict if no imagery is available.
        """
        point  = ee.Geometry.Point([lon, lat])
        region = point.buffer(buffer_m)
        try:
            s1 = (
                ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(point)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
                .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
                .select(["VV", "VH"])
            )
            count = s1.size().getInfo()
            if count == 0:
                return {}
            composite = s1.median()
            vals = composite.sample(
                region=region, scale=10, geometries=False
            ).first().getInfo()["properties"]
            vv = vals.get("VV")
            vh = vals.get("VH")
            if vv is None or vh is None:
                return {}
            return {"vv": vv, "vh": vh, "vh_vv_diff": vh - vv}
        except Exception as e:
            logger.warning(f"SAR extraction failed for ({lat},{lon}): {e}")
            return {}

    def get_elevation_slope(self, lat: float, lon: float) -> Tuple[float, float]:
        """Get elevation and slope from SRTM DEM."""
        point = ee.Geometry.Point([lon, lat])

        try:
            dem = ee.Image('USGS/SRTMGL1_003')
            elevation = dem.select('elevation').sample(
                region=point,
                scale=30,
                geometries=False
            ).first().get('elevation').getInfo()

            slope_image = ee.Terrain.slope(dem)
            slope = slope_image.sample(
                region=point,
                scale=30,
                geometries=False
            ).first().get('slope').getInfo()

            return elevation, slope

        except:
            return None, None
            
    def match_sentinel_to_gedi(
        self,
        gedi_csv: str,
        output_csv: str = "training_data.csv",
        time_window_days: int = 30,
        max_samples: int = None
    ) -> pd.DataFrame:
        """
        Match Sentinel-2 features to GEDI biomass samples.
        
        Args:
            gedi_csv: Path to GEDI biomass CSV
            output_csv: Output CSV filename
            time_window_days: Days before/after GEDI shot to composite Sentinel-2
            max_samples: Maximum samples to process (for testing)
            
        Returns:
            DataFrame with matched training data
        """
        logger.info(f"Loading GEDI data from {gedi_csv}")
        gedi_df = pd.read_csv(gedi_csv)
        
        if max_samples:
            gedi_df = gedi_df.head(max_samples)
        
        # Check if output file exists and resume from last position
        output_path = Path(output_csv)
        start_idx = 0
        if output_path.exists():
            existing_df = pd.read_csv(output_path)
            start_idx = len(existing_df)
            logger.info(f"Resuming from sample {start_idx} (found {start_idx} existing samples)")
            training_data = existing_df.to_dict('records')
        else:
            training_data = []
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Processing {len(gedi_df)} GEDI samples (starting from {start_idx})...")
        
        # Assume GEDI data is from 2019-2023
        # For each point, get Sentinel-2 composite from surrounding months
        start_time = time.time()
        
        # Use a 6-month window centered on typical GEDI acquisition (growing season)
        start_date = "2020-01-01"
        end_date = "2020-12-31"
        
        for idx, row in gedi_df.iterrows():
            # Skip already processed samples
            if idx < start_idx:
                continue
            if idx % 10 == 0:  # Log every 10 samples instead of 100
                elapsed = time.time() - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                eta_seconds = (len(gedi_df) - idx) / rate if rate > 0 else 0
                logger.info(f"Processed {idx}/{len(gedi_df)} samples (Success: {len(training_data)}) "
                           f"- Rate: {rate:.2f} samples/sec - ETA: {eta_seconds/60:.1f} min")
                
            lat, lon = row['lat'], row['lon']
            agbd = row['agbd_tonnes_per_ha']
            
            # Retry logic for API calls (max 3 attempts)
            max_retries = 3
            retry_count = 0
            features = None
            elevation, slope = None, None
            
            while retry_count < max_retries and features is None:
                try:
                    # Get Sentinel-2 features
                    sample_start = time.time()
                    features = self.get_sentinel_features(
                        lat, lon, start_date, end_date, buffer_m=50
                    )
                    features_time = time.time() - sample_start
                    
                    if features is None:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"Sample {idx}: No features, retry {retry_count}/{max_retries}")
                            time.sleep(2)  # Wait before retry
                        continue
                        
                    # Get elevation and slope
                    elev_start = time.time()
                    elevation, slope = self.get_elevation_slope(lat, lon)
                    elev_time = time.time() - elev_start

                    # Get Sentinel-1 SAR features
                    sar_feats = self.get_sentinel1_features(
                        lat, lon, start_date, end_date, buffer_m=50
                    )
                    
                    total_time = time.time() - sample_start
                    if idx % 10 == 0:
                        logger.info(f"Sample {idx} timing: Sentinel={features_time:.2f}s, Elevation={elev_time:.2f}s, Total={total_time:.2f}s")
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Sample {idx}: Error on attempt {retry_count}: {e}")
                    if retry_count < max_retries:
                        time.sleep(5)  # Wait longer on error
                    else:
                        logger.error(f"Sample {idx}: Failed after {max_retries} attempts, skipping")
                        continue
            
            # Skip if all retries failed
            if features is None:
                logger.debug(f"Sample {idx}: Skipping after all retries")
                continue
            
            # Combine all features (Sentinel-2 + SAR + terrain)
            sample = {
                'lat': lat,
                'lon': lon,
                # Sentinel-2
                'blue': features.get('B2'),
                'green': features.get('B3'),
                'red': features.get('B4'),
                'nir': features.get('B8'),
                'swir1': features.get('B11'),
                'swir2': features.get('B12'),
                'ndvi': features.get('NDVI'),
                'evi': features.get('EVI'),
                'savi': features.get('SAVI'),
                'ndmi': features.get('NDMI'),
                'nbr': features.get('NBR'),
                # Sentinel-1 SAR
                'vv': sar_feats.get('vv'),
                'vh': sar_feats.get('vh'),
                'vh_vv_diff': sar_feats.get('vh_vv_diff'),
                # Terrain
                'elevation': elevation,
                'slope': slope,
                'n_images': features.get('n_images'),
                # Target
                'agbd_tonnes_per_ha': agbd,
            }
            
            # Check for missing values
            if None not in sample.values():
                training_data.append(sample)
                
                # Save incrementally every 50 samples to avoid data loss
                if len(training_data) % 50 == 0:
                    df_temp = pd.DataFrame(training_data)
                    df_temp.to_csv(output_path, index=False)
                    logger.info(f"💾 Saved checkpoint: {len(training_data)} samples")
                
        # Create DataFrame
        df = pd.DataFrame(training_data)
        
        # Save to CSV
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        logger.info(f"\nCreated training dataset with {len(df)} samples")
        logger.info(f"Saved to {output_path}")
        logger.info(f"\nFeature columns: {df.columns.tolist()}")
        logger.info(f"\nBiomass statistics:")
        logger.info(f"  Mean: {df['agbd_tonnes_per_ha'].mean():.2f}")
        logger.info(f"  Std: {df['agbd_tonnes_per_ha'].std():.2f}")
        logger.info(f"  Range: {df['agbd_tonnes_per_ha'].min():.2f} - {df['agbd_tonnes_per_ha'].max():.2f}")
        
        return df


# Example usage
if __name__ == "__main__":
    collector = SentinelCollector()
    
    # Get script directory
    script_dir = Path(__file__).parent  # backend/ml/
    
    # Process GEDI data collected earlier
    gedi_file = script_dir / "gedi_data" / "gedi_congo_basin_biomass.csv"
    output_file = script_dir / "sentinel_gedi_training.csv"  # Keep output in same directory
    
    # Create matched training dataset
    df = collector.match_sentinel_to_gedi(
        gedi_csv=str(gedi_file),
        output_csv=str(output_file),
        max_samples=12000  # Collect 12000 samples for improved model accuracy
    )
    
    print(f"\nTraining data shape: {df.shape}")
    print(f"\nFirst few samples:")
    print(df.head())
    
    # Check for missing values
    print(f"\nMissing values per column:")
    print(df.isnull().sum())
