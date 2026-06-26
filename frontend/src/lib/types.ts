export interface LandPlot {
  id: string;
  owner_id: string;
  name: string;
  geometry: GeoJSON.Polygon;
  area_hectares: number;
  region: string | null;
  land_use: "forest" | "grassland" | "cropland" | "wetland" | "agroforestry";
}

export interface ScanResult {
  scan_id: string;
  plot_id: string | null;
  mean_ndvi: number;
  mean_evi: number;
  estimated_biomass: number;
  estimated_tco2e: number;
  carbon_density: number;
  integrity_score: number;
  buy_price_per_tonne: number;
  risk_adjustment: number;
  raw_bands?: Record<string, number>;
}

// NOTE: CarbonCredit, Transaction, and FootprintResult interfaces (and the
// matching api.ts functions for /api/credits, /api/transactions,
// /api/certificates, /api/dashboard/footprint) were removed here as part of
// the capstone re-scope. Those endpoints belong to the TerraFoma LTD
// marketplace product and are not mounted in this prototype's backend
// (see backend/main.py) — the types had zero live call sites. See
// backend/legacy/ and frontend/legacy/ for the preserved marketplace code.

export interface MonitoringReport {
  id: string;
  plot_id: string;
  check_date: string;
  current_ndvi: number;
  baseline_ndvi: number;
  delta_ndvi: number;
  z_score: number;
  n_historical_scans: number;
  data_quality: string;
  classification: "stable" | "improving" | "degrading" | "acute_disturbance";
  alert_level: "info" | "positive" | "warning" | "critical";
  cause: string;
  explanation: string;
  recommendation: string;
  spectral_context?: {
    ndvi: number | null;
    evi: number | null;
    ndmi: number | null;
    nbr: number | null;
  };
}

export interface PlotWithMonitoring {
  id: string;
  owner_id: string;
  name: string;
  area_hectares: number;
  region: string | null;
  land_use: string;
  geometry?: any;
  baseline_agbd?: number | null;
  baseline_ndvi?: number | null;
  baseline_scan_date?: string | null;
  latest_scan?: {
    mean_ndvi: number;
    estimated_tco2e: number;
    estimated_biomass: number;
    created_at: string;
  } | null;
  latest_monitoring?: MonitoringReport | null;
}
