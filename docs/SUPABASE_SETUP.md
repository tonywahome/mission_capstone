# Supabase Setup Guide for TerraFoma

This guide will help you set up Supabase so your TerraFoma application uses a real database with dynamic data instead of hardcoded sample values.

## Why Set Up Supabase?

**Current State (In-Memory Database):**
- ❌ Data is lost when server restarts
- ❌ Only 5 hardcoded sample credits
- ❌ No real user accounts or transactions
- ❌ Cannot add new credits or update data

**After Supabase Setup:**
- ✅ Persistent data storage (survives server restarts)
- ✅ Unlimited carbon credits
- ✅ Real user authentication
- ✅ Transaction history tracking
- ✅ Can scan plots and create new credits dynamically
- ✅ Professional production-ready database

---

## Step 1: Create a Supabase Account

1. Go to [https://supabase.com](https://supabase.com)
2. Click **"Start your project"** or **"Sign Up"**
3. Sign up with:
   - GitHub account (recommended), OR
   - Email and password
4. Verify your email if required

> **Cost:** Supabase has a generous **free tier** that's perfect for this project. You won't need to pay anything.

---

## Step 2: Create a New Project

1. After logging in, click **"New Project"**
2. Fill in the project details:
   - **Organization:** Select your organization (or create one)
   - **Project Name:** `terrafoma` (or any name you prefer)
   - **Database Password:** Choose a strong password (save this somewhere safe!)
   - **Region:** Choose the region closest to you (e.g., `us-east-1` for USA)
   - **Pricing Plan:** Select **"Free"**
3. Click **"Create new project"**
4. Wait 2-3 minutes while Supabase sets up your database

---

## Step 3: Get Your API Keys

Once your project is ready:

1. Click on **"Settings"** (gear icon) in the left sidebar
2. Click on **"API"** under Project Settings
3. You'll see several important values:

### Required Values:

**Project URL:**
```
https://xxxxxxxxxxxxx.supabase.co
```
Copy this - you'll need it for `SUPABASE_URL`

**API Keys - Find these two:**

1. **`anon` `public`** key (starts with `eyJ...`)
   - This is your **public** key
   - Copy this for `SUPABASE_ANON_KEY`

2. **`service_role` `secret`** key (starts with `eyJ...`)
   - This is your **admin** key
   - Copy this for `SUPABASE_SERVICE_ROLE_KEY`
   - ⚠️ **Keep this secret!** Never commit it to GitHub

---

## Step 4: Create Database Tables

Now we'll create the tables to store your carbon credits, users, transactions, etc.

### Option A: SQL Editor (Recommended)

1. In your Supabase dashboard, click **"SQL Editor"** in the left sidebar
2. Click **"New query"**
3. Copy the entire contents of `backend/data/schema.sql` from your project:

```bash
# From your project directory, copy the schema file
cat backend/data/schema.sql
```

4. Paste the SQL into the Supabase SQL Editor
5. Click **"Run"** (or press Cmd/Ctrl + Enter)
6. You should see: ✅ **"Success. No rows returned"**

### What This Creates:

The schema creates these tables:
- **users** - User accounts (landowners, buyers, admins)
- **land_plots** - Land plot information with coordinates
- **scan_results** - Satellite scan results with biomass data
- **carbon_credits** - Carbon credits with pricing and status
- **risk_assessments** - Risk scores for each plot
- **transactions** - Purchase history
- **audit_log** - Track all changes
- **industrial_profiles** - Company carbon footprint data

### Option B: Table Editor (Manual)

If you prefer a visual approach, you can create tables manually:

1. Click **"Table Editor"** in the left sidebar
2. Click **"Create a new table"**
3. Follow the schema in `backend/data/schema.sql` for each table

---

## Step 5: Configure Your Application

### Update `.env` File

1. In your project root, edit `.env` file:

```bash
cd /Users/cococe/Desktop/terrafoma
nano .env  # or use any text editor
```

2. Add/update these lines:

```env
# Supabase Configuration
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-service-role-key-here
```

**⚠️ Important:**
- Replace `xxxxxxxxxxxxx` with your actual project URL
- Replace the keys with your actual keys from Step 3
- Make sure there are **no spaces** around the `=` sign
- Make sure `.env` is in your `.gitignore` (it already is!)

### Verify `.env` File

Your complete `.env` file should look like this:

```env
# Google Earth Engine
EARTHENGINE_PROJECT_ID=venture-intern-africa
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json

# Supabase
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Mapbox (for frontend)
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1...
```

---

## Step 6: Restart Your Backend Server

1. Stop your current backend server (Ctrl+C in the terminal)
2. Restart it:

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8002
```

3. Look for this message:
   ```
   INFO:     Supabase client initialized
   ```

   Instead of:
   ```
   WARNING:  Supabase not configured, using in-memory database
   ```

---

## Step 7: Populate Initial Data (Optional)

### Option A: Use the Scan Endpoint

You can create real carbon credits by scanning plots:

1. Go to http://localhost:3001/dashboard
2. Click on a forested area in Kenya
3. Adjust the scan parameters
4. Click "Scan Plot"
5. The biomass data will be calculated and stored in Supabase!

### Option B: Insert Sample Data via SQL

If you want to start with sample data in Supabase:

1. Go to **SQL Editor** in Supabase
2. Run this SQL to insert sample credits:

```sql
-- Insert a sample user (landowner)
INSERT INTO users (id, email, full_name, role, company_name)
VALUES 
  ('550e8400-e29b-41d4-a716-446655440000', 'landowner@kenya.org', 'Kenya Forest Service', 'landowner', 'Kenya Forest Service');

-- Insert sample land plots
INSERT INTO land_plots (id, owner_id, name, geometry, area_hectares, region, land_use)
VALUES 
  ('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'Aberdare Forest Conservation', 
   '{"type":"Polygon","coordinates":[[[36.7,-0.5],[36.8,-0.5],[36.8,-0.6],[36.7,-0.6],[36.7,-0.5]]]}', 
   45.3, 'Nyeri County', 'forest'),
  ('660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'Mount Kenya Woodland',
   '{"type":"Polygon","coordinates":[[[37.3,-0.1],[37.4,-0.1],[37.4,-0.2],[37.3,-0.2],[37.3,-0.1]]]}',
   28.7, 'Meru County', 'forest');

-- Insert sample scan results
INSERT INTO scan_results (id, plot_id, estimated_biomass, estimated_tco2e, integrity_score, model_version)
VALUES 
  ('770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', 180.5, 12101.2, 92.4, 'rf_v1'),
  ('770e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440002', 125.3, 6198.1, 88.1, 'rf_v1');

-- Insert sample carbon credits
INSERT INTO carbon_credits (id, scan_id, plot_id, owner_id, vintage_year, quantity_tco2e, price_per_tonne, status, integrity_score, risk_score)
VALUES 
  ('880e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001',
   '550e8400-e29b-41d4-a716-446655440000', 2024, 12101.2, 29.30, 'listed', 92.4, 0.12),
  ('880e8400-e29b-41d4-a716-446655440002', '770e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440002',
   '550e8400-e29b-41d4-a716-446655440000', 2024, 6198.1, 23.25, 'listed', 88.1, 0.18);
```

3. Click **"Run"**

---

## Step 8: Verify Everything Works

### Test the API:

```bash
# Test that credits are loading from Supabase
curl http://localhost:8002/api/credits?status=listed | python3 -m json.tool
```

You should see credits returned from your Supabase database!

### Test the Frontend:

1. Go to http://localhost:3001/marketplace
2. You should see your carbon credits
3. If you inserted sample data, you'll see Aberdare Forest and Mount Kenya Woodland
4. If the list is empty, go scan some plots in the Dashboard!

### Check Supabase Dashboard:

1. In Supabase, click **"Table Editor"**
2. Select **"carbon_credits"** table
3. You should see your data!

---

## Troubleshooting

### Error: "Invalid API key"

**Problem:** Wrong API keys in `.env`

**Solution:**
1. Go back to Supabase → Settings → API
2. Copy the keys again (make sure you copy the entire key)
3. Update `.env` file
4. Restart backend server

### Error: "relation does not exist"

**Problem:** Database tables haven't been created

**Solution:**
1. Go to Supabase SQL Editor
2. Run the `backend/data/schema.sql` script again
3. Check for any error messages in the SQL output

### Still seeing "using in-memory database"

**Problem:** Backend can't connect to Supabase

**Solution:**
1. Check `.env` file exists in project root
2. Verify SUPABASE_URL starts with `https://`
3. Verify keys are complete (start with `eyJ`)
4. Check for typos or extra spaces
5. Restart backend server

### Empty marketplace

**Problem:** No credits in database yet

**Solution:**
- Either scan plots in Dashboard (recommended)
- Or insert sample data using SQL from Step 7

---

## Understanding the Data Flow

Once Supabase is set up:

```
1. User scans a plot in Dashboard
   ↓
2. Backend fetches satellite data from Google Earth Engine
   ↓
3. ML model predicts biomass
   ↓
4. Backend calculates:
   - Carbon (tCO2e)
   - Price per tonne (based on quality)
   - Community benefit (60%)
   ↓
5. Backend saves to Supabase:
   - land_plots table
   - scan_results table
   - carbon_credits table
   ↓
6. Marketplace loads from Supabase
   ↓
7. Credits appear on marketplace with REAL data!
```

---

## Database Schema Overview

### Main Tables:

**carbon_credits** - Your main table
```
- id (UUID)
- quantity_tco2e (carbon offset amount)
- price_per_tonne ($ per tonne)
- status (listed, sold, retired)
- integrity_score (0-100 quality score)
- risk_score (0-1 risk level)
- vintage_year (year credit was issued)
```

**land_plots**
```
- id (UUID)
- name (plot name)
- area_hectares (plot size)
- region (location)
- geometry (GeoJSON coordinates)
```

**scan_results**
```
- id (UUID)
- plot_id (links to land_plots)
- estimated_biomass (tonnes/ha)
- estimated_tco2e (total carbon)
- integrity_score (quality)
```

**transactions**
```
- id (UUID)
- credit_id (which credit was purchased)
- buyer_id, seller_id (users)
- quantity_tco2e (amount purchased)
- total_price (transaction value)
```

---

## Next Steps After Setup

Once Supabase is working:

1. **Create User Accounts**
   - Add authentication (Supabase Auth)
   - Allow landowners to register
   - Allow buyers to create accounts

2. **Enable Real Purchases**
   - Add payment integration (Stripe, etc.)
   - Update credit status on purchase
   - Generate certificates

3. **Add More Features**
   - Transaction history page
   - User dashboard
   - Credit retirement tracking
   - Email notifications

4. **Enable Row-Level Security**
   - Protect user data
   - Ensure users only see their own credits
   - Admin-only operations

---

## Supabase Free Tier Limits

Your free tier includes:

- ✅ **500 MB database storage** (plenty for this project)
- ✅ **2 GB bandwidth/month** (sufficient for demos)
- ✅ **50 MB file storage**
- ✅ **Unlimited API requests**
- ✅ **50,000 monthly active users**

This is more than enough for a hackathon project or small production app!

---

## Security Best Practices

### ✅ DO:
- Keep `.env` file in `.gitignore`
- Use environment variables for all secrets
- Use `anon` key for frontend
- Use `service_role` key only in backend
- Enable Row-Level Security in production

### ❌ DON'T:
- Commit API keys to GitHub
- Share your `service_role` key
- Hardcode credentials in source code
- Use admin keys in frontend

---

## Comparing In-Memory vs Supabase

| Feature | In-Memory | Supabase |
|---------|-----------|----------|
| **Persistence** | ❌ Lost on restart | ✅ Persistent |
| **Data Limit** | 5 sample credits | ∞ Unlimited |
| **Real Users** | ❌ No accounts | ✅ Full auth |
| **Transactions** | ❌ Simulated | ✅ Real tracking |
| **Scan & Save** | ❌ Temporary | ✅ Saved forever |
| **API Updates** | ❌ Not possible | ✅ Full CRUD |
| **Production Ready** | ❌ Demo only | ✅ Yes |
| **Cost** | Free | Free (up to limits) |

---

## Quick Reference

### Environment Variables:
```env
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
```

### Useful Supabase URLs:
- **Dashboard:** https://app.supabase.com
- **SQL Editor:** https://app.supabase.com/project/YOUR_PROJECT/sql
- **Table Editor:** https://app.supabase.com/project/YOUR_PROJECT/editor
- **API Docs:** https://app.supabase.com/project/YOUR_PROJECT/api

### Backend Check:
```bash
# See if Supabase is connected
grep "Supabase" backend/*.log

# Test API
curl http://localhost:8002/api/credits?status=listed
```

---

## Support

If you run into issues:

1. **Check Supabase Logs:**
   - Dashboard → Logs → API Logs
   - Look for error messages

2. **Check Backend Logs:**
   ```bash
   tail -f backend/backend.log
   ```

3. **Supabase Documentation:**
   - https://supabase.com/docs

4. **Community:**
   - Supabase Discord: https://discord.supabase.com
   - StackOverflow: tag `supabase`

---

## Summary

1. ✅ Create Supabase account (free)
2. ✅ Create new project
3. ✅ Copy URL and API keys
4. ✅ Run `schema.sql` in SQL Editor
5. ✅ Update `.env` file
6. ✅ Restart backend server
7. ✅ Scan plots or insert sample data
8. ✅ See real data in marketplace!

**Result:** Your TerraFoma app now uses a real database instead of hardcoded values. Every scan you do creates a real carbon credit that's stored permanently in Supabase! 🎉

---

**Need Help?** Refer to the troubleshooting section or check the Supabase logs for detailed error messages.
