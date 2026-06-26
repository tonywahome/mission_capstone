-- Sample Data for TerraFoma (ALU Capstone re-scope)
-- Run this AFTER schema.sql, migration_add_auth.sql,
-- migration_approval_workflow.sql, AND migration_capstone_rescope.sql.
--
-- ILLUSTRATIVE DEMO DATA ONLY. These rows exist to populate the dashboard
-- (map view, audit-trail/verification queue) for demonstration purposes.
-- They are NOT field-collected plots and were NOT used to train or
-- validate the biomass model (see backend/ml/train_biomass_model.py).
-- The capstone's actual field-validation sample is Bugesera (savanna/
-- grassland) and Rulindo (agroforestry) districts, Rwanda — see the
-- revised research proposal Section 1.5/3.3.1. This file replaces an
-- earlier Kenya-based placeholder seed that predated the re-scope.

-- 1. Create a sample steward (field data submitter) user
-- Role widened to 'steward' by migration_capstone_rescope.sql; legacy rows
-- using 'landowner' remain valid under the same widened CHECK constraint.
INSERT INTO users (id, email, full_name, role, company_name, created_at)
VALUES
  ('550e8400-e29b-41d4-a716-446655440000', 'steward.pilot@terrafoma-capstone.local', 'Bugesera-Rulindo Field Stewardship Pilot', 'steward', 'ALU Capstone Field Team', now())
ON CONFLICT (id) DO NOTHING;

-- 2. Create sample land plots with coordinates
-- `region` holds the district name directly (Bugesera or Rulindo), matching
-- the keys in backend/services/mock_data.py's REGION_ELEVATION and the
-- demo features in backend/data/sample_plots.geojson. land_use values are
-- drawn from the two in-scope strata (grassland/savanna in Bugesera,
-- agroforestry in Rulindo), plus one wetland plot for variety — 'forest' is
-- intentionally avoided here since closed-canopy forest is not part of the
-- capstone's active validation sample.
INSERT INTO land_plots (id, owner_id, name, geometry, area_hectares, region, land_use, created_at)
VALUES
  -- Nyamata Grassland (Bugesera)
  ('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000',
   'Nyamata Grassland Reference Plot',
   '{"type":"Polygon","coordinates":[[[30.083,-2.207],[30.107,-2.207],[30.107,-2.187],[30.083,-2.187],[30.083,-2.207]]]}',
   42.3, 'Bugesera', 'grassland', now()),

  -- Ngenda Savanna (Bugesera)
  ('660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000',
   'Ngenda Savanna Block',
   '{"type":"Polygon","coordinates":[[[30.138,-2.114],[30.165,-2.114],[30.165,-2.090],[30.138,-2.090],[30.138,-2.114]]]}',
   35.6, 'Bugesera', 'grassland', now()),

  -- Base Agroforestry (Rulindo)
  ('660e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000',
   'Base Agroforestry Reference Plot',
   '{"type":"Polygon","coordinates":[[[29.978,-1.754],[29.997,-1.754],[29.997,-1.736],[29.978,-1.736],[29.978,-1.754]]]}',
   24.8, 'Rulindo', 'agroforestry', now()),

  -- Buyoga Agroforestry (Rulindo)
  ('660e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000',
   'Buyoga Agroforestry Block',
   '{"type":"Polygon","coordinates":[[[30.038,-1.710],[30.060,-1.710],[30.060,-1.690],[30.038,-1.690],[30.038,-1.710]]]}',
   31.5, 'Rulindo', 'agroforestry', now()),

  -- Gashora Wetland Transition (Bugesera)
  ('660e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000',
   'Gashora Wetland Transition Plot',
   '{"type":"Polygon","coordinates":[[[30.038,-2.312],[30.055,-2.312],[30.055,-2.296],[30.038,-2.296],[30.038,-2.312]]]}',
   17.2, 'Bugesera', 'wetland', now())
ON CONFLICT (id) DO NOTHING;

-- 3. Create sample scan results (satellite analysis)
-- Biomass/carbon figures are illustrative, scaled to plausible AGB ranges
-- for grassland/savanna and agroforestry (much lower than closed-canopy
-- forest, which the original Kenya seed used). model_version 'rf_v1'
-- matches the actual current artifact name, models/biomass_model_v1.pkl —
-- flagged as legacy/pending-retrain in README.md, not renamed here, since
-- it genuinely is the v1 artifact.
INSERT INTO scan_results (id, plot_id, scan_date, estimated_biomass, estimated_tco2e, carbon_density, integrity_score, model_version, created_at)
VALUES
  ('770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001',
   now(), 18.5, 1450.0, 34.28, 81.2, 'rf_v1', now()),

  ('770e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440002',
   now(), 14.2, 980.0, 27.53, 78.5, 'rf_v1', now()),

  ('770e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440003',
   now(), 52.6, 2870.0, 115.73, 88.3, 'rf_v1', now()),

  ('770e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440004',
   now(), 47.9, 3340.0, 106.03, 85.7, 'rf_v1', now()),

  ('770e8400-e29b-41d4-a716-446655440005', '660e8400-e29b-41d4-a716-446655440005',
   now(), 22.3, 890.0, 51.74, 74.1, 'rf_v1', now())
ON CONFLICT (id) DO NOTHING;

-- 4. Verification records
-- This capstone has no secondary market, credit issuance, or buyer
-- matching (see README "Out of Scope"); carbon_credits is retained as the
-- de facto Verification store (backend/routers/landowner.py), so these
-- rows demonstrate the verification-flow statuses added by
-- migration_capstone_rescope.sql rather than a marketplace listing.
-- price_per_tonne is retained for schema compatibility only — it is not
-- surfaced by any active capstone feature; see backend/legacy/ for the
-- separate TerraFoma LTD marketplace code that still uses it.
INSERT INTO carbon_credits (id, scan_id, plot_id, owner_id, vintage_year, quantity_tco2e, price_per_tonne, status, integrity_score, risk_score, created_at)
VALUES
  -- Nyamata Grassland — verified
  ('880e8400-e29b-41d4-a716-446655440001',
   '770e8400-e29b-41d4-a716-446655440001',
   '660e8400-e29b-41d4-a716-446655440001',
   '550e8400-e29b-41d4-a716-446655440000',
   2026, 1450.0, 0.00, 'verified', 81.2, 0.15, now()),

  -- Ngenda Savanna — awaiting verifier review
  ('880e8400-e29b-41d4-a716-446655440002',
   '770e8400-e29b-41d4-a716-446655440002',
   '660e8400-e29b-41d4-a716-446655440002',
   '550e8400-e29b-41d4-a716-446655440000',
   2026, 980.0, 0.00, 'pending_review', 78.5, 0.22, now()),

  -- Base Agroforestry — verified
  ('880e8400-e29b-41d4-a716-446655440003',
   '770e8400-e29b-41d4-a716-446655440003',
   '660e8400-e29b-41d4-a716-446655440003',
   '550e8400-e29b-41d4-a716-446655440000',
   2026, 2870.0, 0.00, 'verified', 88.3, 0.10, now()),

  -- Buyoga Agroforestry — flagged for review (illustrative data-quality concern)
  ('880e8400-e29b-41d4-a716-446655440004',
   '770e8400-e29b-41d4-a716-446655440004',
   '660e8400-e29b-41d4-a716-446655440004',
   '550e8400-e29b-41d4-a716-446655440000',
   2026, 3340.0, 0.00, 'flagged', 85.7, 0.30, now()),

  -- Gashora Wetland — awaiting verifier review
  ('880e8400-e29b-41d4-a716-446655440005',
   '770e8400-e29b-41d4-a716-446655440005',
   '660e8400-e29b-41d4-a716-446655440005',
   '550e8400-e29b-41d4-a716-446655440000',
   2026, 890.0, 0.00, 'pending_review', 74.1, 0.35, now())
ON CONFLICT (id) DO NOTHING;

-- Verify the data was inserted — breakdown by verification status rather
-- than a single hardcoded 'listed' filter, since the audit trail now spans
-- verified/pending_review/flagged rather than one marketplace state.
SELECT
  status,
  COUNT(*) as count,
  SUM(quantity_tco2e) as total_tco2e
FROM carbon_credits
GROUP BY status
ORDER BY status;
