"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { PlotWithMonitoring } from "@/lib/types";

const ALERT_STYLES: Record<string, { bg: string; text: string; dot: string; border: string; label: string }> = {
  critical: { bg: "bg-red-50",     text: "text-red-700",     dot: "bg-red-500",     border: "border-red-200",     label: "Critical" },
  warning:  { bg: "bg-amber-50",   text: "text-amber-700",   dot: "bg-amber-500",   border: "border-amber-200",   label: "Warning" },
  positive: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", border: "border-emerald-200", label: "Improving" },
  info:     { bg: "bg-terra-50",   text: "text-terra-700",   dot: "bg-terra-500",   border: "border-terra-200",   label: "Stable" },
};

function StatusBadge({ level }: { level: string }) {
  const s = ALERT_STYLES[level] ?? ALERT_STYLES.info;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${s.bg} ${s.border} ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function PlotCard({
  plot,
  onDelete,
}: {
  plot: PlotWithMonitoring;
  onDelete: (id: string) => Promise<void>;
}) {
  const mon = plot.latest_monitoring;
  const scan = plot.latest_scan;
  const alertLevel = mon?.alert_level ?? "info";
  const s = ALERT_STYLES[alertLevel];

  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting]     = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await onDelete(plot.id);
    } catch (err: any) {
      const msg = err.message || "";
      setDeleteError(
        msg.includes("listed or sold")
          ? "This plot has listed or sold credits and cannot be deleted. Retire the credits first."
          : msg || "Failed to delete plot"
      );
    } finally {
      setDeleting(false);
    }
  };

  const biomass = scan?.estimated_biomass ?? plot.baseline_agbd;
  const scanDate = scan?.created_at
    ? new Date(scan.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
    : null;

  const cardBorder =
    alertLevel === "critical" ? "border-red-300" :
    alertLevel === "warning"  ? "border-amber-300" :
    "border-[var(--color-border)]";

  return (
    <div className={`bg-white rounded-2xl border-2 ${cardBorder} shadow-sm hover:shadow-md transition-all flex flex-col`}>
      {/* Top strip */}
      <div className={`rounded-t-2xl border-b px-5 py-3 flex items-center justify-between ${
        alertLevel === "critical" ? "bg-red-50 border-red-200" :
        alertLevel === "warning"  ? "bg-amber-50 border-amber-200" :
        "bg-[var(--color-surface-subtle)] border-[var(--color-border)]"
      }`}>
        <div>
          <h3 className="font-bold text-primary leading-tight">{plot.name}</h3>
          <p className="text-xs text-muted mt-0.5">{plot.region ?? "Rwanda"} · {plot.land_use} · {plot.area_hectares.toFixed(0)} ha</p>
        </div>
        {mon ? <StatusBadge level={alertLevel} /> : (
          <span className="text-xs text-muted bg-white border border-[var(--color-border)] px-2.5 py-0.5 rounded-full">No data yet</span>
        )}
      </div>

      <div className="p-5 flex-1 flex flex-col">
        {/* Key metrics */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="text-center bg-[var(--color-surface-subtle)] rounded-xl p-3">
            <div className="text-xl font-bold text-terra-700">
              {mon ? mon.current_ndvi.toFixed(3) : scan ? scan.mean_ndvi.toFixed(3) : "—"}
            </div>
            <div className="text-xs text-muted mt-0.5">NDVI</div>
          </div>
          <div className="text-center bg-[var(--color-surface-subtle)] rounded-xl p-3">
            <div className={`text-xl font-bold ${
              mon
                ? mon.delta_ndvi < 0 ? "text-red-600" : "text-emerald-600"
                : "text-primary"
            }`}>
              {mon ? `${mon.delta_ndvi >= 0 ? "+" : ""}${mon.delta_ndvi.toFixed(3)}` : "—"}
            </div>
            <div className="text-xs text-muted mt-0.5">Δ NDVI</div>
          </div>
          <div className="text-center bg-[var(--color-surface-subtle)] rounded-xl p-3">
            <div className="text-xl font-bold text-primary">
              {biomass != null ? `${biomass.toFixed(0)}` : "—"}
            </div>
            <div className="text-xs text-muted mt-0.5">t/ha</div>
          </div>
        </div>

        {/* Carbon stock row */}
        {scan && (
          <div className="flex items-center justify-between text-sm mb-3 px-1">
            <span className="text-muted">Carbon stock</span>
            <span className="font-bold text-primary">{scan.estimated_tco2e.toFixed(1)} tCO₂e</span>
          </div>
        )}

        {/* Baseline badge */}
        {plot.baseline_agbd != null && (
          <div className="flex items-center justify-between text-sm mb-3 px-1">
            <span className="text-muted flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-terra-500" />
              GEDI baseline
            </span>
            <span className="font-semibold text-terra-700">{plot.baseline_agbd.toFixed(1)} t/ha</span>
          </div>
        )}

        {/* Last scan date */}
        {scanDate && (
          <div className="flex items-center justify-between text-sm mb-3 px-1">
            <span className="text-muted">Last scan</span>
            <span className="text-secondary font-medium">{scanDate}</span>
          </div>
        )}

        {/* Latest monitoring finding */}
        {mon && (
          <div className={`rounded-xl border px-3 py-2.5 mb-4 ${s.bg} ${s.border} ${s.text}`}>
            <p className="text-xs font-semibold uppercase tracking-wide mb-0.5">Latest finding</p>
            <p className="text-sm font-medium leading-snug">{mon.cause}</p>
          </div>
        )}

        <div className="flex-1" />

        {/* Delete confirmation */}
        {confirming ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 mt-2">
            <p className="text-sm font-bold text-red-800 mb-1">Delete "{plot.name}"?</p>
            <p className="text-xs text-red-600 mb-3">
              All scans, monitoring reports and pending credits will be removed permanently.
              Plots with active (listed/sold) credits cannot be deleted.
            </p>
            {deleteError && (
              <p className="text-xs text-red-700 font-medium bg-red-100 rounded-lg px-2 py-1.5 mb-2">{deleteError}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 py-2 rounded-lg bg-red-600 text-white text-xs font-semibold hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {deleting ? "Deleting…" : "Yes, delete"}
              </button>
              <button
                onClick={() => { setConfirming(false); setDeleteError(null); }}
                disabled={deleting}
                className="flex-1 py-2 rounded-lg border border-red-300 text-red-700 text-xs font-semibold hover:bg-red-100 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-2 space-y-2">
            <div className="flex gap-2">
              <Link
                href={`/landowner/monitoring/${plot.id}`}
                className="flex-1 text-center py-2.5 rounded-xl bg-terra-700 text-white text-sm font-semibold hover:bg-terra-800 transition-colors"
              >
                View monitoring
              </Link>
              <Link
                href={`/landowner/pending-scans?plot_id=${plot.id}`}
                className="px-4 py-2.5 rounded-xl border border-[var(--color-border)] text-secondary text-sm font-medium hover:bg-terra-50 transition-colors"
              >
                Credits
              </Link>
            </div>
            <button
              onClick={() => setConfirming(true)}
              className="w-full py-2 rounded-xl border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 hover:border-red-300 transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete plot
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function LandownerDashboard() {
  const router = useRouter();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [plots, setPlots] = useState<PlotWithMonitoring[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [pendingCredits, setPendingCredits] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading) {
      if (!isAuthenticated || !user) { router.push("/login"); return; }
      loadData();
    }
  }, [authLoading, isAuthenticated, user]);

  const loadData = async () => {
    if (!user?.id) return;
    try {
      const [plotsData, notifRes, pendingRes] = await Promise.allSettled([
        api.getPlotsByOwner(user.id),
        fetch(`/api/notifications?user_id=${user.id}`),
        api.getPendingScans(user.id),
      ]);
      if (plotsData.status === "fulfilled") setPlots(plotsData.value as PlotWithMonitoring[]);
      if (notifRes.status === "fulfilled" && (notifRes.value as Response).ok) {
        const d = await (notifRes.value as Response).json();
        setNotifications(d.notifications || []);
      }
      if (pendingRes.status === "fulfilled") {
        const d = pendingRes.value as any;
        setPendingCredits((d.pending_scans || []).length);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePlot = async (plotId: string) => {
    if (!user?.id) return;
    await api.deletePlot(plotId, user.id);
    setPlots(prev => prev.filter(p => p.id !== plotId));
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface-subtle)]">
        <div className="flex items-center gap-3 text-muted">
          <div className="w-5 h-5 border-2 border-terra-600 border-t-transparent rounded-full animate-spin" />
          Loading dashboard…
        </div>
      </div>
    );
  }

  const critical = plots.filter(p => p.latest_monitoring?.alert_level === "critical").length;
  const warnings  = plots.filter(p => p.latest_monitoring?.alert_level === "warning").length;

  return (
    <div className="min-h-screen bg-[var(--color-surface-subtle)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-primary">
            Welcome back, {user?.full_name?.split(" ")[0]}
          </h1>
          <p className="text-muted mt-1">Satellite monitoring and carbon credit management for your plots</p>
        </div>

        {/* Summary strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Registered plots",    value: plots.length,    color: "text-terra-700" },
            { label: "Critical alerts",     value: critical,        color: "text-red-600"   },
            { label: "Warnings",            value: warnings,        color: "text-amber-600" },
            { label: "Pending scan reviews", value: pendingCredits, color: "text-blue-600"  },
          ].map(item => (
            <div key={item.label} className="bg-white rounded-2xl border border-[var(--color-border)] p-5 shadow-sm">
              <div className={`text-3xl font-bold ${item.color}`}>{item.value}</div>
              <div className="text-sm text-muted mt-1">{item.label}</div>
            </div>
          ))}
        </div>

        {/* Critical alert banner */}
        {critical > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-red-800">
                {critical} plot{critical > 1 ? "s require" : " requires"} immediate attention
              </p>
              <p className="text-xs text-red-600">Field verification may be required. Check monitoring reports below.</p>
            </div>
          </div>
        )}

        {/* Pending scan reviews banner */}
        {pendingCredits > 0 && (
          <Link
            href="/landowner/pending-scans"
            className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6 hover:bg-amber-100 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                <span className="text-base">📋</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-amber-800">
                  {pendingCredits} scan result{pendingCredits !== 1 ? "s" : ""} awaiting your review
                </p>
                <p className="text-xs text-amber-600">Approve to list credits on the registry</p>
              </div>
            </div>
            <svg className="w-5 h-5 text-amber-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        )}

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Plots grid */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-primary">My plots</h2>
              <Link
                href="/request-registration"
                className="text-sm font-semibold text-terra-600 hover:text-terra-700 flex items-center gap-1"
              >
                + Register new plot
              </Link>
            </div>

            {plots.length === 0 ? (
              <div className="bg-white rounded-2xl border border-[var(--color-border)] p-12 text-center shadow-sm">
                <div className="text-5xl mb-4">🌳</div>
                <h3 className="text-lg font-semibold text-primary mb-2">No plots registered yet</h3>
                <p className="text-muted mb-6 text-sm">Register your land to start satellite monitoring and earn carbon credits.</p>
                <Link
                  href="/request-registration"
                  className="inline-block bg-terra-700 text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-terra-800 transition-colors"
                >
                  Register your first plot
                </Link>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-4">
                {plots.map(plot => (
                  <PlotCard key={plot.id} plot={plot} onDelete={handleDeletePlot} />
                ))}
              </div>
            )}
          </div>

          {/* Right sidebar */}
          <div className="space-y-4">
            {/* Quick actions */}
            <div className="bg-white rounded-2xl border border-[var(--color-border)] p-5 shadow-sm">
              <h3 className="font-bold text-primary mb-4">Quick actions</h3>
              <div className="space-y-1">
                {[
                  { href: "/landowner/pending-scans", icon: "📋", label: "Review pending scans" },
                  { href: "/request-registration",   icon: "🗺️", label: "Register new land" },
                  { href: "/marketplace",            icon: "💱", label: "View marketplace" },
                  { href: "/registry",               icon: "📒", label: "Public registry" },
                ].map(a => (
                  <Link key={a.href} href={a.href}
                    className="flex items-center gap-3 p-3 rounded-xl hover:bg-terra-50 transition-colors"
                  >
                    <span className="text-lg">{a.icon}</span>
                    <span className="text-sm font-medium text-secondary">{a.label}</span>
                    <svg className="w-4 h-4 text-muted ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </Link>
                ))}
              </div>
            </div>

            {/* Recent notifications */}
            {notifications.length > 0 && (
              <div className="bg-white rounded-2xl border border-[var(--color-border)] p-5 shadow-sm">
                <h3 className="font-bold text-primary mb-4">Recent notifications</h3>
                <div className="space-y-3">
                  {notifications.slice(0, 4).map(n => (
                    <div key={n.id} className={`rounded-xl p-3 ${!n.read ? "bg-amber-50 border border-amber-200" : "bg-[var(--color-surface-subtle)]"}`}>
                      <p className={`text-sm font-semibold ${!n.read ? "text-amber-900" : "text-primary"}`}>{n.title}</p>
                      <p className="text-xs text-muted mt-0.5 line-clamp-2">{n.message}</p>
                      <p className="text-xs text-muted mt-1">
                        {new Date(n.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
