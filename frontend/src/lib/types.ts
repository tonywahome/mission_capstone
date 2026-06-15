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

export interface CarbonCredit {
  id: string;
  scan_id?: string;
  plot_id: string;
  owner_id: string;
  vintage_year: number;
  quantity_tco2e: number;
  price_per_tonne: number;
  status: "pending" | "verified" | "listed" | "sold" | "retired";
  integrity_score: number;
  risk_score: number;
  permanence_discount: number;
  listed_at?: string;
  sold_at?: string;
  retired_at?: string;
  created_at?: string;
  region?: string;
  plot_name?: string;
}

export interface Transaction {
  id: string;
  credit_id: string;
  buyer_id: string;
  seller_id?: string;
  quantity_tco2e: number;
  total_price: number;
  currency: string;
  certificate_url?: string;
  status: string;
  created_at?: string;
}

export interface FootprintResult {
  annual_tco2e: number;
  monthly_tco2e: number;
  // GHG Protocol scope totals
  scope1_tco2e: number;
  scope2_tco2e: number;
  scope3_tco2e: number;
  // Individual sources
  electricity_tco2e: number;
  fuel_tco2e: number;
  natural_gas_tco2e: number;
  refrigerant_tco2e: number;
  flights_tco2e: number;
  waste_tco2e: number;
  water_tco2e: number;
  freight_tco2e: number;
  freight_sea_tco2e: number;
  supply_chain_tco2e: number;
  breakdown: {
    electricity: number;
    fuel: number;
    natural_gas: number;
    refrigerant: number;
    flights: number;
    waste: number;
    water: number;
    freight_road: number;
    freight_sea: number;
    supply_chain: number;
  };
}

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

export interface CreditStats {
  total_credits: number;
  total_verified: number;
  total_listed: number;
  total_sold: number;
  total_retired: number;
  total_tco2e: number;
  avg_price: number;
  avg_integrity: number;
}
