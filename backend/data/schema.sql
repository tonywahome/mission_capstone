-- TerraFoma Database Schema for Supabase
-- Run this in the Supabase SQL Editor

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email         TEXT UNIQUE NOT NULL,
  full_name     TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('landowner', 'buyer', 'admin')),
  company_name  TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- Land Plots
CREATE TABLE IF NOT EXISTS land_plots (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id      UUID REFERENCES users(id),
  name          TEXT NOT NULL,
  geometry      JSONB NOT NULL,
  area_hectares FLOAT NOT NULL,
  region        TEXT,
  land_use      TEXT CHECK (land_use IN ('forest', 'grassland', 'cropland', 'wetland', 'agroforestry')),
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- Scan Results
CREATE TABLE IF NOT EXISTS scan_results (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  plot_id             UUID REFERENCES land_plots(id) ON DELETE CASCADE,
  scan_date           TIMESTAMPTZ DEFAULT now(),
  mean_ndvi           FLOAT,
  mean_evi            FLOAT,
  estimated_biomass   FLOAT,
  estimated_tco2e     FLOAT,
  carbon_density      FLOAT,
  integrity_score     FLOAT CHECK (integrity_score BETWEEN 0 AND 100),
  model_version       TEXT DEFAULT 'rf_v1',
  raw_bands           JSONB,
  created_at          TIMESTAMPTZ DEFAULT now()
);

-- Carbon Credits
CREATE TABLE IF NOT EXISTS carbon_credits (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  scan_id           UUID REFERENCES scan_results(id),
  plot_id           UUID REFERENCES land_plots(id),
  owner_id          UUID REFERENCES users(id),
  vintage_year      INT NOT NULL,
  quantity_tco2e    FLOAT NOT NULL,
  price_per_tonne   FLOAT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'verified'
                      CHECK (status IN ('pending', 'verified', 'listed', 'sold', 'retired')),
  integrity_score   FLOAT CHECK (integrity_score BETWEEN 0 AND 100),
  risk_score        FLOAT CHECK (risk_score BETWEEN 0 AND 100),
  permanence_discount FLOAT DEFAULT 0,
  listed_at         TIMESTAMPTZ,
  sold_at           TIMESTAMPTZ,
  retired_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

-- Risk Assessments
CREATE TABLE IF NOT EXISTS risk_assessments (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  plot_id           UUID REFERENCES land_plots(id),
  assessment_date   TIMESTAMPTZ DEFAULT now(),
  drought_risk      FLOAT CHECK (drought_risk BETWEEN 0 AND 1),
  wildfire_risk     FLOAT CHECK (wildfire_risk BETWEEN 0 AND 1),
  deforestation_risk FLOAT CHECK (deforestation_risk BETWEEN 0 AND 1),
  political_risk    FLOAT CHECK (political_risk BETWEEN 0 AND 1),
  composite_risk    FLOAT CHECK (composite_risk BETWEEN 0 AND 1),
  weather_data      JSONB,
  created_at        TIMESTAMPTZ DEFAULT now()
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  credit_id         UUID REFERENCES carbon_credits(id),
  buyer_id          UUID REFERENCES users(id),
  seller_id         UUID REFERENCES users(id),
  quantity_tco2e    FLOAT NOT NULL,
  total_price       FLOAT NOT NULL,
  currency          TEXT DEFAULT 'USD',
  certificate_url   TEXT,
  status            TEXT DEFAULT 'completed'
                      CHECK (status IN ('pending', 'completed', 'cancelled')),
  created_at        TIMESTAMPTZ DEFAULT now()
);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_type   TEXT NOT NULL,
  entity_id     UUID NOT NULL,
  action        TEXT NOT NULL,
  old_value     JSONB,
  new_value     JSONB,
  performed_by  UUID REFERENCES users(id),
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- Industrial Profiles
CREATE TABLE IF NOT EXISTS industrial_profiles (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) UNIQUE,
  company_name          TEXT NOT NULL,
  industry_sector       TEXT,
  annual_emissions_tco2 FLOAT,
  energy_kwh_monthly    FLOAT,
  fuel_litres_monthly   FLOAT,
  employees             INT,
  offset_target_pct     FLOAT DEFAULT 0,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security (optional for hackathon)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE land_plots ENABLE ROW LEVEL SECURITY;
