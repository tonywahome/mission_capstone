-- Sample Data for TerraFoma
-- Run this AFTER running schema.sql
-- This creates 5 sample carbon credits from Kenya conservation projects

-- 1. Create a sample landowner user
INSERT INTO users (id, email, full_name, role, company_name, created_at)
VALUES 
  ('550e8400-e29b-41d4-a716-446655440000', 'kfs@conservation.ke', 'Kenya Forest Service', 'landowner', 'Kenya Forest Service', now())
ON CONFLICT (id) DO NOTHING;

-- 2. Create sample land plots with coordinates
INSERT INTO land_plots (id, owner_id, name, geometry, area_hectares, region, land_use, created_at)
VALUES 
  -- Aberdare Forest Conservation
  ('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 
   'Aberdare Forest Conservation',
   '{"type":"Polygon","coordinates":[[[36.70,-0.50],[36.75,-0.50],[36.75,-0.55],[36.70,-0.55],[36.70,-0.50]]]}',
   45.3, 'Nyeri County', 'forest', now()),
   
  -- Mount Kenya Woodland
  ('660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000',
   'Mount Kenya Woodland',
   '{"type":"Polygon","coordinates":[[[37.30,-0.10],[37.35,-0.10],[37.35,-0.15],[37.30,-0.15],[37.30,-0.10]]]}',
   28.7, 'Meru County', 'forest', now()),
   
  -- Kakamega Rainforest
  ('660e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000',
   'Kakamega Rainforest Conservation',
   '{"type":"Polygon","coordinates":[[[34.85,0.25],[34.92,0.25],[34.92,0.18],[34.85,0.18],[34.85,0.25]]]}',
   67.2, 'Kakamega County', 'forest', now()),
   
  -- Mau Forest Complex
  ('660e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000',
   'Mau Forest Complex',
   '{"type":"Polygon","coordinates":[[[35.80,-0.45],[35.88,-0.45],[35.88,-0.52],[35.80,-0.52],[35.80,-0.45]]]}',
   52.1, 'Nakuru County', 'forest', now()),
   
  -- Loita Forest
  ('660e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000',
   'Loita Forest Conservation',
   '{"type":"Polygon","coordinates":[[[35.65,-1.35],[35.72,-1.35],[35.72,-1.42],[35.65,-1.42],[35.65,-1.35]]]}',
   38.9, 'Narok County', 'forest', now())
ON CONFLICT (id) DO NOTHING;

-- 3. Create sample scan results (satellite analysis)
INSERT INTO scan_results (id, plot_id, scan_date, estimated_biomass, estimated_tco2e, carbon_density, integrity_score, model_version, created_at)
VALUES 
  ('770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', 
   now(), 180.5, 12101.2, 267.1, 92.4, 'rf_v1', now()),
   
  ('770e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440002',
   now(), 125.3, 6198.1, 215.9, 88.1, 'rf_v1', now()),
   
  ('770e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440003',
   now(), 210.8, 24415.3, 363.3, 94.7, 'rf_v1', now()),
   
  ('770e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440004',
   now(), 95.4, 8566.2, 164.4, 76.3, 'rf_v1', now()),
   
  ('770e8400-e29b-41d4-a716-446655440005', '660e8400-e29b-41d4-a716-446655440005',
   now(), 142.7, 9567.8, 245.9, 85.2, 'rf_v1', now())
ON CONFLICT (id) DO NOTHING;

-- 4. Create carbon credits
INSERT INTO carbon_credits (id, scan_id, plot_id, owner_id, vintage_year, quantity_tco2e, price_per_tonne, status, integrity_score, risk_score, listed_at, created_at)
VALUES 
  -- Aberdare Forest (Premium tier)
  ('880e8400-e29b-41d4-a716-446655440001', 
   '770e8400-e29b-41d4-a716-446655440001', 
   '660e8400-e29b-41d4-a716-446655440001',
   '550e8400-e29b-41d4-a716-446655440000',
   2024, 12101.2, 29.30, 'listed', 92.4, 0.12, now(), now()),
   
  -- Mount Kenya (High tier)
  ('880e8400-e29b-41d4-a716-446655440002',
   '770e8400-e29b-41d4-a716-446655440002',
   '660e8400-e29b-41d4-a716-446655440002',
   '550e8400-e29b-41d4-a716-446655440000',
   2024, 6198.1, 23.25, 'listed', 88.1, 0.18, now(), now()),
   
  -- Kakamega (Premium tier)
  ('880e8400-e29b-41d4-a716-446655440003',
   '770e8400-e29b-41d4-a716-446655440003',
   '660e8400-e29b-41d4-a716-446655440003',
   '550e8400-e29b-41d4-a716-446655440000',
   2024, 24415.3, 37.78, 'listed', 94.7, 0.08, now(), now()),
   
  -- Mau Forest (Standard tier)
  ('880e8400-e29b-41d4-a716-446655440004',
   '770e8400-e29b-41d4-a716-446655440004',
   '660e8400-e29b-41d4-a716-446655440004',
   '550e8400-e29b-41d4-a716-446655440000',
   2024, 8566.2, 21.30, 'listed', 76.3, 0.28, now(), now()),
   
  -- Loita Forest (High tier)
  ('880e8400-e29b-41d4-a716-446655440005',
   '770e8400-e29b-41d4-a716-446655440005',
   '660e8400-e29b-41d4-a716-446655440005',
   '550e8400-e29b-41d4-a716-446655440000',
   2024, 9567.8, 22.62, 'listed', 85.2, 0.22, now(), now())
ON CONFLICT (id) DO NOTHING;

-- Verify the data was inserted
SELECT 
  'Credits loaded:' as status,
  COUNT(*) as count,
  SUM(quantity_tco2e) as total_tco2e,
  ROUND(SUM(quantity_tco2e * price_per_tonne), 2) as total_value_usd
FROM carbon_credits
WHERE status = 'listed';
