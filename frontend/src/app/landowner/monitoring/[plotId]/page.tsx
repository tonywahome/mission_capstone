"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { MonitoringReport, PlotWithMonitoring } from "@/lib/types";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ReferenceArea, ResponsiveContainer, Legend,
} from "recharts";
import VegetationMap from "@/components/VegetationMap";

// ── Constants ─────────────────────────────────────────────────────────────────

const ALERT = {
  critical: {
    bg: "bg-red-50", border: "border-red-300", text: "text-red-700",
    badge: "bg-red-100 text-red-800 border-red-200",
    pill: "bg-red-600 text-white",
    icon: "⚠", label: "Critical alert", ring: "#ef4444",
  },
  warning: {
    bg: "bg-amber-50", border: "border-amber-300", text: "text-amber-700",
    badge: "bg-amber-100 text-amber-800 border-amber-200",
    pill: "bg-amber-500 text-white",
    icon: "⚡", label: "Warning", ring: "#f59e0b",
  },
  positive: {
    bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-700",
    badge: "bg-emerald-100 text-emerald-800 border-emerald-200",
    pill: "bg-emerald-600 text-white",
    icon: "↑", label: "Improving", ring: "#16a34a",
  },
  info: {
    bg: "bg-terra-50", border: "border-terra-200", text: "text-terra-700",
    badge: "bg-terra-100 text-terra-700 border-terra-200",
    pill: "bg-terra-700 text-white",
    icon: "✓", label: "Stable", ring: "#15803d",
  },
} as const;

type AlertLevel = keyof typeof ALERT;

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
function fmtShort(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

// ── Visual components ─────────────────────────────────────────────────────────

function NDVIGauge({ value, size = 148 }: { value: number; size?: number }) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  const color =
    value >= 0.65 ? "#16a34a" :
    value >= 0.45 ? "#d97706" : "#dc2626";
  const label =
    value >= 0.65 ? "Dense canopy" :
    value >= 0.45 ? "Moderate cover" : "Sparse cover";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        {/* Outer glow ring */}
        <div className="absolute inset-0 rounded-full opacity-10" style={{ boxShadow: `0 0 0 8px ${color}` }} />
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#f3f4f6" strokeWidth="3" />
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="1.5"
            strokeDasharray="25 75" strokeDashoffset="0" />
          <circle
            cx="18" cy="18" r="15.9" fill="none"
            stroke={color} strokeWidth="3.2"
            strokeDasharray={`${pct} ${100 - pct}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.6s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-bold leading-none" style={{ color, fontSize: size * 0.22 }}>
            {value.toFixed(3)}
          </span>
          <span className="text-muted mt-0.5" style={{ fontSize: size * 0.085 }}>NDVI</span>
        </div>
      </div>
      <span className="text-xs font-semibold" style={{ color }}>{label}</span>
    </div>
  );
}

function SpectralBar({
  label, value, min = -1, max = 1, low = -0.1, high = 0.3, unit = "",
}: {
  label: string; value: number | null | undefined;
  min?: number; max?: number; low?: number; high?: number; unit?: string;
}) {
  if (value == null) {
    return (
      <div className="flex items-center justify-between py-2">
        <span className="text-sm text-muted">{label}</span>
        <span className="text-sm text-muted">—</span>
      </div>
    );
  }
  const pct = ((value - min) / (max - min)) * 100;
  const color = value < low ? "#ef4444" : value > high ? "#16a34a" : "#d97706";
  return (
    <div className="py-2">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm text-muted">{label}</span>
        <span className="text-sm font-bold" style={{ color }}>
          {value.toFixed(3)}{unit}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden relative">
        <div className="absolute inset-0 flex">
          <div className="h-full bg-red-100" style={{ width: `${((low - min) / (max - min)) * 100}%` }} />
          <div className="h-full bg-amber-50" style={{ width: `${((high - low) / (max - min)) * 100}%` }} />
          <div className="h-full bg-emerald-50 flex-1" />
        </div>
        <div
          className="absolute top-0 h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(Math.max(pct, 2), 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function StatCard({
  label, value, sub, accent = false,
}: {
  label: string; value: React.ReactNode; sub?: string; accent?: boolean;
}) {
  return (
    <div className={`rounded-2xl border p-5 ${accent
      ? "bg-terra-700 border-terra-600 text-white"
      : "bg-white border-[var(--color-border)] shadow-sm"}`}>
      <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${accent ? "text-terra-200" : "text-muted"}`}>
        {label}
      </p>
      <div className={`text-2xl font-bold leading-none ${accent ? "text-white" : "text-primary"}`}>{value}</div>
      {sub && <p className={`text-xs mt-1.5 ${accent ? "text-terra-200" : "text-muted"}`}>{sub}</p>}
    </div>
  );
}

function DataQualityBadge({ quality, n }: { quality: string; n: number }) {
  const cfg =
    quality === "historical"       ? { color: "text-emerald-700 bg-emerald-50 border-emerald-200", label: `${n} historical observations` } :
    quality === "limited_history"  ? { color: "text-amber-700 bg-amber-50 border-amber-200",   label: `${n} baseline scan — limited history` } :
    quality === "single_baseline"  ? { color: "text-amber-700 bg-amber-50 border-amber-200",   label: "1 reference point — delta building" } :
                                     { color: "text-blue-700 bg-blue-50 border-blue-200",       label: "First check — baseline will form with more scans" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${cfg.color}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
      {cfg.label}
    </span>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const cfg = ALERT[d.alert_level as AlertLevel] ?? ALERT.info;
  return (
    <div className="bg-white border border-[var(--color-border)] rounded-xl shadow-xl p-3.5 text-sm min-w-[200px]">
      <p className="font-bold text-primary mb-2">{label}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-muted">NDVI</span>
          <span className="font-bold text-terra-700">{Number(d.current_ndvi).toFixed(3)}</span>
        </div>
        {d.evi != null && (
          <div className="flex justify-between gap-4">
            <span className="text-muted">EVI</span>
            <span className="font-semibold text-primary">{Number(d.evi).toFixed(3)}</span>
          </div>
        )}
        <div className="flex justify-between gap-4">
          <span className="text-muted">Baseline</span>
          <span className="text-secondary">{Number(d.baseline_ndvi).toFixed(3)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted">Δ NDVI</span>
          <span className={`font-bold ${d.delta_ndvi >= 0 ? "text-emerald-600" : "text-red-600"}`}>
            {d.delta_ndvi >= 0 ? "+" : ""}{Number(d.delta_ndvi).toFixed(3)}
          </span>
        </div>
      </div>
      <div className={`mt-2 pt-2 border-t border-gray-100 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border ${cfg.badge}`}>
        {cfg.icon} {cfg.label}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PlotMonitoringPage() {
  const { plotId } = useParams<{ plotId: string }>();
  const router = useRouter();
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [plot, setPlot]       = useState<PlotWithMonitoring | null>(null);
  const [latest, setLatest]   = useState<MonitoringReport | null>(null);
  const [history, setHistory] = useState<MonitoringReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError]     = useState("");
  const [chartView, setChartView] = useState<"ndvi" | "delta">("ndvi");

  const load = useCallback(async () => {
    if (!plotId) return;
    setLoading(true);
    setError("");
    try {
      const [plotData, histData] = await Promise.allSettled([
        api.getPlot(plotId),
        api.getMonitoringHistory(plotId, 52),
      ]);
      if (plotData.status === "fulfilled") setPlot(plotData.value as PlotWithMonitoring);
      if (histData.status === "fulfilled") {
        const h = histData.value as MonitoringReport[];
        setHistory(h);
        if (h.length > 0) setLatest(h[0]);
      }
    } catch (e: any) {
      setError(e.message ?? "Failed to load monitoring data");
    } finally {
      setLoading(false);
    }
  }, [plotId]);

  useEffect(() => {
    if (!authLoading) {
      if (!isAuthenticated) { router.push("/login"); return; }
      load();
    }
  }, [authLoading, isAuthenticated, load]);

  const runCheck = async () => {
    if (!plotId || running) return;
    setRunning(true);
    setError("");
    try {
      const report = await api.runMonitoringCheck(plotId) as MonitoringReport;
      setLatest(report);
      setHistory(prev => [report, ...prev]);
    } catch (e: any) {
      setError(e.message ?? "Monitoring check failed");
    } finally {
      setRunning(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface-subtle)]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-terra-600 border-t-transparent rounded-full animate-spin" style={{ borderWidth: 3 }} />
          <p className="text-muted text-sm">Loading monitoring data…</p>
        </div>
      </div>
    );
  }

  const cfg = ALERT[latest?.alert_level as AlertLevel ?? "info"];

  // Chart series — oldest first
  const chartData = [...history].reverse().map(r => ({
    date:         fmtShort(r.check_date),
    current_ndvi: r.current_ndvi,
    baseline_ndvi: r.baseline_ndvi,
    delta_ndvi:   r.delta_ndvi,
    evi:          r.spectral_context?.evi ?? null,
    alert_level:  r.alert_level,
  }));

  // Summary stats
  const ndviTrend = history.length >= 2
    ? history[0].current_ndvi - history[history.length - 1].current_ndvi
    : null;


  return (
    <div className="min-h-screen bg-[var(--color-surface-subtle)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* ── Breadcrumb ── */}
        <nav className="flex items-center gap-2 text-sm text-muted mb-5">
          <Link href="/landowner" className="hover:text-primary transition-colors">Dashboard</Link>
          <span className="opacity-40">/</span>
          <span className="text-primary font-medium">{plot?.name ?? "Plot monitoring"}</span>
        </nav>

        {/* ── Page header ── */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-primary leading-tight">{plot?.name ?? "Plot monitoring"}</h1>
            <p className="text-muted text-sm mt-1">
              {plot?.region ?? "Rwanda"} · {plot?.land_use} · {plot?.area_hectares?.toFixed(0)} ha
            </p>
            {latest && (
              <div className="flex items-center gap-3 mt-3">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold ${cfg.pill}`}>
                  {cfg.icon} {cfg.label}
                </span>
                <DataQualityBadge quality={latest.data_quality} n={latest.n_historical_scans} />
              </div>
            )}
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            {latest && (
              <span className="text-xs text-muted hidden sm:block">
                Last check: {fmtDate(latest.check_date)}
              </span>
            )}
            <button
              onClick={runCheck}
              disabled={running}
              className="flex items-center gap-2 px-5 py-2.5 bg-terra-700 text-white text-sm font-semibold rounded-xl hover:bg-terra-800 disabled:opacity-50 transition-colors shadow-sm"
            >
              {running ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Run check now
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 mb-6 flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            {error}
          </div>
        )}

        {/* ── No data state ── */}
        {!latest && !loading && (
          <div className="bg-white rounded-2xl border border-[var(--color-border)] p-20 text-center shadow-sm">
            <div className="w-16 h-16 bg-terra-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
              <svg className="w-8 h-8 text-terra-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-primary mb-2">No monitoring data yet</h2>
            <p className="text-muted text-sm max-w-sm mx-auto mb-6">
              Run the first satellite check to begin tracking vegetation health, NDVI trends, and carbon stock changes.
            </p>
            <button
              onClick={runCheck}
              disabled={running}
              className="bg-terra-700 text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-terra-800 disabled:opacity-50 transition-colors"
            >
              {running ? "Running…" : "Run first check"}
            </button>
          </div>
        )}

        {latest && (
          <div className="space-y-6">

            {/* ── Hero: 4-up key metrics ── */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">

              {/* NDVI Gauge */}
              <div className="bg-white rounded-2xl border border-[var(--color-border)] shadow-sm p-6 flex flex-col items-center justify-center">
                <NDVIGauge value={latest.current_ndvi} size={140} />
              </div>

              {/* Change panel */}
              <div className="bg-white rounded-2xl border border-[var(--color-border)] shadow-sm p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted mb-3">Change vs baseline</p>
                <div className={`text-3xl font-bold mb-3 flex items-center gap-1 ${latest.delta_ndvi >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                  {latest.delta_ndvi >= 0 ? "▲" : "▼"} {Math.abs(latest.delta_ndvi).toFixed(3)}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-muted">Baseline NDVI</span>
                    <span className="font-semibold text-primary">{latest.baseline_ndvi.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted">Z-score</span>
                    <span className={`font-semibold ${
                      latest.z_score < -1.5 ? "text-red-600" :
                      latest.z_score > 1.5  ? "text-emerald-600" : "text-primary"
                    }`}>
                      {latest.z_score > 0 ? "+" : ""}{latest.z_score.toFixed(2)}σ
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted">Observations</span>
                    <span className="font-semibold text-primary">{latest.n_historical_scans}</span>
                  </div>
                  {ndviTrend !== null && (
                    <div className="flex justify-between items-center pt-1 border-t border-[var(--color-border)]">
                      <span className="text-muted">Overall trend</span>
                      <span className={`font-semibold text-xs ${ndviTrend >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {ndviTrend >= 0 ? "▲" : "▼"} {Math.abs(ndviTrend).toFixed(3)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Status */}
              <div className={`rounded-2xl border-2 p-5 ${cfg.bg} ${cfg.border} flex flex-col`}>
                <p className={`text-xs font-semibold uppercase tracking-wider mb-3 ${cfg.text} opacity-70`}>Status</p>
                <div className="flex-1 flex flex-col justify-center">
                  <div className={`text-5xl font-bold mb-2 ${cfg.text}`}>{cfg.icon}</div>
                  <p className={`text-xl font-bold ${cfg.text}`}>{cfg.label}</p>
                  <p className={`text-xs mt-1 ${cfg.text} opacity-70`}>
                    {latest.classification.replace(/_/g, " ")}
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(0,0,0,0.08)" }}>
                  <p className={`text-xs font-medium ${cfg.text}`}>{latest.cause}</p>
                </div>
              </div>

              {/* Spectral indices */}
              <div className="bg-white rounded-2xl border border-[var(--color-border)] shadow-sm p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted mb-1">Spectral indices</p>
                <div className="divide-y divide-[var(--color-border)]">
                  <SpectralBar label="EVI"  value={latest.spectral_context?.evi}  min={-0.2} max={0.9} low={0.2} high={0.5} />
                  <SpectralBar label="NDMI" value={latest.spectral_context?.ndmi} min={-0.8} max={0.8} low={-0.2} high={0.2} />
                  <SpectralBar label="NBR"  value={latest.spectral_context?.nbr}  min={-0.5} max={0.9} low={-0.1} high={0.3} />
                </div>
              </div>
            </div>

            {/* ── NDVI trend chart ── */}
            {chartData.length >= 1 && (() => {
              // Y-axis domain: always include baseline and data range with padding
              const allNdvi = chartData.map(d => d.current_ndvi);
              const yMin = Math.max(0, Math.min(...allNdvi, latest.baseline_ndvi) - 0.12);
              const yMax = Math.min(1, Math.max(...allNdvi, latest.baseline_ndvi) + 0.12);
              const trendDir = ndviTrend !== null ? (ndviTrend > 0.005 ? "up" : ndviTrend < -0.005 ? "down" : "flat") : null;

              return (
              <div className="bg-white rounded-2xl border border-[var(--color-border)] shadow-sm overflow-hidden">
                {/* Chart header */}
                <div className="px-6 pt-5 pb-4 flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-[var(--color-border)]">
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <h2 className="font-bold text-primary">NDVI vegetation trend</h2>
                      {trendDir && (
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
                          trendDir === "up"   ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                          trendDir === "down" ? "bg-red-50 text-red-700 border border-red-200" :
                                               "bg-slate-50 text-slate-600 border border-slate-200"
                        }`}>
                          {trendDir === "up" ? "▲" : trendDir === "down" ? "▼" : "→"} {trendDir}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted">
                      Satellite observations vs historical baseline · thresholds: critical &lt;0.3 · warning 0.3–0.5 · healthy &gt;0.5
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="flex rounded-xl border border-[var(--color-border)] overflow-hidden text-xs font-semibold">
                      {(["ndvi", "delta"] as const).map(v => (
                        <button
                          key={v}
                          onClick={() => setChartView(v)}
                          className={`px-3.5 py-1.5 transition-colors ${chartView === v
                            ? "bg-terra-700 text-white"
                            : "text-muted hover:bg-terra-50"}`}
                        >
                          {v === "ndvi" ? "NDVI" : "Δ NDVI"}
                        </button>
                      ))}
                    </div>
                    <span className="text-xs text-muted bg-[var(--color-surface-subtle)] px-2.5 py-1 rounded-full border border-[var(--color-border)]">
                      {chartData.length} check{chartData.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>

                <div className="px-2 pt-4 pb-2">
                  <ResponsiveContainer width="100%" height={320}>
                    {chartView === "ndvi" ? (
                      <AreaChart data={chartData} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
                        <defs>
                          <linearGradient id="ndviGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%"  stopColor="#15803d" stopOpacity={0.22} />
                            <stop offset="100%" stopColor="#15803d" stopOpacity={0.02} />
                          </linearGradient>
                          <linearGradient id="eviGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%"  stopColor="#d97706" stopOpacity={0.14} />
                            <stop offset="100%" stopColor="#d97706" stopOpacity={0} />
                          </linearGradient>
                        </defs>

                        {/* Health zone bands — rendered first so they sit behind everything */}
                        <ReferenceArea y1={Math.max(yMin, 0)}    y2={Math.min(yMax, 0.3)}  fill="#fef2f2" fillOpacity={1} ifOverflow="hidden" />
                        <ReferenceArea y1={Math.max(yMin, 0.3)}  y2={Math.min(yMax, 0.5)}  fill="#fffbeb" fillOpacity={1} ifOverflow="hidden" />
                        <ReferenceArea y1={Math.max(yMin, 0.5)}  y2={Math.min(yMax, 1.0)}  fill="#f0fdf4" fillOpacity={1} ifOverflow="hidden" />

                        <CartesianGrid strokeDasharray="2 4" stroke="#e2e8f0" vertical={false} />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 11, fill: "#94a3b8", fontWeight: 500 }}
                          tickLine={false} axisLine={false}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          domain={[yMin, yMax]}
                          tick={{ fontSize: 11, fill: "#94a3b8" }}
                          tickLine={false} axisLine={false}
                          width={44}
                          tickFormatter={(v) => v.toFixed(2)}
                        />
                        <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#e2e8f0", strokeWidth: 1.5 }} />

                        {/* Baseline reference */}
                        <ReferenceLine
                          y={latest.baseline_ndvi}
                          stroke="#d97706" strokeDasharray="6 3" strokeWidth={1.5}
                          label={{ value: `Baseline ${latest.baseline_ndvi.toFixed(3)}`, fontSize: 10, fill: "#d97706", position: "insideTopRight", fontWeight: 600 }}
                        />

                        {/* Zone threshold lines */}
                        {yMin < 0.5 && yMax > 0.5 && (
                          <ReferenceLine y={0.5} stroke="#16a34a" strokeDasharray="2 4" strokeWidth={1} strokeOpacity={0.5} />
                        )}
                        {yMin < 0.3 && yMax > 0.3 && (
                          <ReferenceLine y={0.3} stroke="#dc2626" strokeDasharray="2 4" strokeWidth={1} strokeOpacity={0.5} />
                        )}

                        {chartData.some(d => d.evi != null) && (
                          <Area type="monotoneX" dataKey="evi" stroke="#d97706" strokeWidth={1.5}
                            fill="url(#eviGrad)" dot={false} strokeDasharray="4 2" />
                        )}
                        <Area
                          type="monotoneX" dataKey="current_ndvi"
                          stroke="#15803d" strokeWidth={3}
                          fill="url(#ndviGrad)"
                          dot={chartData.length <= 20
                            ? { r: 4, fill: "#15803d", stroke: "white", strokeWidth: 2 }
                            : false}
                          activeDot={{ r: 6, fill: "#15803d", stroke: "white", strokeWidth: 2.5 }}
                        />
                        {chartData.some(d => d.evi != null) && (
                          <Legend
                            wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
                            formatter={(v) => v === "current_ndvi" ? "NDVI" : "EVI"}
                            iconType="circle" iconSize={8}
                          />
                        )}
                      </AreaChart>
                    ) : (
                      <AreaChart data={chartData} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
                        <defs>
                          <linearGradient id="posGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%"  stopColor="#16a34a" stopOpacity={0.22} />
                            <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="negGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%"  stopColor="#dc2626" stopOpacity={0} />
                            <stop offset="100%" stopColor="#dc2626" stopOpacity={0.18} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="2 4" stroke="#e2e8f0" vertical={false} />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 11, fill: "#94a3b8", fontWeight: 500 }}
                          tickLine={false} axisLine={false}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          tick={{ fontSize: 11, fill: "#94a3b8" }}
                          tickLine={false} axisLine={false} width={44}
                          tickFormatter={(v) => (v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2))}
                        />
                        <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#e2e8f0", strokeWidth: 1.5 }} />
                        <ReferenceLine y={0} stroke="#cbd5e1" strokeWidth={1.5} label={{ value: "No change", fontSize: 10, fill: "#94a3b8", position: "insideTopLeft" }} />
                        <Area
                          type="monotoneX" dataKey="delta_ndvi"
                          stroke={latest.delta_ndvi >= 0 ? "#16a34a" : "#dc2626"}
                          strokeWidth={3}
                          fill={latest.delta_ndvi >= 0 ? "url(#posGrad)" : "url(#negGrad)"}
                          dot={chartData.length <= 20 ? { r: 4, fill: latest.delta_ndvi >= 0 ? "#16a34a" : "#dc2626", stroke: "white", strokeWidth: 2 } : false}
                          activeDot={{ r: 6, stroke: "white", strokeWidth: 2.5 }}
                        />
                      </AreaChart>
                    )}
                  </ResponsiveContainer>
                </div>

                {/* Zone legend strip */}
                <div className="px-6 pb-4 flex items-center gap-5 flex-wrap">
                  {[
                    { color: "bg-red-100",   border: "border-red-200",   dot: "bg-red-500",     label: "Critical  ( < 0.3 )" },
                    { color: "bg-amber-50",  border: "border-amber-200", dot: "bg-amber-500",   label: "Warning  ( 0.3 – 0.5 )" },
                    { color: "bg-emerald-50",border: "border-emerald-200",dot: "bg-emerald-600",label: "Healthy  ( > 0.5 )" },
                  ].map(z => (
                    <div key={z.label} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${z.color} ${z.border}`}>
                      <span className={`w-2 h-2 rounded-full ${z.dot}`} />
                      {z.label}
                    </div>
                  ))}
                  {ndviTrend !== null && (
                    <span className="ml-auto text-xs text-muted">
                      Overall trend: <span className={`font-semibold ${ndviTrend >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {ndviTrend >= 0 ? "▲" : "▼"} {Math.abs(ndviTrend).toFixed(3)}
                      </span> since first check
                    </span>
                  )}
                </div>
              </div>
              );
            })()}

            {/* ── Spatial vegetation map ── */}
            {plot?.geometry && (
              <VegetationMap plotId={plotId} geometry={plot.geometry as GeoJSON.Polygon} />
            )}

            {/* ── Alert card + Recommendation + Carbon panel ── */}
            <div className="grid lg:grid-cols-3 gap-4">

              {/* Alert */}
              <div className={`lg:col-span-1 rounded-2xl border-2 p-6 ${cfg.bg} ${cfg.border}`}>
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg font-bold border ${cfg.badge}`}>
                    {cfg.icon}
                  </div>
                  <div>
                    <span className={`text-xs font-bold uppercase tracking-wider ${cfg.text} opacity-70`}>{cfg.label}</span>
                    <h3 className={`text-sm font-bold ${cfg.text}`}>{latest.cause}</h3>
                  </div>
                </div>
                <p className={`text-sm leading-relaxed ${cfg.text}`}>{latest.explanation}</p>
              </div>

              {/* Recommendation */}
              <div className="lg:col-span-1 bg-white rounded-2xl border border-[var(--color-border)] shadow-sm p-6">
                <h3 className="font-bold text-primary mb-3 flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-terra-100 text-terra-700 text-xs flex items-center justify-center font-bold flex-shrink-0">!</span>
                  Recommended action
                </h3>
                <div className="space-y-2">
                  {latest.recommendation.split(". ").filter(Boolean).map((line, i) => (
                    <p key={i} className="text-sm text-secondary leading-relaxed flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-terra-400 mt-1.5 flex-shrink-0" />
                      {line.trim()}{line.endsWith(".") ? "" : "."}
                    </p>
                  ))}
                </div>
              </div>

              {/* Historical performance */}
              <div className="lg:col-span-1 bg-white rounded-2xl border border-[var(--color-border)] shadow-sm p-6">
                <h3 className="font-bold text-primary mb-4">Plot performance</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-muted">Total checks</span>
                    <span className="font-bold text-primary">{history.length}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-muted">Alerts fired</span>
                    <span className={`font-bold ${
                      history.filter(r => r.alert_level === "critical").length > 0 ? "text-red-600" : "text-primary"
                    }`}>
                      {history.filter(r => r.alert_level === "critical").length} critical,{" "}
                      {history.filter(r => r.alert_level === "warning").length} warning
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-muted">Best NDVI</span>
                    <span className="font-bold text-emerald-600">
                      {history.length > 0 ? Math.max(...history.map(r => r.current_ndvi)).toFixed(3) : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-muted">Avg NDVI</span>
                    <span className="font-bold text-primary">
                      {history.length > 0
                        ? (history.reduce((s, r) => s + r.current_ndvi, 0) / history.length).toFixed(3)
                        : "—"}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-[var(--color-border)]">
                    <p className="text-xs text-muted mb-2">Alert distribution</p>
                    <div className="flex gap-1 h-2 rounded-full overflow-hidden">
                      {(["critical", "warning", "positive", "info"] as const).map(level => {
                        const count = history.filter(r => r.alert_level === level).length;
                        const pct = history.length > 0 ? (count / history.length) * 100 : 0;
                        const colors = { critical: "bg-red-500", warning: "bg-amber-400", positive: "bg-emerald-500", info: "bg-terra-500" };
                        return pct > 0 ? <div key={level} className={`h-full ${colors[level]}`} style={{ width: `${pct}%` }} /> : null;
                      })}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Monitoring history table ── */}
            {history.length > 0 && (
              <div className="bg-white rounded-2xl border border-[var(--color-border)] shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-[var(--color-border)] flex items-center justify-between">
                  <div>
                    <h2 className="font-bold text-primary">Monitoring history</h2>
                    <p className="text-sm text-muted">All weekly satellite checks for this plot</p>
                  </div>
                  <span className="text-xs text-muted bg-[var(--color-surface-subtle)] px-2.5 py-1 rounded-full border border-[var(--color-border)]">
                    {history.length} record{history.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-[var(--color-surface-subtle)] border-b border-[var(--color-border)]">
                        {["Date", "NDVI", "Δ NDVI", "EVI", "Z-score", "Status", "Cause"].map(h => (
                          <th key={h} className={`px-5 py-3 text-xs font-semibold uppercase tracking-wide text-muted ${
                            h === "Date" || h === "Status" || h === "Cause" ? "text-left" : "text-right"
                          }`}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {history.map((r, i) => {
                        const rc = ALERT[r.alert_level as AlertLevel] ?? ALERT.info;
                        return (
                          <tr key={r.id} className={`hover:bg-[var(--color-surface-subtle)] transition-colors ${i === 0 ? "font-medium" : ""}`}>
                            <td className="px-5 py-3.5">
                              <span className="text-secondary">{fmtDate(r.check_date)}</span>
                              {i === 0 && <span className="ml-2 text-xs text-terra-600 font-semibold">latest</span>}
                            </td>
                            <td className="px-5 py-3.5 text-right font-semibold text-terra-700">{r.current_ndvi.toFixed(3)}</td>
                            <td className={`px-5 py-3.5 text-right font-semibold ${r.delta_ndvi >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                              {r.delta_ndvi >= 0 ? "+" : ""}{r.delta_ndvi.toFixed(3)}
                            </td>
                            <td className="px-5 py-3.5 text-right text-secondary">
                              {r.spectral_context?.evi != null ? Number(r.spectral_context.evi).toFixed(3) : "—"}
                            </td>
                            <td className={`px-5 py-3.5 text-right font-semibold ${r.z_score < -1.5 ? "text-red-600" : r.z_score > 1.5 ? "text-emerald-600" : "text-primary"}`}>
                              {r.z_score > 0 ? "+" : ""}{r.z_score.toFixed(2)}
                            </td>
                            <td className="px-5 py-3.5">
                              <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${rc.badge}`}>
                                {rc.icon} {rc.label}
                              </span>
                            </td>
                            <td className="px-5 py-3.5 text-muted max-w-xs">
                              <span className="line-clamp-1">{r.cause}</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}
