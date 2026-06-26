"""
TerraFoma — Rwanda GEDI + Sentinel-2 Export via Python earthengine-api

Use this if you prefer running from the terminal instead of the GEE Code Editor.

Setup (one-time):
    pip install earthengine-api
    earthengine authenticate          # opens browser for Google login
    earthengine set_project YOUR_PROJECT_ID

Run:
    python gee_export_rwanda.py

The CSV lands in Google Drive → TerraFoma/sentinel_gedi_training_v2.csv
Copy it to: backend/ml/data/sentinel_gedi_training_v2.csv
Then re-run train_biomass_model.ipynb
"""

import ee
import sys

# ── Authenticate ───────────────────────────────────────────────────────────────
try:
    ee.Initialize(opt_url='https://earthengine.googleapis.com')
    print("Earth Engine initialised ✓")
except Exception:
    print("Authenticating — a browser window will open...")
    ee.Authenticate()
    ee.Initialize()
    print("Authenticated ✓")


# ── AOI: Rwanda ────────────────────────────────────────────────────────────────
rwanda = (ee.FeatureCollection('FAO/GAUL/2015/level0')
          .filter(ee.Filter.eq('ADM0_NAME', 'Rwanda'))
          .geometry())


# ── Helpers ────────────────────────────────────────────────────────────────────

def mask_s2_clouds(image):
    scl  = image.select('SCL')
    mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return image.updateMask(mask).divide(10000)


def add_indices(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi')
    evi  = image.expression(
        '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
        {'NIR': image.select('B8'), 'RED': image.select('B4'), 'BLUE': image.select('B2')}
    ).rename('evi')
    savi = image.expression(
        '1.5 * ((NIR - RED) / (NIR + RED + 0.5))',
        {'NIR': image.select('B8'), 'RED': image.select('B4')}
    ).rename('savi')
    ndmi = image.normalizedDifference(['B8', 'B11']).rename('ndmi')
    nbr  = image.normalizedDifference(['B8', 'B12']).rename('nbr')
    reci = image.expression(
        '(NIR / RE1) - 1',
        {'NIR': image.select('B8'), 'RE1': image.select('B5')}
    ).rename('reci')
    return image.addBands([ndvi, evi, savi, ndmi, nbr, reci])


# ── GEDI L4A ──────────────────────────────────────────────────────────────────
print("Building GEDI sample points...")

gedi_mosaic = (ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY')
               .filterBounds(rwanda)
               .filterDate('2020-01-01', '2023-12-31')
               .select(['agbd', 'agbd_se', 'l4_quality_flag', 'sensitivity'])
               .filter(ee.Filter.eq('l4_quality_flag', 1))
               .mosaic()
               .clip(rwanda))

gedi_points = gedi_mosaic.stratifiedSample(
    numPoints=8000,
    classBand=None,
    region=rwanda,
    scale=25,
    projection='EPSG:4326',
    seed=42,
    geometries=True,
    dropNulls=True,
)

# Quality filters
def add_rel_error(f):
    rel = ee.Number(f.get('agbd_se')).divide(ee.Number(f.get('agbd')))
    return f.set('agbd_relative_error', rel)

gedi_points = (gedi_points
               .filter(ee.Filter.gt('agbd', 1.0))
               .filter(ee.Filter.lt('agbd', 600))
               .filter(ee.Filter.notNull(['agbd_se']))
               .map(add_rel_error)
               .filter(ee.Filter.lt('agbd_relative_error', 0.5)))

n = gedi_points.size().getInfo()
print(f"  GEDI points after quality filter: {n:,}")


# ── Sentinel-2 dry season (Jun–Aug 2022) ──────────────────────────────────────
print("Building Sentinel-2 dry season composite...")

s2_dry = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
          .filterBounds(rwanda)
          .filterDate('2022-06-01', '2022-08-31')
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
          .map(mask_s2_clouds)
          .map(add_indices))

dry_composite = s2_dry.median().clip(rwanda)
dry_renamed = dry_composite.select(
    ['B2',       'B3',        'B4',      'B5',      'B6',      'B7',      'B8',      'B8A',      'B11',       'B12',       'ndvi',     'evi',     'savi',     'ndmi',     'nbr',     'reci'],
    ['dry_blue', 'dry_green', 'dry_red', 'dry_re1', 'dry_re2', 'dry_re3', 'dry_nir', 'dry_nir2', 'dry_swir1', 'dry_swir2', 'dry_ndvi', 'dry_evi', 'dry_savi', 'dry_ndmi', 'dry_nbr', 'dry_reci']
)

print(f"  Dry images: {s2_dry.size().getInfo()}")


# ── Sentinel-2 wet season (Mar–May 2022) ──────────────────────────────────────
print("Building Sentinel-2 wet season composite...")

s2_wet = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
          .filterBounds(rwanda)
          .filterDate('2022-03-01', '2022-05-31')
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
          .map(mask_s2_clouds)
          .map(add_indices))

wet_composite = s2_wet.median().clip(rwanda)
wet_renamed = wet_composite.select(
    ['B8',      'B11',       'ndvi',     'evi',     'savi'],
    ['wet_nir', 'wet_swir1', 'wet_ndvi', 'wet_evi', 'wet_savi']
)

delta_ndvi = (wet_renamed.select('wet_ndvi')
              .subtract(dry_renamed.select('dry_ndvi'))
              .rename('delta_ndvi'))

print(f"  Wet images: {s2_wet.size().getInfo()}")


# ── Sentinel-1 SAR ────────────────────────────────────────────────────────────
print("Building SAR composite...")

s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
      .filterBounds(rwanda)
      .filterDate('2022-01-01', '2022-12-31')
      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
      .filter(ee.Filter.eq('instrumentMode', 'IW'))
      .select(['VV', 'VH']))

sar = (s1.median().clip(rwanda)
       .rename(['vv', 'vh']))
sar = sar.addBands(sar.select('vh').subtract(sar.select('vv')).rename('vh_vv_diff'))


# ── Terrain ────────────────────────────────────────────────────────────────────
srtm    = ee.Image('USGS/SRTMGL1_003').clip(rwanda)
terrain = (srtm.select('elevation')
           .addBands(ee.Terrain.slope(srtm).rename('slope'))
           .addBands(ee.Terrain.aspect(srtm).rename('aspect')))


# ── Stack and sample ──────────────────────────────────────────────────────────
print("Sampling all layers at GEDI points (this may take a moment)...")

all_layers = (dry_renamed
              .addBands(wet_renamed)
              .addBands(delta_ndvi)
              .addBands(sar)
              .addBands(terrain))

sampled = all_layers.sampleRegions(
    collection=gedi_points,
    scale=25,
    projection='EPSG:4326',
    tileScale=4,
    geometries=True,
)


def add_lat_lon(f):
    coords = f.geometry().coordinates()
    return (f.set('lon', coords.get(0))
             .set('lat', coords.get(1))
             .set('agbd_tonnes_per_ha', f.get('agbd'))
             .setGeometry(None))

sampled = sampled.map(add_lat_lon)


# ── Export ─────────────────────────────────────────────────────────────────────
print("Submitting export task to Google Drive...")

task = ee.batch.Export.table.toDrive(
    collection=sampled,
    description='terrafoma_rwanda_training_v2',
    folder='TerraFoma',
    fileNamePrefix='sentinel_gedi_training_v2',
    fileFormat='CSV',
)
task.start()

print(f"""
Export task submitted ✓
  Task ID: {task.id}
  Status:  {task.status()['state']}

Monitor progress:
  python -c "import ee; ee.Initialize(); t = ee.batch.Task.list()[0]; print(t.status())"

Or check: https://code.earthengine.google.com/tasks

When done:
  1. Download from Google Drive → TerraFoma/sentinel_gedi_training_v2.csv
  2. Copy to:  backend/ml/data/sentinel_gedi_training_v2.csv
  3. Run:      train_biomass_model.ipynb
""")
