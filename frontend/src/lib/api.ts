// Empty string so all calls use relative paths (/api/...) which are proxied
// to the backend via the rewrites in next.config.js.
const API_URL = "";

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API request failed");
  }

  return res.json();
}

export const api = {
  // Scan
  runScan: (data: { plot_id?: string; geometry?: object; owner_id: string }) =>
    fetchAPI("/api/scan", { method: "POST", body: JSON.stringify(data) }),

  getScan: (scanId: string) => fetchAPI(`/api/scan/${scanId}`),

  // Plots
  getPlots: () => fetchAPI("/api/plots"),
  getPlotsGeoJSON: () => fetchAPI("/api/plots/geojson"),
  getPlot: (plotId: string) => fetchAPI(`/api/plots/${plotId}`),

  // NOTE: Credits/Transactions/Certificates/Dashboard-footprint functions
  // (getCredits, getCredit, getCreditStats, createCredit, updateCreditStatus,
  // createTransaction, getTransaction, getCertificateURL, calculateFootprint)
  // were removed here as part of the capstone re-scope. They called
  // /api/credits, /api/transactions, /api/certificates, /api/dashboard/footprint
  // — marketplace/buyer-footprint endpoints that are not mounted in this
  // prototype's backend (see backend/main.py) and had zero live call sites.
  // See backend/legacy/ and frontend/legacy/ for the preserved marketplace code.

  // Notifications
  getNotifications: (userId: string) =>
    fetchAPI(`/api/notifications/me?user_id=${userId}`),
  getUnreadCount: (userId: string) =>
    fetchAPI(`/api/notifications/unread-count?user_id=${userId}`),
  markNotificationRead: (notificationId: string) =>
    fetchAPI(`/api/notifications/${notificationId}/mark-read`, {
      method: "PATCH",
    }),
  markAllRead: (userId: string) =>
    fetchAPI(`/api/notifications/mark-all-read`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),

  // Monitoring
  getPlotsByOwner: (ownerId: string) => fetchAPI(`/api/plots/owner/${ownerId}`),
  deletePlot: (plotId: string, ownerId: string) =>
    fetchAPI(`/api/plots/${plotId}?owner_id=${ownerId}`, { method: "DELETE" }),
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
  getPendingScans: (userId: string) =>
    fetchAPI(`/api/landowner/pending-scans?user_id=${userId}`),
  getPlotScans: (plotId: string, userId: string) =>
    fetchAPI(`/api/landowner/pending-scans?user_id=${userId}&plot_id=${plotId}`),
  // District-scoped audit queue for verifier_analyst users — see
  // backend/routers/landowner.py's /verification-queue endpoint. Distinct
  // from getPendingScans, which is owner_id-scoped for stewards.
  getVerificationQueue: (verifierId: string) =>
    fetchAPI(`/api/landowner/verification-queue?verifier_id=${verifierId}`),
  approveListing: (creditId: string, approved: boolean, rejectionReason?: string) =>
    fetchAPI("/api/landowner/approve-listing", {
      method: "POST",
      body: JSON.stringify({
        credit_id: creditId,
        approved,
        rejection_reason: rejectionReason,
      }),
    }),
  getMyCredits: (userId: string) =>
    fetchAPI(`/api/landowner/my-credits?user_id=${userId}`),
};
