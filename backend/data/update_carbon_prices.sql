-- Update Carbon Credit Prices to Reflect New Lower Pricing Structure
-- Run this in Supabase SQL Editor to update existing records
-- Date: March 7, 2026

-- New pricing structure:
-- Premium (90-100 integrity, <0.15 risk): $8/tonne
-- High Quality (75-89 integrity, 0.15-0.30 risk): $5/tonne  
-- Standard (60-74 integrity, 0.30-0.45 risk): $4/tonne
-- Basic (<60 integrity, >0.45 risk): $2/tonne

-- Update prices using CASE statement to replicate the pricing logic
UPDATE carbon_credits
SET 
  price_per_tonne = CASE
    -- Premium tier
    WHEN integrity_score >= 90 AND risk_score < 0.15 THEN 
      GREATEST(
        8.0 + ((integrity_score - 50) / 100.0 * 8.0) - (risk_score * 10.0),
        2.0
      )
    -- High Quality tier
    WHEN integrity_score >= 75 AND risk_score < 0.30 THEN 
      GREATEST(
        5.0 + ((integrity_score - 50) / 100.0 * 8.0) - (risk_score * 10.0),
        2.0
      )
    -- Standard tier
    WHEN integrity_score >= 60 AND risk_score < 0.45 THEN 
      GREATEST(
        4.0 + ((integrity_score - 50) / 100.0 * 8.0) - (risk_score * 10.0),
        2.0
      )
    -- Basic tier
    ELSE 
      GREATEST(
        2.0 + ((integrity_score - 50) / 100.0 * 8.0) - (risk_score * 10.0),
        2.0
      )
  END,
  updated_at = now()
WHERE price_per_tonne IS NOT NULL;

-- Display summary of changes
SELECT 
  status,
  COUNT(*) as credit_count,
  ROUND(AVG(price_per_tonne)::numeric, 2) as avg_price,
  ROUND(MIN(price_per_tonne)::numeric, 2) as min_price,
  ROUND(MAX(price_per_tonne)::numeric, 2) as max_price,
  ROUND(SUM(quantity_tco2e * price_per_tonne)::numeric, 2) as total_value
FROM carbon_credits
GROUP BY status
ORDER BY status;

-- Show individual credit updates
SELECT 
  id,
  quantity_tco2e,
  ROUND(price_per_tonne::numeric, 2) as price_per_tonne,
  ROUND((quantity_tco2e * price_per_tonne)::numeric, 2) as total_value,
  integrity_score,
  ROUND(risk_score::numeric, 3) as risk_score,
  status
FROM carbon_credits
ORDER BY created_at DESC
LIMIT 20;
