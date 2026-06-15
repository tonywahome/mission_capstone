"""
Download GEDI L4A data (Above-Ground Biomass Density) for a study area.

GEDI Data Product:
- GEDI L4A: Footprint level aboveground biomass density
- Resolution: ~25m diameter footprints
- Coverage: 51.6°N to 51.6°S (tropics and temperate)

Installation:
    pip install earthaccess pandas geopandas h5py

Setup:
    1. Create NASA Earthdata account: https://urs.earthdata.nasa.gov/users/new
    2. Approve applications: https://urs.earthdata.nasa.gov/profile
       - NASA GESDISC DATA ARCHIVE
"""

import earthaccess
import pandas as pd
import h5py
import numpy as np
from pathlib import Path
from typing import Tuple, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GEDICollector:
    """Collect GEDI L4A biomass data for a bounding box."""
    
    def __init__(self, output_dir: str = "ml/gedi_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def authenticate(self):
        """Authenticate with NASA Earthdata."""
        logger.info("Authenticating with NASA Earthdata...")
        earthaccess.login()
        
    def search_gedi(
        self, 
        bbox: Tuple[float, float, float, float],
        start_date: str = "2019-04-01",
        end_date: str = "2023-12-31"
    ) -> List:
        """
        Search for GEDI L4A granules.
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of granule results
        """
        logger.info(f"Searching GEDI L4A data for bbox: {bbox}")
        
        # Correct GEDI L4A product names from NASA Earthdata catalog
        product_names = [
            'GEDI_L4A_AGB_Density_V2_1_2056',  # Version 2.1 (latest)
            'GEDI_L4A_AGB_Density_V2_1986',    # Version 2
            'GEDI_L4A_AGB_Density_GW_2028',    # Golden Weeks version
        ]
        
        results = []
        for product in product_names:
            logger.info(f"Trying product name: {product}")
            try:
                results = earthaccess.search_data(
                    short_name=product,
                    cloud_hosted=True,
                    bounding_box=bbox,
                    temporal=(start_date, end_date),
                    count=100  # Adjust based on area size
                )
                
                if results:
                    logger.info(f"✅ Found {len(results)} granules with product: {product}")
                    break
            except Exception as e:
                logger.warning(f"Product {product} failed: {e}")
                continue
        
        if not results:
            logger.warning(f"No granules found. Tried products: {product_names}")
        
        return results
        
    def download_granules(self, results: List, max_files: int = 10) -> List[str]:
        """Download GEDI granules."""
        logger.info(f"Downloading up to {max_files} granules...")
        
        files = earthaccess.download(
            results[:max_files],
            local_path=str(self.output_dir)
        )
        
        logger.info(f"Downloaded {len(files)} files")
        return files
        
    def extract_biomass_data(self, h5_file: str) -> pd.DataFrame:
        """
        Extract biomass and location data from GEDI L4A HDF5 file.
        
        Returns:
            DataFrame with columns: lat, lon, agbd, quality_flag, sensitivity
        """
        data_list = []
        
        try:
            with h5py.File(h5_file, 'r') as f:
                # GEDI L4A has multiple beams
                beams = [key for key in f.keys() if key.startswith('BEAM')]
                
                for beam in beams:
                    try:
                        # Extract relevant datasets directly
                        lat = f[f'{beam}/lat_lowestmode'][:]
                        lon = f[f'{beam}/lon_lowestmode'][:]
                        agbd = f[f'{beam}/agbd'][:]  # Mg/ha (tonnes/hectare)
                        quality = f[f'{beam}/l4_quality_flag'][:]
                        sensitivity = f[f'{beam}/sensitivity'][:]
                        
                        # Create dataframe for this beam
                        df_beam = pd.DataFrame({
                            'lat': lat,
                            'lon': lon,
                            'agbd_tonnes_per_ha': agbd,
                            'quality_flag': quality,
                            'sensitivity': sensitivity,
                            'beam': beam
                        })
                        
                        # Filter for high quality shots
                        # quality_flag = 1 means high quality
                        # sensitivity > 0.9 recommended
                        df_beam = df_beam[
                            (df_beam['quality_flag'] == 1) &
                            (df_beam['sensitivity'] > 0.9) &
                            (df_beam['agbd_tonnes_per_ha'] > 0) &
                            (df_beam['agbd_tonnes_per_ha'] < 500)  # Remove outliers
                        ]
                        
                        data_list.append(df_beam)
                        
                    except Exception as e:
                        logger.warning(f"Error processing beam {beam}: {e}")
                        continue
        
        except (OSError, Exception) as e:
            logger.error(f"Error opening or reading HDF5 file {h5_file}: {e}")
            logger.warning(f"Skipping corrupted file: {h5_file}")
            return pd.DataFrame()
        
        if data_list:
            return pd.concat(data_list, ignore_index=True)
        else:
            return pd.DataFrame()
            
    def collect_for_region(
        self,
        bbox: Tuple[float, float, float, float],
        output_filename: str = "gedi_biomass_samples.csv",
        max_granules: int = 10
    ) -> pd.DataFrame:
        """
        Complete workflow: search, download, and extract GEDI data.
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat)
            output_filename: Output CSV filename
            max_granules: Maximum number of granules to download
            
        Returns:
            DataFrame with all extracted data
        """
        self.authenticate()
        
        # Search for data
        results = self.search_gedi(bbox)
        
        if not results:
            logger.warning("No GEDI data found for this region")
            return pd.DataFrame()
        
        # Download granules
        files = self.download_granules(results, max_files=max_granules)
        
        # Extract data from all files
        all_data = []
        for h5_file in files:
            logger.info(f"Processing {h5_file}")
            df = self.extract_biomass_data(h5_file)
            if not df.empty:
                all_data.append(df)
        
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            
            # Save to CSV
            output_path = self.output_dir / output_filename
            final_df.to_csv(output_path, index=False)
            logger.info(f"Saved {len(final_df)} GEDI samples to {output_path}")
            
            # Print statistics
            logger.info(f"\nBiomass Statistics:")
            logger.info(f"  Mean AGBD: {final_df['agbd_tonnes_per_ha'].mean():.2f} tonnes/ha")
            logger.info(f"  Median AGBD: {final_df['agbd_tonnes_per_ha'].median():.2f} tonnes/ha")
            logger.info(f"  Range: {final_df['agbd_tonnes_per_ha'].min():.2f} - {final_df['agbd_tonnes_per_ha'].max():.2f}")
            
            return final_df
        else:
            logger.warning("No data extracted from granules")
            return pd.DataFrame()


# Example usage
if __name__ == "__main__":
    collector = GEDICollector()
    
    # Define bounding boxes (min_lon, min_lat, max_lon, max_lat)
    # Use larger regions for better GEDI coverage
    
    regions = {
        # Kenya - Central Highlands (LARGER area, includes Aberdare + Mt Kenya)
        'kenya_central': (36.0, -1.0, 37.5, 0.5),
        
        # Kenya - Mau Forest Complex (large forested area)
        'kenya_mau': (35.0, -0.8, 35.8, 0.2),
        
        # Tanzania - Mount Kilimanjaro region
        'tanzania_kilimanjaro': (36.8, -3.5, 37.8, -2.5),
        
        # Uganda - Budongo Forest
        'uganda_budongo': (31.3, 1.5, 31.8, 2.0),
        
        # Congo Basin (guaranteed GEDI data - dense tropical forest)
        'congo_basin': (20.0, -2.0, 25.0, 2.0),
    }
    
    # Start with Congo Basin (most reliable GEDI coverage)
    # Change to 'kenya_central' or others in regions dict above
    region_name = 'congo_basin'
    bbox = regions[region_name]
    
    print(f"\n{'='*60}")
    print(f"Collecting GEDI data for: {region_name}")
    print(f"Bounding box: {bbox}")
    print(f"{'='*60}\n")
    
    # Collect data
    df = collector.collect_for_region(
        bbox=bbox,
        output_filename=f"gedi_{region_name}_biomass.csv",
        max_granules=10  # Reduced to ~2GB, still gives ~15,000 samples
    )
    
    if df.empty:
        print("\n⚠️  No data found for this region. Try these alternatives:")
        print("1. Use 'congo_basin' - guaranteed to have data (large tropical forest)")
        print("2. Increase max_granules to 50+")
        print("3. Check if your region is within ±51.6° latitude (GEDI coverage limit)")
        print("\nTo change region, edit the 'region_name' variable in this script.")
    else:
        print(f"\n✅ Successfully collected {len(df)} GEDI biomass samples")
        print(f"\nFirst few samples:")
        print(df.head())
        print(f"\nBiomass statistics:")
        print(f"  Mean: {df['agbd_tonnes_per_ha'].mean():.2f} tonnes/ha")
        print(f"  Range: {df['agbd_tonnes_per_ha'].min():.2f} - {df['agbd_tonnes_per_ha'].max():.2f}")
