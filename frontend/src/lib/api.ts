import { supabase } from "@/lib/supabase";

// Empty string so all calls use relative paths (/api/...) which are proxied
// to the backend via the rewrites in next.config.js.
const API_URL = "";

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (session) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API request failed");
  }

  return res.json();
}

export const api = {
  // Scan
  runScan: (data: {
    plot_id?: string;
    geometry?: object;
    owner_id?: string; // research_admin only — scan on behalf of a steward
    registration_request_id?: string;
  }) => fetchAPI("/api/scan", { method: "POST", body: JSON.stringify(data) }),

  getScan: (scanId: string) => fetchAPI(`/api/scan/${scanId}`),

  submitScanForReview: (data: {
    scan_id: string;
    plot_id?: string | null;
    owner_id?: string; // research_admin only — matches runScan's override path
    tco2e: number;
    integrity_score: number;
    risk_score: number;
  }) =>
    fetchAPI("/api/scan/submit-review", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // NOTE: Credits/Transactions/Certificates/Dashboard-footprint functions
  // (getCredits, getCredit, getCreditStats, createCredit, updateCreditStatus,
  // createTransaction, getTransaction, getCertificateURL, calculateFootprint)
  // were removed here as part of the capstone re-scope. They called
  // /api/credits, /api/transactions, /api/certificates, /api/dashboard/footprint
  // — marketplace/buyer-footprint endpoints that are not mounted in this
  // prototype's backend (see backend/main.py) and had zero live call sites.
  // See backend/legacy/ and frontend/legacy/ for the preserved marketplace code.

  // Plots
  getPlots: () => fetchAPI("/api/plots"),
  getPlotsGeoJSON: () => fetchAPI("/api/plots/geojson"),
  getPlot: (plotId: string) => fetchAPI(`/api/plots/${plotId}`),

  // Notifications
  getNotifications: () => fetchAPI(`/api/notifications/me`),
  getUnreadCount: () => fetchAPI(`/api/notifications/unread-count`),
  markNotificationRead: (notificationId: string) =>
    fetchAPI(`/api/notifications/${notificationId}/mark-read`, {
      method: "PATCH",
    }),
  markAllRead: () =>
    fetchAPI(`/api/notifications/mark-all-read`, { method: "POST" }),

  // Monitoring
  getPlotsByOwner: (ownerId: string) => fetchAPI(`/api/plots/owner/${ownerId}`),
  deletePlot: (plotId: string) =>
    fetchAPI(`/api/plots/${plotId}`, { method: "DELETE" }),
  getLatestMonitoring: (plotId: string) => fetchAPI(`/api/monitoring/plots/${plotId}/latest`),
  getMonitoringHistory: (plotId: string, limit = 52) =>
    fetchAPI(`/api/monitoring/plots/${plotId}/history?limit=${limit}`),
  runMonitoringCheck: (plotId: string) =>
    fetchAPI(`/api/monitoring/plots/${plotId}/run`, { method: "POST" }),
  getMonitoringSummary: () => fetchAPI("/api/monitoring/summary"),
  getVegetationTiles: (plotId: string, daysBack = 30) =>
    fetchAPI(`/api/monitoring/plots/${plotId}/vegetation-tiles?days_back=${daysBack}`),
  getChangeDetection: (plotId: string, currentDays = 30, baselineDays = 180) =>
    fetchAPI(`/api/monitoring/plots/${plotId}/change-detection?current_days=${currentDays}&baseline_days=${baselineDays}`),

  // Landowner - Pending Scans & Approval
  getPendingScans: () => fetchAPI(`/api/landowner/pending-scans`),
  getPlotScans: (plotId: string) =>
    fetchAPI(`/api/landowner/pending-scans?plot_id=${plotId}`),
  // District-scoped audit queue for analyst users — see
  // backend/routers/landowner.py's /verification-queue endpoint. Distinct
  // from getPendingScans, which is owner-scoped for stewards.
  getVerificationQueue: () => fetchAPI(`/api/landowner/verification-queue`),
  approveListing: (creditId: string, approved: boolean, rejectionReason?: string) =>
    fetchAPI("/api/landowner/approve-listing", {
      method: "POST",
      body: JSON.stringify({
        credit_id: creditId,
        approved,
        rejection_reason: rejectionReason,
      }),
    }),
  unsubmitScan: (creditId: string) =>
    fetchAPI("/api/landowner/unsubmit", {
      method: "POST",
      body: JSON.stringify({ credit_id: creditId }),
    }),
  getMyCredits: () => fetchAPI(`/api/landowner/my-credits`),

  // Registration requests (admin review)
  submitRegistrationRequest: (data: {
    owner_name: string;
    owner_email: string;
    land_location: string;
    land_size: string;
    land_type: string;
    coordinates?: { lat: number; lon: number };
    boundaries?: number[][];
    geometry?: object;
    additional_info?: string;
  }) =>
    fetchAPI("/api/registration/request", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getPlotForRegistrationRequest: (requestId: string) =>
    fetchAPI(`/api/registration/requests/${requestId}/plot`),
  getRegistrationRequests: (status?: "pending" | "approved" | "rejected") =>
    fetchAPI(`/api/registration/requests${status ? `?status=${status}` : ""}`),
  approveRegistrationRequest: (requestId: string) =>
    fetchAPI(`/api/registration/requests/${requestId}/approve`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  rejectRegistrationRequest: (requestId: string, rejectionReason?: string) =>
    fetchAPI(`/api/registration/requests/${requestId}/reject`, {
      method: "POST",
      body: JSON.stringify({ rejection_reason: rejectionReason }),
    }),
};
