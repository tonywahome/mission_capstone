-- Migration: Add Uncertainty and Model Info to Scan Results
-- Run this in the Supabase SQL Editor
-- Date: July 2, 2026
--
-- Purpose: Adds columns to support the uncertainty-reporting module and machine learning
-- model metadata (biomass_lower_90, biomass_upper_90, biomass_uncertainty_pct, model_type,
-- model_r2, and sensors_used) to the physical scan_results table.
--

ALTER TABLE scan_results 
ADD COLUMN IF NOT EXISTS biomass_lower_90 FLOAT,
ADD COLUMN IF NOT EXISTS biomass_upper_90 FLOAT,
ADD COLUMN IF NOT EXISTS biomass_uncertainty_pct FLOAT,
ADD COLUMN IF NOT EXISTS model_type TEXT,
ADD COLUMN IF NOT EXISTS model_r2 FLOAT,
ADD COLUMN IF NOT EXISTS sensors_used JSONB;

COMMENT ON COLUMN scan_results.biomass_lower_90 IS 'Lower bound of the 90% prediction interval for estimated biomass (tonnes/ha).';
COMMENT ON COLUMN scan_results.biomass_upper_90 IS 'Upper bound of the 90% prediction interval for estimated biomass (tonnes/ha).';
COMMENT ON COLUMN scan_results.biomass_uncertainty_pct IS 'Uncertainty percentage relative to estimated biomass: (upper - lower) / mean * 100.';
COMMENT ON COLUMN scan_results.model_type IS 'The machine learning algorithm used (e.g. Random Forest, XGBoost).';
COMMENT ON COLUMN scan_results.model_r2 IS 'The cross-validation R-squared score of the model.';
COMMENT ON COLUMN scan_results.sensors_used IS 'JSON tracking which sensors (Sentinel-2, Sentinel-1 SAR, GEDI) contributed to the scan.';
