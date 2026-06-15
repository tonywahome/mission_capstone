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

  // Credits
  getCredits: (params?: { status?: string; min_integrity?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.min_integrity)
      query.set("min_integrity", String(params.min_integrity));
    return fetchAPI(`/api/credits?${query}`);
  },
  getCredit: (creditId: string) => fetchAPI(`/api/credits/${creditId}`),
  getCreditStats: () => fetchAPI("/api/credits/stats"),
  createCredit: (data: object) =>
    fetchAPI("/api/credits", { method: "POST", body: JSON.stringify(data) }),
  updateCreditStatus: (creditId: string, status: string) =>
    fetchAPI(`/api/credits/${creditId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // Transactions
  createTransaction: (data: object) =>
    fetchAPI("/api/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getTransaction: (txId: string) => fetchAPI(`/api/transactions/${txId}`),

  // Certificates
  getCertificateURL: (txId: string) =>
    `${API_URL}/api/certificates/${txId}`,

  // Dashboard
  calculateFootprint: (data: {
    energy_kwh_monthly: number;
    fuel_litres_monthly: number;
    fuel_type: string;
    natural_gas_m3_monthly?: number;
    refrigerant_leaked_kg_annual?: number;
    flights_short_km_annual?: number;
    flights_long_km_annual?: number;
    waste_landfill_kg_monthly?: number;
    waste_recycled_kg_monthly?: number;
    water_m3_monthly?: number;
    freight_tonne_km_monthly?: number;
    freight_sea_tonne_km_monthly?: number;
    supply_chain_spend_usd_monthly?: number;
  }) =>
    fetchAPI("/api/dashboard/footprint", {
      method: "POST",
      body: JSON.stringify(data),
    }),

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
