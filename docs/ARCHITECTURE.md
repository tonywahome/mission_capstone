# TerraFoma System Architecture

## Overview

TerraFoma is a full-stack carbon credit platform consisting of three main components:
1. **Backend API** - FastAPI server with ML integration
2. **Frontend Web App** - Next.js marketplace and dashboard
3. **ML Pipeline** - Satellite data processing and biomass estimation

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dashboard   │  │ Marketplace  │  │  Registry    │          │
│  │  (Scanning)  │  │  (Credits)   │  │ (Tracking)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                 │
│                           │                                      │
│                    HTTP/REST API                                 │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    API Routers                           │    │
│  │  /scan  /credits  /dashboard  /certificates             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Business Logic                         │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │   Biomass    │  │   Carbon     │  │     Risk     │  │    │
│  │  │  Estimator   │  │  Calculator  │  │    Scorer    │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               In-Memory Database                         │    │
│  │  { carbon_credits, scan_results, transactions }         │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┼──────────────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────────────┐
│                      ML Pipeline                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │        Trained Model (biomass_model_v1.pkl)             │    │
│  │        Random Forest Regressor (R²=0.53)                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Google Earth Engine                         │    │
│  │  • Sentinel-2 imagery    • SRTM elevation               │    │
│  │  • GEDI biomass data     • Feature extraction           │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (Next.js + React)

**Technology Stack:**
- Next.js 14.2 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Mapbox GL JS

**Key Pages:**

#### `/` (Landing Page)
- Hero section with value proposition
- Feature highlights
- Call-to-action buttons

#### `/dashboard` (Biomass Scanning)
- Interactive Mapbox map
- Plot selection tool (click to select location)
- Real-time biomass estimation
- Results display with carbon metrics
- Risk and integrity scores

#### `/marketplace` (Carbon Credits)
- **Impact Dashboard:** 
  - Total carbon available
  - Community funding generated
  - Active projects count
- **Filter Tabs:**
  - All credits
  - Premium tier
  - Standard tier
- **Credit Cards:**
  - Project details (location, area, biomass)
  - Quality tier badge
  - Carbon offset amount
  - Price per tonne
  - Community benefit (60%)
  - Risk gauge
  - Purchase button

#### `/registry` (Credit Registry)
- List of all issued credits
- Transaction history
- Credit status (available, sold, retired)

#### `/certificate/[id]` (Certificate Viewer)
- Downloadable PDF certificate
- Credit details and verification info
- QR code for verification

**API Client (`lib/api.ts`):**
```typescript
export const api = {
  scanPlot: (lat, lon, buffer_m, land_use) => POST /api/scan
  getCredits: (status?) => GET /api/credits
  getCreditById: (id) => GET /api/credits/{id}
  getDashboard: () => GET /api/dashboard
  getCertificate: (id) => GET /api/certificate/{id}
}
```

### 2. Backend (FastAPI + Python)

**Technology Stack:**
- FastAPI 0.110+
- Python 3.13
- Joblib (model serialization)
- Google Earth Engine API
- NumPy + scikit-learn

**API Structure:**

#### Routers (`routers/`)

**`scan.py` - Plot Scanning**
```python
POST /api/scan
{
  "lat": float,
  "lon": float,
  "buffer_m": float,
  "land_use": str
}
→ Returns biomass, tCO2e, price, community benefit
```

**`credits.py` - Carbon Credits**
```python
GET /api/credits?status=listed
→ Returns list of available credits

GET /api/credits/{id}
→ Returns detailed credit information
```

**`dashboard.py` - Analytics**
```python
GET /api/dashboard
→ Returns system-wide statistics
```

**`certificates.py` - Certificate Generation**
```python
GET /api/certificate/{id}
→ Returns PDF certificate or metadata
```

#### Services (`services/`)

**`biomass_estimator.py`**
```python
def estimate_biomass(lat, lon, buffer_m, land_use):
    # 1. Load trained model
    model = joblib.load("ml/models/biomass_model_v1.pkl")
    
    # 2. Get satellite features from Earth Engine
    features = get_ee_features(lat, lon, buffer_m)
    
    # 3. Predict biomass
    biomass = model.predict([features])
    
    # 4. Calculate carbon
    tco2e = biomass_to_tco2e(biomass, area_ha)
    
    return biomass, tco2e
```

**`carbon_calculator.py`**
```python
def calculate_credit_price(tco2e, integrity_score, risk_score):
    # Quality tier determination
    if integrity_score > 90 and risk_score < 0.15:
        tier = "Premium"
        price = 35.0
    elif integrity_score > 80:
        tier = "High"
        price = calculate_premium_price(...)
    elif integrity_score > 70:
        tier = "Standard"
        price = 18.0
    else:
        tier = "Basic"
        price = 12.0
    
    return price, tier

def calculate_community_benefit(total_value):
    community_direct = total_value * 0.45  # 45%
    conservation_fund = total_value * 0.15  # 15%
    platform_fee = total_value * 0.40      # 40%
    
    return {
        "community_direct": community_direct,
        "conservation_fund": conservation_fund,
        "platform_fee": platform_fee
    }
```

**`risk_scorer.py`**
```python
def calculate_risk_score(features):
    # Factors considered:
    # - Land use type stability
    # - Proximity to deforestation
    # - Historical biomass trends
    # - Socioeconomic factors
    
    risk = base_risk * land_use_multiplier * proximity_factor
    return min(max(risk, 0.0), 1.0)
```

#### Database (`database.py`)

**In-Memory Database Implementation:**
```python
class InMemoryDB:
    def __init__(self):
        self.data = {
            "carbon_credits": [],
            "scan_results": [],
            "transactions": [],
            "land_plots": [],
            "audit_log": []
        }
        self.initialize_sample_data()
    
    def table(self, name):
        return InMemoryTable(self.data[name])

class InMemoryTable:
    # Supabase-compatible query interface
    def select(self, *columns): ...
    def eq(self, field, value): ...
    def gte(self, field, value): ...
    def order(self, field, desc=False): ...
    def execute(self): ...
    def insert(self, data): ...
    def update(self, data): ...
```

**Sample Credits:**
5 pre-populated conservation projects from Kenya with realistic data:
- Aberdare Forest (Nyeri)
- Mount Kenya Woodland (Meru)
- Kakamega Rainforest (Kakamega)
- Mau Forest Complex (Nakuru)
- Loita Forest (Narok)

### 3. ML Pipeline

**Training Data Collection:**

```python
# collect_sentinel_data.py
def collect_sentinel_features(lat, lon, start_date, end_date):
    # 1. Define region
    region = ee.Geometry.Point([lon, lat]).buffer(1000)
    
    # 2. Get Sentinel-2 image collection
    s2 = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterBounds(region) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # 3. Calculate median composite
    composite = s2.median()
    
    # 4. Extract spectral bands
    bands = ['B1','B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12']
    
    # 5. Calculate vegetation indices
    ndvi = composite.normalizedDifference(['B8', 'B4'])
    evi = composite.expression(...)
    savi = composite.expression(...)
    ndmi = composite.normalizedDifference(['B8', 'B11'])
    
    # 6. Add elevation features
    elevation = ee.Image('USGS/SRTMGL1_003')
    slope = ee.Terrain.slope(elevation)
    
    return extract_features(composite, ndvi, evi, savi, ndmi, elevation, slope)

# collect_gedi_data.py
def collect_gedi_biomass(region, start_date, end_date):
    # 1. Get GEDI L4A biomass product
    gedi = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY') \
        .filterBounds(region) \
        .filterDate(start_date, end_date)
    
    # 2. Extract agbd (Above Ground Biomass Density)
    biomass = gedi.select('agbd').mean()
    
    return biomass
```

**Model Training Process:**

```python
# train_biomass_model.ipynb

# 1. Load training data
df = pd.read_csv('data/sentinel_gedi_training.csv')
# Columns: B1-B12, NDVI, EVI, SAVI, NDMI, elevation, slope, biomass

# 2. Prepare features and target
X = df.drop('biomass', axis=1)
y = df['biomass']

# 3. Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 4. Train model
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=20,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42
)
model.fit(X_train, y_train)

# 5. Evaluate
y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)

# 6. Save model
joblib.dump({
    'model': model,
    'feature_names': X.columns.tolist(),
    'test_r2': r2,
    'test_mae': mae
}, 'models/biomass_model_v1.pkl')
```

**Feature Engineering:**

1. **Spectral Bands** (10 features)
   - B1: Coastal aerosol (443nm)
   - B2: Blue (490nm)
   - B3: Green (560nm)
   - B4: Red (665nm)
   - B5: Red edge 1 (705nm)
   - B6: Red edge 2 (740nm)
   - B7: Red edge 3 (783nm)
   - B8: NIR (842nm)
   - B11: SWIR 1 (1610nm)
   - B12: SWIR 2 (2190nm)

2. **Vegetation Indices** (4 features)
   - NDVI: (NIR - Red) / (NIR + Red)
   - EVI: 2.5 * ((NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1))
   - SAVI: ((NIR - Red) / (NIR + Red + 0.5)) * 1.5
   - NDMI: (NIR - SWIR1) / (NIR + SWIR1)

3. **Topographic Features** (2 features)
   - Elevation (meters)
   - Slope (degrees)

**Total Features:** 16 input features → 1 output (biomass t/ha)

## Data Flow

### Biomass Scanning Flow

```
1. User clicks on map (lat, lon)
   ↓
2. Frontend sends POST /api/scan
   ↓
3. Backend receives request
   ↓
4. biomass_estimator.estimate_biomass()
   ↓
5. Query Google Earth Engine
   • Get Sentinel-2 composite
   • Extract 16 features
   • Get elevation/slope
   ↓
6. Load ML model
   • biomass_model_v1.pkl
   ↓
7. Predict biomass
   • model.predict(features)
   ↓
8. Calculate carbon
   • tCO2e = biomass * 0.47 * 3.667
   ↓
9. Calculate pricing
   • Determine quality tier
   • Apply pricing algorithm
   ↓
10. Calculate community benefit
   • 60% of total value
   ↓
11. Return results to frontend
   ↓
12. Display on dashboard
```

### Credit Purchase Flow

```
1. User browses marketplace
   ↓
2. Frontend loads GET /api/credits?status=listed
   ↓
3. Backend queries in-memory database
   ↓
4. Return list of credits
   ↓
5. User clicks "Purchase"
   ↓
6. Frontend shows confirmation
   (would trigger payment in production)
   ↓
7. Backend updates credit status
   ↓
8. Generate certificate
   ↓
9. Display success + certificate link
```

## Performance Considerations

### Backend Optimization

1. **Model Caching**
   - ML model loaded once at startup
   - Stored in global variable
   - Reused for all predictions

2. **Earth Engine Optimization**
   - Use `.median()` for cloud-free composites
   - Filter by cloud percentage < 20%
   - Reduce resolution for faster processing

3. **API Response Time**
   - Target: < 5 seconds for scan
   - Earth Engine query: ~2-3s
   - Model prediction: < 100ms
   - Pricing calculation: < 10ms

### Frontend Optimization

1. **Code Splitting**
   - Next.js automatic code splitting
   - Route-based lazy loading

2. **Image Optimization**
   - Next.js Image component
   - WebP format support

3. **API Caching**
   - Cache credit listings (5 min TTL)
   - Invalidate on updates

## Security

### API Security

1. **CORS Configuration**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3001"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"]
   )
   ```

2. **Input Validation**
   - Pydantic models for request validation
   - Lat/lon bounds checking
   - Buffer size limits

3. **Rate Limiting** (TODO)
   - Implement per-IP rate limits
   - Prevent API abuse

### Data Security

1. **Environment Variables**
   - API keys stored in .env
   - Never committed to git
   - Loaded via python-dotenv

2. **Earth Engine Authentication**
   - Service account credentials
   - Project-specific access
   - Read-only permissions

## Scalability

### Current Limitations

1. **In-Memory Database**
   - Data lost on restart
   - No persistence
   - Single-server only

2. **Earth Engine Quotas**
   - 25,000 requests/day (free tier)
   - ~1 second per request

### Future Improvements

1. **Database Migration**
   - Move to Supabase/PostgreSQL
   - Persistent storage
   - Multi-server support
   - Database schema:
     ```sql
     CREATE TABLE carbon_credits (
       id UUID PRIMARY KEY,
       project_name TEXT,
       location TEXT,
       area_ha FLOAT,
       biomass_t_per_ha FLOAT,
       quantity_tco2e FLOAT,
       price_per_tonne FLOAT,
       integrity_score FLOAT,
       risk_score FLOAT,
       status TEXT,
       created_at TIMESTAMP
     );
     ```

2. **Caching Layer**
   - Redis for Earth Engine results
   - Cache common locations
   - TTL: 7 days for satellite data

3. **Background Processing**
   - Celery task queue
   - Async Earth Engine queries
   - Batch processing support

4. **Load Balancing**
   - Multiple FastAPI instances
   - Nginx reverse proxy
   - Horizontal scaling

## Monitoring & Observability

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log levels:
# - INFO: API requests, model loading
# - WARNING: Slow queries, model issues
# - ERROR: API failures, GEE errors
```

### Metrics (TODO)

- API response times
- Model prediction latency
- Earth Engine query time
- Credit purchase rate
- Error rates

### Error Handling

1. **Earth Engine Errors**
   ```python
   try:
       features = get_ee_features(lat, lon, buffer_m)
   except ee.EEException as e:
       logger.error(f"Earth Engine error: {e}")
       raise HTTPException(status_code=503, detail="Satellite data unavailable")
   ```

2. **Model Errors**
   ```python
   if _biomass_model_data is None:
       raise HTTPException(status_code=500, detail="Model not loaded")
   ```

## Testing Strategy

### Unit Tests
- Model loading and prediction
- Pricing calculations
- Community benefit calculations
- Feature extraction

### Integration Tests
- API endpoint tests
- Database operations
- Earth Engine integration

### E2E Tests
- Full scan workflow
- Credit purchase flow
- Certificate generation

## Deployment

### Development
```bash
# Backend
uvicorn main:app --reload --port 8002

# Frontend
npm run dev
```

### Production (TODO)
```bash
# Backend
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
npm run build
npm start
```

### Environment Variables

**Backend (.env):**
```
EARTHENGINE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
SUPABASE_URL=https://xxx.supabase.co  # Optional
SUPABASE_KEY=your-key  # Optional
```

**Frontend (.env.local):**
```
NEXT_PUBLIC_MAPBOX_TOKEN=pk.xxx
NEXT_PUBLIC_API_URL=http://localhost:8002
```

## Conclusion

TerraFoma's architecture is designed for:
- **Rapid development** - Simple components, clear separation
- **Easy deployment** - Minimal infrastructure requirements
- **Future scalability** - Clear upgrade path to production
- **Community impact** - Transparent pricing and benefit distribution

The system successfully combines satellite ML with a user-friendly marketplace to democratize carbon credit verification and maximize community benefit.
