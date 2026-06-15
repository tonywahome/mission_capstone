"use client";

import { useState, useEffect } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api } from "@/lib/api";
import type { FootprintResult } from "@/lib/types";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// Global emissions data from IEA (Real historical data 1990-2023)
// Source: IEA Greenhouse Gas Emissions from Energy
// Values converted from MtCO2 to GtCO2 (divided by 1000)
const globalEmissionsData = [
  { year: "1990", emissions: 20.54 },
  { year: "1991", emissions: 20.67 },
  { year: "1992", emissions: 20.61 },
  { year: "1993", emissions: 20.72 },
  { year: "1994", emissions: 20.83 },
  { year: "1995", emissions: 21.4 },
  { year: "1996", emissions: 21.85 },
  { year: "1997", emissions: 22.25 },
  { year: "1998", emissions: 22.43 },
  { year: "1999", emissions: 22.57 },
  { year: "2000", emissions: 23.24 },
  { year: "2001", emissions: 23.58 },
  { year: "2002", emissions: 23.93 },
  { year: "2003", emissions: 24.96 },
  { year: "2004", emissions: 26.13 },
  { year: "2005", emissions: 27.08 },
  { year: "2006", emissions: 27.95 },
  { year: "2007", emissions: 29.01 },
  { year: "2008", emissions: 29.23 },
  { year: "2009", emissions: 28.78 },
  { year: "2010", emissions: 30.55 },
  { year: "2011", emissions: 31.46 },
  { year: "2012", emissions: 31.79 },
  { year: "2013", emissions: 32.44 },
  { year: "2014", emissions: 32.5 },
  { year: "2015", emissions: 32.37 },
  { year: "2016", emissions: 32.44 },
  { year: "2017", emissions: 32.98 },
  { year: "2018", emissions: 33.69 },
  { year: "2019", emissions: 33.63 },
  { year: "2020", emissions: 31.88 },
  { year: "2021", emissions: 33.75 },
  { year: "2022", emissions: 34.19 },
  { year: "2023", emissions: 34.69 },
];

const sectorEmissions = [
  { name: "Energy", value: 73.2, color: "#ef4444" },
  { name: "Agriculture", value: 18.4, color: "#f59e0b" },
  { name: "Industrial", value: 5.2, color: "#3b82f6" },
  { name: "Waste", value: 3.2, color: "#8b5cf6" },
];

interface CreditStats {
  total_credits: number;
  total_verified: number;
  total_listed: number;
  total_sold: number;
  total_retired: number;
  total_tco2e: number;
  avg_price: number;
  avg_integrity: number;
}

export default function DashboardPage() {
  return (
    <ProtectedRoute allowedRoles={["business"]}>
      <DashboardPageContent />
    </ProtectedRoute>
  );
}

function DashboardPageContent() {
  // Scope 1 — Direct emissions
  const [fuelLitres, setFuelLitres] = useState(500);
  const [fuelType, setFuelType] = useState("diesel");
  const [naturalGas, setNaturalGas] = useState(0);
  const [refrigerant, setRefrigerant] = useState(0);

  // Scope 2 — Purchased electricity
  const [energyKwh, setEnergyKwh] = useState(5000);

  // Scope 3 — Value chain
  const [flightsShort, setFlightsShort] = useState(0);
  const [flightsLong, setFlightsLong] = useState(0);
  const [freight, setFreight] = useState(0);
  const [freightSea, setFreightSea] = useState(0);
  const [wasteLandfill, setWasteLandfill] = useState(0);
  const [wasteRecycled, setWasteRecycled] = useState(0);
  const [water, setWater] = useState(0);
  const [supplyChainSpend, setSupplyChainSpend] = useState(0);
  const [result, setResult] = useState<FootprintResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [stats, setStats] = useState<CreditStats | null>(null);
  const [credits, setCredits] = useState<any[]>([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      console.log("📊 Loading dashboard data...");
      console.log("API URL:", process.env.NEXT_PUBLIC_API_URL);
      setStatsLoading(true);

      const [statsData, creditsData] = await Promise.all([
        api.getCreditStats(),
        api.getCredits({ status: "listed" }),
      ]);

      console.log("✅ Stats data received:", statsData);
      console.log("✅ Credits data received:", creditsData);

      setStats(statsData as CreditStats);
      setCredits(creditsData as any[]);
      setStatsLoading(false);
    } catch (err) {
      console.error("❌ Failed to load dashboard data:", err);
      console.error("Error details:", err);
      setStatsLoading(false);
    }
  };

  const handleCalculate = async () => {
    setLoading(true);
    setCalcError(null);
    try {
      const data = (await api.calculateFootprint({
        energy_kwh_monthly: energyKwh,
        fuel_litres_monthly: fuelLitres,
        fuel_type: fuelType,
        natural_gas_m3_monthly: naturalGas,
        refrigerant_leaked_kg_annual: refrigerant,
        flights_short_km_annual: flightsShort,
        flights_long_km_annual: flightsLong,
        waste_landfill_kg_monthly: wasteLandfill,
        waste_recycled_kg_monthly: wasteRecycled,
        water_m3_monthly: water,
        freight_tonne_km_monthly: freight,
        freight_sea_tonne_km_monthly: freightSea,
        supply_chain_spend_usd_monthly: supplyChainSpend,
      })) as FootprintResult;
      setResult(data);
    } catch (err: any) {
      setCalcError(
        err?.message ||
          "Calculation failed. Please try again.",
      );
    }
    setLoading(false);
  };

  const creditsByStatus = stats
    ? [
        { name: "Verified", value: stats.total_verified, color: "#22c55e" },
        { name: "Listed", value: stats.total_listed, color: "#3b82f6" },
        { name: "Sold", value: stats.total_sold, color: "#f59e0b" },
        { name: "Retired", value: stats.total_retired, color: "#6366f1" },
      ]
    : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Carbon Intelligence Dashboard
          </h1>
          <p className="text-gray-600 text-lg">
            Real-time global emissions data and carbon credit marketplace
            insights
          </p>
        </div>

        {/* Global Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium opacity-90">
                Global Emissions 2023
              </h3>
              <span className="text-2xl">🌍</span>
            </div>
            <p className="text-3xl font-bold">
              {globalEmissionsData[globalEmissionsData.length - 1].emissions} Gt
            </p>
            <p className="text-xs opacity-80 mt-1">
              CO₂ from fuel combustion (IEA)
            </p>
            <div className="mt-3 flex items-center text-xs">
              <span className="bg-red-400 bg-opacity-30 px-2 py-1 rounded">
                +1.5% from 2022
              </span>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium opacity-90">
                Credits Available
              </h3>
              <span className="text-2xl">✓</span>
            </div>
            <p className="text-3xl font-bold">
              {statsLoading ? (
                <span className="animate-pulse">...</span>
              ) : stats ? (
                stats.total_listed
              ) : (
                "0"
              )}
            </p>
            <p className="text-xs opacity-80 mt-1">Listed carbon credits</p>
            <div className="mt-3 flex items-center text-xs">
              <span className="bg-green-400 bg-opacity-30 px-2 py-1 rounded">
                {statsLoading
                  ? "Loading..."
                  : stats
                    ? `${stats.total_tco2e.toFixed(0)} tCO₂e`
                    : "0 tCO₂e"}
              </span>
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium opacity-90">Avg Price</h3>
              <span className="text-2xl">💰</span>
            </div>
            <p className="text-3xl font-bold">
              {statsLoading ? (
                <span className="animate-pulse">...</span>
              ) : stats ? (
                `$${stats.avg_price.toFixed(2)}`
              ) : (
                "$0.00"
              )}
            </p>
            <p className="text-xs opacity-80 mt-1">per tonne CO₂e</p>
            <div className="mt-3 flex items-center text-xs">
              <span className="bg-blue-400 bg-opacity-30 px-2 py-1 rounded">
                Market rate
              </span>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium opacity-90">Avg Integrity</h3>
              <span className="text-2xl">🎯</span>
            </div>
            <p className="text-3xl font-bold">
              {statsLoading ? (
                <span className="animate-pulse">...</span>
              ) : stats ? (
                stats.avg_integrity.toFixed(0)
              ) : (
                "0"
              )}
            </p>
            <p className="text-xs opacity-80 mt-1">Quality score (0-100)</p>
            <div className="mt-3 flex items-center text-xs">
              <span className="bg-purple-400 bg-opacity-30 px-2 py-1 rounded">
                {statsLoading ? "Loading..." : "High quality"}
              </span>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Global Emissions Trend */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">📈</span>
              Global CO₂ Emissions Trend
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={globalEmissionsData}>
                <defs>
                  <linearGradient
                    id="colorEmissions"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "white",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="emissions"
                  stroke="#ef4444"
                  fillOpacity={1}
                  fill="url(#colorEmissions)"
                  name="Emissions (Gt CO₂)"
                />
              </AreaChart>
            </ResponsiveContainer>
            <p className="text-sm text-gray-500 mt-2 text-center">
              Historical data: IEA CO₂ emissions from fuel combustion
              (1990-2023)
            </p>
          </div>

          {/* Emissions by Sector */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">🏭</span>
              Emissions by Sector
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sectorEmissions}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {sectorEmissions.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {sectorEmissions.map((sector) => (
                <div key={sector.name} className="flex items-center text-sm">
                  <div
                    className="w-3 h-3 rounded mr-2"
                    style={{ backgroundColor: sector.color }}
                  />
                  <span className="text-gray-700">
                    {sector.name}: {sector.value}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Platform Statistics */}
        {stats && (
          <div className="bg-white rounded-xl border shadow-sm p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">📊</span>
              Platform Carbon Credits Overview
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={creditsByStatus}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "white",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="value" name="Credits" radius={[8, 8, 0, 0]}>
                    {creditsByStatus.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              <div className="flex flex-col justify-center space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                    <p className="text-sm text-green-600 font-medium">
                      Verified
                    </p>
                    <p className="text-2xl font-bold text-green-700">
                      {stats.total_verified}
                    </p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <p className="text-sm text-blue-600 font-medium">Listed</p>
                    <p className="text-2xl font-bold text-blue-700">
                      {stats.total_listed}
                    </p>
                  </div>
                  <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
                    <p className="text-sm text-amber-600 font-medium">Sold</p>
                    <p className="text-2xl font-bold text-amber-700">
                      {stats.total_sold}
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                    <p className="text-sm text-purple-600 font-medium">
                      Retired
                    </p>
                    <p className="text-2xl font-bold text-purple-700">
                      {stats.total_retired}
                    </p>
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border">
                  <p className="text-sm text-gray-600 mb-1">Total Volume</p>
                  <p className="text-3xl font-bold text-gray-900">
                    {stats.total_tco2e.toFixed(1)}
                    <span className="text-lg text-gray-500 ml-2">tCO₂e</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Calculator Section */}
        <div className="grid md:grid-cols-2 gap-8 mb-8">
          {/* Calculator */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-1 flex items-center">
              <span className="mr-2">🧮</span>
              Carbon Footprint Calculator
            </h2>
            <p className="text-xs text-gray-500 mb-5">
              Based on the GHG Protocol Corporate Standard
            </p>

            <div className="space-y-5">
              {/* ── Scope 1 ── */}
              <div className="rounded-xl border border-orange-200 bg-orange-50/40 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                    Scope 1
                  </span>
                  <span className="text-sm font-semibold text-orange-800">
                    Direct Emissions
                  </span>
                </div>
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Fuel consumed (litres/month)
                      </label>
                      <input
                        type="number"
                        min={0}
                        value={fuelLitres}
                        onChange={(e) => setFuelLitres(Number(e.target.value))}
                        onFocus={(e) => e.target.select()}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-orange-400 focus:border-orange-400"
                        placeholder="e.g., 500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Fuel type
                      </label>
                      <select
                        value={fuelType}
                        onChange={(e) => setFuelType(e.target.value)}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-orange-400 focus:border-orange-400"
                      >
                        <option value="diesel">Diesel</option>
                        <option value="petrol">Petrol/Gasoline</option>
                        <option value="lpg">LPG</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Natural gas — heating/process (m³/month)
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={naturalGas}
                      onChange={(e) => setNaturalGas(Number(e.target.value))}
                      onFocus={(e) => e.target.select()}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-orange-400 focus:border-orange-400"
                      placeholder="e.g., 200"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Refrigerant leaked — R-410A (kg/year)
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={refrigerant}
                      onChange={(e) => setRefrigerant(Number(e.target.value))}
                      onFocus={(e) => e.target.select()}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-orange-400 focus:border-orange-400"
                      placeholder="e.g., 2"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      GWP 2088 — check A/C service records
                    </p>
                  </div>
                </div>
              </div>

              {/* ── Scope 2 ── */}
              <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                    Scope 2
                  </span>
                  <span className="text-sm font-semibold text-blue-800">
                    Purchased Energy
                  </span>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Electricity consumed (kWh/month)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={energyKwh}
                    onChange={(e) => setEnergyKwh(Number(e.target.value))}
                    onFocus={(e) => e.target.select()}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
                    placeholder="e.g., 5000"
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    Factor: 0.027 kg CO₂e/kWh (Rwanda grid — MININFRA 2023, ~90% hydro)
                  </p>
                </div>
              </div>

              {/* ── Scope 3 ── */}
              <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="bg-purple-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                    Scope 3
                  </span>
                  <span className="text-sm font-semibold text-purple-800">
                    Value Chain
                  </span>
                </div>
                <div className="space-y-3">
                  {/* Flights */}
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Business Flights (km/year)
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Short-haul (&lt; 1 500 km)
                      </label>
                      <input
                        type="number"
                        min={0}
                        value={flightsShort}
                        onChange={(e) =>
                          setFlightsShort(Number(e.target.value))
                        }
                        onFocus={(e) => e.target.select()}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
                        placeholder="e.g., 5000"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Long-haul (&gt; 1 500 km)
                      </label>
                      <input
                        type="number"
                        min={0}
                        value={flightsLong}
                        onChange={(e) => setFlightsLong(Number(e.target.value))}
                        onFocus={(e) => e.target.select()}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
                        placeholder="e.g., 10000"
                      />
                    </div>
                  </div>

                  {/* Freight */}
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mt-1">
                    Freight (tonne-km/month)
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Road / truck
                      </label>
                      <input
                        type="number"
                        min={0}
                        value={freight}
                        onChange={(e) => setFreight(Number(e.target.value))}
                        onFocus={(e) => e.target.select()}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
                        placeholder="e.g., 1000"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Sea / container ship
                      </label>
                      <input
                        type="number"
                        min={0}
                        value={freightSea}
                        onChange={(e) => setFreightSea(Number(e.target.value))}
                        onFocus={(e) => e.target.select()}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
                        placeholder="e.g., 5000"
                      />
                    </div>
                  </div>

                  {/* Waste */}
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mt-1">
                    Waste generated (kg/month)
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Landfill
                      </label>
                      <input
                        type="number"
                        min={0}
                        value={wasteLandfill}
                        onChange={(e) =>
                          setWasteLandfill(Number(e.target.value))
                        }
                        onFocus={(e) => e.target.select()}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
                        placeholder="e.g., 500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Recycled
                      </label>
                      <input
                        type="number"
                        min={0}
                        value={wasteRecycled}
                        onChange={(e) =>
                          setWasteRecycled(Number(e.target.value))
                        }
                        onFocus={(e) => e.target.select()}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
                        placeholder="e.g., 200"
                      />
                    </div>
                  </div>

                  {/* Supply chain spend */}
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mt-1">
                    Supply Chain
                  </p>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Spend on goods &amp; services (USD/month)
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={supplyChainSpend}
                      onChange={(e) =>
                        setSupplyChainSpend(Number(e.target.value))
                      }
                      onFocus={(e) => e.target.select()}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-400 focus:border-purple-400"
                      placeholder="e.g., 10000"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      Spend-based: 0.308 kg CO₂e per USD (EPA USEEIO)
                    </p>
                  </div>
                </div>
              </div>

              <button
                onClick={handleCalculate}
                disabled={loading}
                className="w-full bg-gradient-to-r from-terra-600 to-terra-700 text-white py-3 rounded-lg font-semibold hover:from-terra-700 hover:to-terra-800 disabled:opacity-50 transition shadow-md"
              >
                {loading ? "Calculating..." : "Calculate Footprint"}
              </button>

              {calcError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                  {calcError}
                </div>
              )}
            </div>
          </div>

          {/* Results */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <span className="mr-2">📋</span>
              Your Carbon Footprint
            </h2>
            {result ? (
              <div className="space-y-5">
                {/* Total */}
                <div className="text-center bg-gradient-to-br from-terra-50 to-green-50 rounded-xl p-6 border-2 border-terra-200">
                  <p className="text-sm text-gray-600 mb-1">
                    Total Annual Emissions
                  </p>
                  <div className="text-5xl font-bold text-terra-600">
                    {result.annual_tco2e.toFixed(1)}
                  </div>
                  <div className="text-gray-600 mt-1 font-medium">
                    tCO₂e per year
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    ({result.monthly_tco2e.toFixed(2)} tCO₂e / month)
                  </div>
                </div>

                {/* Scope summary cards */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-center">
                    <div className="text-xs font-bold text-orange-600 mb-1">
                      Scope 1
                    </div>
                    <div className="text-xl font-bold text-orange-800">
                      {(result.scope1_tco2e ?? 0).toFixed(1)}
                    </div>
                    <div className="text-xs text-orange-500">tCO₂e</div>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                    <div className="text-xs font-bold text-blue-600 mb-1">
                      Scope 2
                    </div>
                    <div className="text-xl font-bold text-blue-800">
                      {(result.scope2_tco2e ?? 0).toFixed(1)}
                    </div>
                    <div className="text-xs text-blue-500">tCO₂e</div>
                  </div>
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-center">
                    <div className="text-xs font-bold text-purple-600 mb-1">
                      Scope 3
                    </div>
                    <div className="text-xl font-bold text-purple-800">
                      {(result.scope3_tco2e ?? 0).toFixed(1)}
                    </div>
                    <div className="text-xs text-purple-500">tCO₂e</div>
                  </div>
                </div>

                {/* Detailed source breakdown */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">
                    Source Breakdown
                  </h3>
                  <div className="space-y-1.5">
                    {[
                      {
                        label: "⚡ Electricity",
                        value: result.electricity_tco2e,
                        scope: 2,
                      },
                      {
                        label: "⛽ Fuel combustion",
                        value: result.fuel_tco2e,
                        scope: 1,
                      },
                      {
                        label: "🔥 Natural gas",
                        value: result.natural_gas_tco2e,
                        scope: 1,
                      },
                      {
                        label: "❄️ Refrigerants",
                        value: result.refrigerant_tco2e,
                        scope: 1,
                      },
                      {
                        label: "✈️ Business flights",
                        value: result.flights_tco2e,
                        scope: 3,
                      },
                      {
                        label: "🚚 Road freight",
                        value: result.freight_tco2e,
                        scope: 3,
                      },
                      {
                        label: "🚢 Sea freight",
                        value: result.freight_sea_tco2e,
                        scope: 3,
                      },
                      {
                        label: "🗑️ Waste",
                        value: result.waste_tco2e,
                        scope: 3,
                      },
                      {
                        label: "💧 Water",
                        value: result.water_tco2e,
                        scope: 3,
                      },
                      {
                        label: "🏭 Supply chain",
                        value: result.supply_chain_tco2e,
                        scope: 3,
                      },
                    ]
                      .filter((row) => row.value > 0)
                      .map((row) => {
                        const pct =
                          result.annual_tco2e > 0
                            ? (row.value / result.annual_tco2e) * 100
                            : 0;
                        const barColor =
                          row.scope === 1
                            ? "bg-orange-400"
                            : row.scope === 2
                              ? "bg-blue-400"
                              : "bg-purple-400";
                        return (
                          <div key={row.label}>
                            <div className="flex justify-between text-xs mb-0.5">
                              <span className="text-gray-700">{row.label}</span>
                              <span className="font-semibold text-gray-800">
                                {row.value.toFixed(2)} t &nbsp;
                                <span className="text-gray-400">
                                  ({pct.toFixed(0)}%)
                                </span>
                              </span>
                            </div>
                            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${barColor}`}
                                style={{ width: `${Math.min(pct, 100)}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                <a
                  href="/marketplace"
                  className="block w-full bg-gradient-to-r from-gray-800 to-gray-900 text-white py-3 rounded-lg font-semibold text-center hover:from-gray-900 hover:to-black transition shadow-md"
                >
                  Offset Your Emissions →
                </a>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-400">
                <div className="text-6xl mb-4">🌱</div>
                <p className="text-lg">Calculate your carbon footprint</p>
                <p className="text-sm mt-2">
                  Fill in the Scope 1, 2, and 3 fields and click Calculate
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Call to Action */}
        <div className="bg-gradient-to-r from-terra-600 to-green-600 rounded-xl p-8 text-white text-center shadow-lg">
          <h3 className="text-2xl font-bold mb-2">Ready to Make an Impact?</h3>
          <p className="mb-6 opacity-90">
            Browse our marketplace of verified carbon credits from A/R and
            conservation projects across Rwanda
          </p>
          <div className="flex gap-4 justify-center">
            <a
              href="/marketplace"
              className="bg-white text-terra-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-100 transition shadow-md"
            >
              View Marketplace
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
