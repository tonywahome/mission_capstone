# Supabase Setup - Quick Reference Card

> **5-Minute Setup Guide** - Get your TerraFoma app using a real database instead of hardcoded sample data

---

## Why Supabase?

| In-Memory (Current) | Supabase |
|---------------------|----------|
| ❌ 5 hardcoded credits | ✅ Unlimited credits |
| ❌ Lost on restart | ✅ Persistent forever |
| ❌ Read-only | ✅ Full CRUD operations |
| ❌ Demo only | ✅ Production ready |

---

## Quick Setup (5 Steps)

### 1️⃣ Create Account (1 min)
- Go to [supabase.com](https://supabase.com)
- Sign up (free - no credit card)
- Create new project, name it `terrafoma`

### 2️⃣ Get API Keys (1 min)
```
Dashboard → Settings → API
```
Copy these 3 values:
- `Project URL`: https://xxxxx.supabase.co
- `anon public` key: eyJ...
- `service_role secret` key: eyJ...

### 3️⃣ Create Tables (2 min)
```
Dashboard → SQL Editor → New Query
```
Paste entire content of `backend/data/schema.sql` → Run

### 4️⃣ Update .env (30 sec)
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
```

### 5️⃣ Restart Backend (30 sec)
```bash
# Stop current server (Ctrl+C)
cd backend
uvicorn main:app --reload --port 8002
```

Look for: ✅ `Supabase client initialized`

---

## Verify It's Working

### Check API:
```bash
curl http://localhost:8002/api/credits?status=listed
```

### Check Frontend:
- Visit http://localhost:3001/dashboard
- Scan a plot (click on map)
- Check marketplace - new credit appears!

### Check Supabase:
- Dashboard → Table Editor → carbon_credits
- See your scanned plots! 🎉

---

## Insert Sample Data (Optional)

If you want starter data, run this in SQL Editor:

```sql
-- Create sample user
INSERT INTO users (id, email, full_name, role) VALUES 
('550e8400-e29b-41d4-a716-446655440000', 'demo@terrafoma.app', 'Demo User', 'landowner');

-- Create sample plot
INSERT INTO land_plots (id, owner_id, name, area_hectares, region, land_use) VALUES
('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 
 'Aberdare Forest', 45.3, 'Nyeri County', 'forest');

-- Create sample scan
INSERT INTO scan_results (id, plot_id, estimated_biomass, estimated_tco2e, integrity_score) VALUES
('770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', 
 180.5, 12101.2, 92.4);

-- Create sample credit
INSERT INTO carbon_credits (scan_id, plot_id, owner_id, vintage_year, quantity_tco2e, price_per_tonne, status, integrity_score, risk_score) VALUES
('770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001',
 '550e8400-e29b-41d4-a716-446655440000', 2024, 12101.2, 29.30, 'listed', 92.4, 0.12);
```

---

## Troubleshooting

### "Invalid API key"
- Copy keys again from Settings → API
- Make sure `.env` has no spaces around `=`
- Keys should start with `eyJ`

### "relation does not exist"
- Run `schema.sql` again in SQL Editor
- Check for error messages

### Still "using in-memory database"
- Check `.env` file is in project root
- Restart backend server
- Check backend logs: `tail -f backend/backend.log`

---

## File Locations

```
terrafoma/
├── .env                              # Add your keys here
├── backend/
│   ├── database.py                   # Auto-detects Supabase
│   └── data/
│       └── schema.sql                # Run this in Supabase
└── docs/
    └── SUPABASE_SETUP.md             # Full detailed guide
```

---

## Environment Variables Template

```env
# Google Earth Engine (keep existing)
EARTHENGINE_PROJECT_ID=venture-intern-africa
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Supabase (add these)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Mapbox (keep existing)
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1...
```

---

## What Gets Stored

When you scan a plot:
1. ✅ Plot coordinates → `land_plots` table
2. ✅ Satellite data → `scan_results` table
3. ✅ Biomass prediction → `scan_results.estimated_biomass`
4. ✅ Carbon credit → `carbon_credits` table
5. ✅ Price & quality → Calculated and stored
6. ✅ Appears in marketplace immediately!

---

## Key Tables

| Table | Purpose |
|-------|---------|
| `carbon_credits` | Your carbon credits with pricing |
| `land_plots` | Plot locations and details |
| `scan_results` | Satellite scan data |
| `users` | User accounts |
| `transactions` | Purchase history |

---

## Free Tier Limits

- 500 MB database ✅ (plenty)
- 2 GB bandwidth/month ✅
- Unlimited API requests ✅
- 50,000 monthly active users ✅

**You won't hit these limits!** 🎉

---

## Need Full Details?

📖 **Complete Guide:** [docs/SUPABASE_SETUP.md](SUPABASE_SETUP.md)

Includes:
- Screenshots
- Detailed explanations
- Security best practices
- Advanced features
- Production deployment tips

---

## Summary

```bash
# 1. Create account at supabase.com
# 2. Copy 3 values (URL + 2 keys)
# 3. Run schema.sql in SQL Editor
# 4. Add values to .env
# 5. Restart backend

# That's it! Now you have a real database! 🚀
```

**Time:** 5 minutes  
**Cost:** $0 (free tier)  
**Result:** Persistent, unlimited, production-ready database!

---

**Questions?** See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for detailed help!
