"use client";

import { useState, useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import "mapbox-gl/dist/mapbox-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import IntegrityBadge from "@/components/IntegrityBadge";
import RiskGauge from "@/components/RiskGauge";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api } from "@/lib/api";
import type { ScanResult } from "@/lib/types";

function ScanPageContent() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const draw = useRef<MapboxDraw | null>(null);

  const [drawnGeometry, setDrawnGeometry] = useState<any>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [area, setArea] = useState<number>(0);
  const [ownerInfo, setOwnerInfo] = useState<any>(null);
  // resolved once on map load — persists even after localStorage is cleared
  const [resolvedOwnerId, setResolvedOwnerId] = useState<string>("demo-user");
  const [toast, setToast] = useState<{
    type: "success" | "error";
    msg: string;
  } | null>(null);

  const vegetationCoverPct = scanResult?.vegetation_cover_pct ?? 0;

  const showToast = (type: "success" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 5000);
  };

  useEffect(() => {
    if (map.current) return;
    if (!mapContainer.current) return;

    fetch("/api/config")
      .then((r) => r.json())
      .then(async (config) => {
        const { mapboxToken } = config;
        if (!mapboxToken) {
          showToast(
            "error",
            "Mapbox token not configured. Contact your administrator.",
          );
          return;
        }
        // @ts-ignore
        mapboxgl.workerUrl = "/mapbox-gl-csp-worker.js";
        mapboxgl.accessToken = mapboxToken;
        initMap();
      })
      .catch(() =>
        showToast("error", "Failed to load map configuration. Please refresh."),
      );

    async function initMap() {
      if (!mapContainer.current) return;
      try {
        const mapInstance = new mapboxgl.Map({
          container: mapContainer.current,
          style: "mapbox://styles/mapbox/satellite-streets-v12",
          // Bugesera/Rulindo study area, Rwanda (was a stale Nairobi-area,
          // Kenya default from the pre-rescope marketplace prototype).
          center: [29.97, -1.95],
          zoom: 10,
        });

        map.current = mapInstance;

        const drawInstance = new MapboxDraw({
          displayControlsDefault: false,
          controls: { polygon: true, trash: true },
          defaultMode: "draw_polygon",
        });

        draw.current = drawInstance;
        mapInstance.addControl(drawInstance);
        mapInstance.addControl(new mapboxgl.NavigationControl(), "top-right");

        mapInstance.on("draw.create", updateArea);
        mapInstance.on("draw.delete", updateArea);
        mapInstance.on("draw.update", updateArea);

        mapInstance.on("load", async () => {
          const storedGeometry = localStorage.getItem("scanGeometry");
          const storedOwnerStr = localStorage.getItem("scanOwnerInfo");

          if (storedGeometry && drawInstance) {
            try {
              const geometry = JSON.parse(storedGeometry);
              drawInstance.add({
                type: "Feature",
                geometry,
                properties: {},
              } as any);
              setDrawnGeometry(geometry);

              if (geometry.type === "Polygon") {
                setArea(calculatePolygonArea(geometry.coordinates[0]) * 100);
              }

              const coordinates = geometry.coordinates[0];
              const bounds = coordinates.reduce(
                (b: any, c: any) => b.extend(c),
                new mapboxgl.LngLatBounds(coordinates[0], coordinates[0]),
              );
              mapInstance.fitBounds(bounds, { padding: 50 });
            } catch (e) {
              console.error("Failed to load stored geometry:", e);
            }
          }

          if (storedOwnerStr) {
            try {
              const info = JSON.parse(storedOwnerStr);
              setOwnerInfo(info);

              // Resolve the real user_id NOW (before localStorage is cleared)
              // and keep it in state so handleScan can use it later.
              if (info.email) {
                const res = await fetch(
                  `/api/auth/user-by-email?email=${encodeURIComponent(info.email)}`,
                );
                if (res.ok) {
                  const userData = await res.json();
                  if (userData.id) {
                    setResolvedOwnerId(userData.id);
                    console.log("Resolved owner_id:", userData.id);
                  }
                } else {
                  console.warn(
                    "user-by-email returned",
                    res.status,
                    "— will use demo-user",
                  );
                }
              }
            } catch (e) {
              console.warn("Could not resolve owner from stored info:", e);
            }
          }

          // Clear after resolving everything
          localStorage.removeItem("scanGeometry");
          localStorage.removeItem("scanOwnerInfo");
          localStorage.removeItem("scanRequestId");
        });

        mapInstance.on("error", (e) => console.error("Mapbox error:", e));
      } catch (e) {
        console.error("Failed to initialise Mapbox:", e);
      }
    }

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  function updateArea() {
    const data = draw.current?.getAll();
    if (data && data.features.length > 0) {
      const feature = data.features[0];
      setDrawnGeometry(feature.geometry);
      if (feature.geometry.type === "Polygon") {
        setArea(
          calculatePolygonArea((feature.geometry as any).coordinates[0]) * 100,
        );
      }
    } else {
      setDrawnGeometry(null);
      setArea(0);
      setScanResult(null);
    }
  }

  function calculatePolygonArea(coords: number[][]): number {
    let area = 0;
    for (let i = 0; i < coords.length - 1; i++) {
      const [x1, y1] = coords[i];
      const [x2, y2] = coords[i + 1];
      area += x1 * y2 - x2 * y1;
    }
    return Math.abs(area / 2) * 111 * 111;
  }

  const handleScan = async () => {
    if (!drawnGeometry) return;
    setLoading(true);
    setScanResult(null);

    try {
      // Use the owner_id resolved during map load (in state, not localStorage which was cleared)
      const result = (await api.runScan({
        geometry: drawnGeometry,
        owner_id: resolvedOwnerId,
      })) as ScanResult;

      setScanResult(result);

      if (ownerInfo && resolvedOwnerId !== "demo-user") {
        showToast(
          "success",
          `Scan complete. Notification sent to ${ownerInfo.name} to review and approve.`,
        );
      } else {
        showToast("success", "Scan complete.");
      }
    } catch (err: any) {
      console.error("Scan failed:", err);
      showToast(
        "error",
        err.message ||
          "Scan failed. Check the backend dMRV service is reachable.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* Map */}
      <div className="flex-1 relative">
        <div ref={mapContainer} className="absolute inset-0 w-full h-full" />
      </div>

      {/* Sidebar */}
      <div className="w-96 bg-[var(--color-surface)] border-l border-[var(--color-border)] overflow-y-auto flex flex-col">
        {/* Toast */}
        {toast && (
          <div
            className={`mx-4 mt-4 px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-2 ${
              toast.type === "success"
                ? "bg-emerald-50 border border-emerald-300 text-emerald-700"
                : "bg-red-50 border border-red-300 text-red-700"
            }`}
          >
            {toast.type === "success" ? "✓" : "✕"} {toast.msg}
          </div>
        )}

        <div className="p-6 flex-1">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">🛰️</span>
              <h2 className="text-xl font-bold text-[var(--color-text-primary)]">
                Land Scanner
              </h2>
            </div>
            <p className="text-sm text-[var(--color-text-muted)]">
              Draw a polygon on the map to select a plot, then run a satellite
              scan to estimate vegetation cover and carbon stock.
            </p>
          </div>
          "🛰️ Estimate vegetation cover"
          {ownerInfo && (
            <div className="bg-[var(--color-surface-muted)] border border-[var(--color-border)] rounded-xl p-4 mb-5">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-terra-700 text-white text-xs flex items-center justify-center font-bold">
                  {ownerInfo.name?.charAt(0).toUpperCase() ?? "?"}
                </div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                  Registration request
                </p>
              </div>
              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-[var(--color-text-muted)]">Owner</span>
                  <span className="font-semibold text-[var(--color-text-primary)]">
                    {ownerInfo.name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--color-text-muted)]">Email</span>
                  <span className="font-medium text-[var(--color-text-secondary)] truncate max-w-[180px]">
                    {ownerInfo.email}
                  </span>
                </div>
                {ownerInfo.location && (
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">
                      Location
                    </span>
                    <span className="font-medium text-[var(--color-text-secondary)]">
                      {ownerInfo.location}
                    </span>
                  </div>
                )}
              </div>
              <div
                className={`mt-2.5 pt-2.5 border-t border-[var(--color-border)] flex items-center gap-1.5 text-xs font-semibold ${
                  resolvedOwnerId !== "demo-user"
                    ? "text-emerald-600"
                    : "text-amber-600"
                }`}
              >
                {resolvedOwnerId !== "demo-user"
                  ? "✓ Owner ID resolved — notification will reach this user"
                  : "⚠ Owner ID not resolved — scan will use demo account"}
              </div>
            </div>
          )}
          {drawnGeometry ? (
            <div className="space-y-4">
              {/* Selected plot info */}
              <div className="bg-[var(--color-surface-muted)] rounded-xl p-4">
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
                  Selected plot
                </p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-[var(--color-text-muted)]">Area</div>
                    <div className="font-bold text-[var(--color-text-primary)]">
                      {area.toFixed(2)} ha
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--color-text-muted)]">Status</div>
                    <div className="font-bold text-emerald-600">
                      Ready to scan
                    </div>
                  </div>
                </div>
              </div>

              {/* Scan button */}
              {!scanResult && (
                <button
                  onClick={handleScan}
                  disabled={loading}
                  className="w-full bg-terra-700 text-white py-3 rounded-xl font-semibold hover:bg-terra-800 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />{" "}
                      Scanning…
                    </>
                  ) : (
                    "🛰️  Run satellite scan"
                  )}
                </button>
              )}

              {/* Loading state */}
              {loading && (
                <div className="bg-[var(--color-surface-muted)] border border-[var(--color-border)] rounded-xl p-4 text-sm">
                  <p className="font-semibold text-[var(--color-text-primary)] mb-2">
                    Processing…
                  </p>
                  <ul className="space-y-1 text-[var(--color-text-muted)]">
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-terra-500" />
                      Extracting Sentinel-2 imagery
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-terra-500" />
                      Calculating NDVI, EVI indices
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-terra-500" />
                      Running GEDI biomass model
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-terra-500" />
                      Estimating carbon stock
                    </li>
                  </ul>
                </div>
              )}

              {/* Scan results */}
              {scanResult && (
                <div className="space-y-4">
                  {/* Carbon summary */}
                  <div className="bg-[var(--color-surface-muted)] rounded-xl p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
                      Scan results
                    </p>
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <div className="text-3xl font-bold text-terra-700">
                          {vegetationCoverPct.toFixed(1)}%
                        </div>
                        <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                          Vegetation cover estimate
                        </div>
                      </div>
                      <IntegrityBadge score={scanResult.integrity_score} />
                    </div>

                    <div className="text-xs text-[var(--color-text-muted)] mb-4">
                      Model-backed estimate derived from Sentinel-2 NDVI and
                      EVI, with the trained biomass model used for the
                      underlying land scan.
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {[
                        {
                          label: "NDVI",
                          value: scanResult.mean_ndvi.toFixed(3),
                        },
                        { label: "EVI", value: scanResult.mean_evi.toFixed(3) },
                        {
                          label: "Biomass",
                          value: `${scanResult.estimated_biomass.toFixed(1)} t/ha`,
                        },
                        {
                          label: "Carbon stock",
                          value: `${scanResult.estimated_tco2e.toFixed(1)} tCO₂e`,
                        },
                      ].map(({ label, value }) => (
                        <div
                          key={label}
                          className="bg-[var(--color-surface)] rounded-lg p-2.5"
                        >
                          <div className="text-xs text-[var(--color-text-muted)]">
                            {label}
                          </div>
                          <div className="font-semibold text-[var(--color-text-primary)] mt-0.5">
                            {value}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Uncertainty / risk */}
                  <div className="bg-[var(--color-surface-muted)] rounded-xl p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
                      Uncertainty
                    </p>
                    <RiskGauge
                      score={scanResult.risk_adjustment}
                      label="Permanence Risk"
                    />
                  </div>

                  {/* Next steps */}
                  <div className="bg-[var(--color-surface-muted)] border border-[var(--color-border)] rounded-xl p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
                      Next steps
                    </p>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2 text-emerald-600">
                        <span>✓</span> Scan saved to database
                      </div>
                      <div
                        className={`flex items-center gap-2 ${resolvedOwnerId !== "demo-user" ? "text-emerald-600" : "text-amber-600"}`}
                      >
                        <span>
                          {resolvedOwnerId !== "demo-user" ? "✓" : "⚠"}
                        </span>
                        {resolvedOwnerId !== "demo-user"
                          ? "In-app notification sent to landowner"
                          : "Notification sent to demo account (owner ID unresolved)"}
                      </div>
                      <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
                        <span>⏳</span> Awaiting landowner approval
                      </div>
                    </div>
                    {ownerInfo && resolvedOwnerId !== "demo-user" && (
                      <div className="mt-3 pt-3 border-t border-[var(--color-border)] text-xs text-[var(--color-text-muted)]">
                        <strong className="text-[var(--color-text-secondary)]">
                          {ownerInfo.name}
                        </strong>{" "}
                        will review results under <em>Pending scans</em> in
                        their dashboard.
                      </div>
                    )}
                  </div>

                  {/* Re-scan button */}
                  <button
                    onClick={() => {
                      setScanResult(null);
                    }}
                    className="w-full py-2.5 rounded-xl border border-[var(--color-border)] text-[var(--color-text-secondary)] text-sm font-medium hover:bg-[var(--color-surface-muted)] transition-colors"
                  >
                    Draw new polygon
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* Empty state */
            <div className="text-center py-12">
              <div className="w-14 h-14 bg-[var(--color-surface-muted)] rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-7 h-7 text-[var(--color-text-muted)]"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                  />
                </svg>
              </div>
              <p className="font-semibold text-[var(--color-text-primary)] mb-1">
                Draw a plot boundary
              </p>
              <p className="text-sm text-[var(--color-text-muted)] mb-5">
                Use the polygon tool on the map to select the land area you want
                to scan.
              </p>
              <ol className="text-xs text-[var(--color-text-muted)] space-y-1.5 text-left bg-[var(--color-surface-muted)] rounded-xl p-4">
                <li className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-terra-700 text-white text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5">
                    1
                  </span>
                  Click the polygon icon in the map toolbar
                </li>
                <li className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-terra-700 text-white text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5">
                    2
                  </span>
                  Click to place boundary points around the plot
                </li>
                <li className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-terra-700 text-white text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5">
                    3
                  </span>
                  Double-click to complete the polygon
                </li>
              </ol>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ScanPage() {
  return (
    <ProtectedRoute allowedRoles={["steward", "research_admin"]}>
      <ScanPageContent />
    </ProtectedRoute>
  );
}
