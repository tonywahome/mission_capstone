"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

interface PendingScan {
  credit_id: string;
  scan_id: string;
  plot_id: string;
  plot_name: string;
  scan_date: string;
  quantity_tco2e: number;
  price_per_tonne: number;
  total_value: number;
  integrity_score: number;
  risk_score: number;
  biomass: number;
  ndvi: number;
  evi: number;
  carbon_density: number;
  status: string;
}

const STATUS_STYLES: Record<string, { bg: string; border: string; text: string; dot: string; label: string }> = {
  pending_approval: { bg: "bg-amber-50",   border: "border-amber-200",   text: "text-amber-800",   dot: "bg-amber-500 animate-pulse", label: "Awaiting approval" },
  listed:           { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-800", dot: "bg-emerald-500",             label: "Listed on registry" },
  rejected:         { bg: "bg-red-50",     border: "border-red-200",     text: "text-red-800",     dot: "bg-red-500",                 label: "Rejected" },
  sold:             { bg: "bg-terra-50",   border: "border-terra-200",   text: "text-terra-800",   dot: "bg-terra-500",               label: "Sold" },
};

function IntegrityRing({ score }: { score: number }) {
  const pct = Math.round(score);
  const color =
    score >= 70 ? "#15803d" :
    score >= 50 ? "#d97706" :
    "#dc2626";
  const label =
    score >= 70 ? "High integrity" :
    score >= 50 ? "Medium integrity" :
    "Low integrity";
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="3.2" />
          <circle
            cx="18" cy="18" r="15.9" fill="none"
            stroke={color} strokeWidth="3.2"
            strokeDasharray={`${pct} ${100 - pct}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-bold" style={{ color }}>{pct}</span>
        </div>
      </div>
      <span className="text-xs font-semibold" style={{ color }}>{label}</span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[var(--color-surface-subtle)] rounded-xl p-3 text-center">
      <div className="text-xs text-muted mb-1">{label}</div>
      <div className="text-base font-bold text-primary">{value}</div>
    </div>
  );
}

function ScanCard({
  scan,
  plotMode,
  onApprove,
  onReject,
  processing,
}: {
  scan: PendingScan;
  plotMode: boolean;
  onApprove: (id: string) => void;
  onReject: (scan: PendingScan) => void;
  processing: boolean;
}) {
  const date = new Date(scan.scan_date).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
  });

  const st = STATUS_STYLES[scan.status] ?? STATUS_STYLES.pending_approval;
  const isPending = scan.status === "pending_approval";

  return (
    <div className={`bg-white rounded-2xl border-2 ${st.border} shadow-sm overflow-hidden`}>
      {/* Top bar */}
      <div className={`${st.bg} border-b ${st.border} px-5 py-3 flex items-center justify-between`}>
        <div>
          {!plotMode && <h2 className="font-bold text-primary">{scan.plot_name}</h2>}
          <p className={`text-xs text-muted ${!plotMode ? "mt-0.5" : ""}`}>Satellite scan · {date}</p>
        </div>
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${st.bg} ${st.text} border ${st.border}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
          {st.label}
        </span>
      </div>

      <div className="p-5">
        {/* Key numbers row */}
        <div className="flex items-center justify-between gap-4 mb-5">
          <div>
            <div className="text-4xl font-bold text-terra-700 leading-none">
              {scan.quantity_tco2e.toFixed(1)}
            </div>
            <div className="text-sm text-muted mt-0.5">tCO₂e carbon stock</div>
          </div>

          <IntegrityRing score={scan.integrity_score} />

          <div className="text-right">
            <div className="text-3xl font-bold text-primary leading-none">
              ${scan.total_value.toFixed(2)}
            </div>
            <div className="text-sm text-muted mt-0.5">
              at ${scan.price_per_tonne.toFixed(2)}/tonne
            </div>
          </div>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-5">
          <Metric label="NDVI" value={scan.ndvi.toFixed(3)} />
          <Metric label="EVI" value={scan.evi.toFixed(3)} />
          <Metric label="Biomass" value={`${scan.biomass.toFixed(1)} t/ha`} />
          <Metric label="Carbon density" value={`${scan.carbon_density.toFixed(2)} tCO₂e/ha`} />
        </div>

        {/* Risk bar */}
        <div className="mb-5">
          <div className="flex justify-between text-xs text-muted mb-1.5">
            <span>Permanence risk</span>
            <span className={`font-semibold ${
              scan.risk_score < 30 ? "text-emerald-600" :
              scan.risk_score < 60 ? "text-amber-600" : "text-red-600"
            }`}>{scan.risk_score.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                scan.risk_score < 30 ? "bg-emerald-500" :
                scan.risk_score < 60 ? "bg-amber-500" : "bg-red-500"
              }`}
              style={{ width: `${scan.risk_score}%` }}
            />
          </div>
        </div>

        {/* Actions — only for pending credits */}
        {isPending ? (
          <div className="flex gap-3">
            <button
              onClick={() => onApprove(scan.credit_id)}
              disabled={processing}
              className="flex-1 py-2.5 rounded-xl bg-terra-700 text-white text-sm font-semibold hover:bg-terra-800 disabled:opacity-50 transition-colors"
            >
              Accept & list on registry
            </button>
            <button
              onClick={() => onReject(scan)}
              disabled={processing}
              className="flex-1 py-2.5 rounded-xl border-2 border-red-200 text-red-600 text-sm font-semibold hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              Reject listing
            </button>
          </div>
        ) : (
          <div className={`rounded-xl px-4 py-2.5 text-sm font-medium text-center ${st.bg} ${st.text} border ${st.border}`}>
            {scan.status === "listed"   && "This credit is listed on the carbon registry"}
            {scan.status === "sold"     && "This credit has been sold"}
            {scan.status === "rejected" && "This listing was rejected"}
          </div>
        )}
      </div>
    </div>
  );
}

function PendingScansContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const plotId = searchParams.get("plot_id");

  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [scans, setScans] = useState<PendingScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [rejectTarget, setRejectTarget] = useState<PendingScan | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  useEffect(() => {
    if (!authLoading) {
      if (!isAuthenticated || !user) { router.push("/login"); return; }
      load();
    }
  }, [authLoading, isAuthenticated, user, plotId]);

  const load = async () => {
    if (!user?.id) return;
    try {
      let res: { pending_scans: PendingScan[] };
      if (plotId) {
        res = await api.getPlotScans(plotId, user.id) as { pending_scans: PendingScan[] };
      } else {
        res = await api.getPendingScans(user.id) as { pending_scans: PendingScan[] };
      }
      setScans(res.pending_scans || []);
    } catch {
      showToast("error", "Failed to load scan results");
    } finally {
      setLoading(false);
    }
  };

  const showToast = (type: "success" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 4000);
  };

  const handleApprove = async (creditId: string) => {
    setProcessing(true);
    try {
      await api.approveListing(creditId, true);
      setScans(prev => prev.map(s =>
        s.credit_id === creditId ? { ...s, status: "listed" } : s
      ));
      showToast("success", "Carbon credit listed on the registry.");
    } catch (e: any) {
      showToast("error", e.message || "Failed to approve listing");
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!rejectTarget) return;
    setProcessing(true);
    try {
      await api.approveListing(rejectTarget.credit_id, false, rejectionReason);
      setScans(prev => prev.map(s =>
        s.credit_id === rejectTarget.credit_id ? { ...s, status: "rejected" } : s
      ));
      setRejectTarget(null);
      setRejectionReason("");
      showToast("success", "Listing rejected.");
    } catch (e: any) {
      showToast("error", e.message || "Failed to reject listing");
    } finally {
      setProcessing(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface-subtle)]">
        <div className="flex items-center gap-3 text-muted">
          <div className="w-5 h-5 border-2 border-terra-600 border-t-transparent rounded-full animate-spin" />
          Loading scan results…
        </div>
      </div>
    );
  }

  const plotName = scans[0]?.plot_name;
  const pendingCount = scans.filter(s => s.status === "pending_approval").length;

  return (
    <div className="min-h-screen bg-[var(--color-surface-subtle)]">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">

        {/* Toast */}
        {toast && (
          <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold flex items-center gap-2 ${
            toast.type === "success" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"
          }`}>
            {toast.type === "success" ? "✓" : "✕"} {toast.msg}
          </div>
        )}

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-2 text-sm">
          <Link href="/landowner" className="text-muted hover:text-primary transition-colors">
            ← Dashboard
          </Link>
          {plotId && plotName && (
            <>
              <span className="text-muted">/</span>
              <Link
                href={`/landowner/monitoring/${plotId}`}
                className="text-muted hover:text-primary transition-colors"
              >
                {plotName}
              </Link>
            </>
          )}
        </div>

        <h1 className="text-2xl font-bold text-primary mb-1">
          {plotId && plotName ? `Credits — ${plotName}` : "Satellite scan results"}
        </h1>
        <p className="text-muted text-sm mb-8">
          {plotId
            ? "All scan results and carbon credit listings for this plot."
            : "Review and approve your scan results to list carbon credits on the registry."}
        </p>

        {scans.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[var(--color-border)] p-16 text-center shadow-sm">
            <div className="text-5xl mb-4">🛰️</div>
            <h2 className="text-lg font-bold text-primary mb-2">No scan results yet</h2>
            <p className="text-muted text-sm mb-6 max-w-xs mx-auto">
              {plotId
                ? "This plot hasn't been scanned yet. Scans are triggered by the system operator."
                : "When an operator scans your registered land you'll see the results here to review."}
            </p>
            <Link
              href="/landowner"
              className="inline-block bg-terra-700 text-white px-5 py-2 rounded-xl text-sm font-semibold hover:bg-terra-800 transition-colors"
            >
              Back to dashboard
            </Link>
          </div>
        ) : (
          <div className="space-y-5">
            <p className="text-sm text-muted">
              {scans.length} scan result{scans.length !== 1 ? "s" : ""}
              {pendingCount > 0 && ` · ${pendingCount} awaiting your approval`}
            </p>
            {scans.map(scan => (
              <ScanCard
                key={scan.credit_id}
                scan={scan}
                plotMode={!!plotId}
                onApprove={handleApprove}
                onReject={setRejectTarget}
                processing={processing}
              />
            ))}
          </div>
        )}
      </div>

      {/* Reject modal */}
      {rejectTarget && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-primary mb-1">Reject listing</h3>
            <p className="text-sm text-muted mb-4">
              This will prevent <strong>{rejectTarget.plot_name}</strong> credits from being listed.
              You can approve a future scan at any time.
            </p>
            <textarea
              value={rejectionReason}
              onChange={e => setRejectionReason(e.target.value)}
              className="w-full border border-[var(--color-border)] rounded-xl p-3 text-sm mb-4 resize-none focus:outline-none focus:ring-2 focus:ring-terra-500"
              rows={3}
              placeholder="Reason for rejection (optional)…"
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setRejectTarget(null); setRejectionReason(""); }}
                className="flex-1 py-2.5 rounded-xl border border-[var(--color-border)] text-secondary text-sm font-semibold hover:bg-[var(--color-surface-subtle)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={processing}
                className="flex-1 py-2.5 rounded-xl bg-red-600 text-white text-sm font-semibold hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {processing ? "Rejecting…" : "Confirm reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PendingScansPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface-subtle)]">
        <div className="flex items-center gap-3 text-muted">
          <div className="w-5 h-5 border-2 border-terra-600 border-t-transparent rounded-full animate-spin" />
          Loading…
        </div>
      </div>
    }>
      <PendingScansContent />
    </Suspense>
  );
}
