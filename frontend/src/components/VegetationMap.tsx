"use client";

import { useRef, useEffect, useState } from "react";
import mapboxgl from "mapbox-gl";
import { api } from "@/lib/api";

type Band = "ndvi" | "evi" | "nbr" | "false_color" | "change";

const STATIC_BANDS: {
  id: Exclude<Band, "change">;
  label: string;
  desc: string;
  gradient: string[];
  low: string;
  high: string;
}[] = [
  {
    id: "ndvi",
    label: "NDVI",
    desc: "Vegetation density",
    gradient: ["#d73027", "#fee08b", "#66bd63", "#1a9850"],
    low: "Bare soil",
    high: "Dense canopy",
  },
  {
    id: "evi",
    label: "EVI",
    desc: "Canopy health",
    gradient: ["#d73027", "#fee08b", "#66bd63", "#1a9850"],
    low: "Poor",
    high: "Dense",
  },
  {
    id: "nbr",
    label: "NBR",
    desc: "Fire / burn ratio",
    gradient: ["#7f0000", "#d73027", "#fee08b", "#1a9850"],
    low: "Severe burn",
    high: "Healthy",
  },
  {
    id: "false_color",
    label: "False Color",
    desc: "NIR / Red / Green",
    gradient: ["#5c3317", "#e6b800", "#ff6600", "#cc0000"],
    low: "Bare / urban",
    high: "Dense veg.",
  },
];

const ZONE_STYLES: Record<string, { fill: string; stroke: string; label: string; desc: string }> = {
  critical:  { fill: "rgba(220,38,38,0.55)",  stroke: "#dc2626", label: "Critical loss",  desc: "Significant vegetation loss detected. Field verification recommended within 7 days." },
  degrading: { fill: "rgba(245,158,11,0.45)",  stroke: "#f59e0b", label: "Degrading",      desc: "Gradual NDVI decline. Inspect within 30 days — possible drought, pests or grazing." },
  stable:    { fill: "rgba(100,116,139,0.30)", stroke: "#64748b", label: "Stable",         desc: "No significant change vs. baseline. Carbon stock is being maintained." },
  improving: { fill: "rgba(22,163,74,0.45)",   stroke: "#16a34a", label: "Improving",      desc: "Vegetation gain detected. Likely active growth or recovery after a dry period." },
};

interface TilesData {
  gee_available: boolean;
  tiles?: Record<Exclude<Band, "change">, string>;
  date_range?: { from: string; to: string; n_images: number };
}

interface ChangeData {
  gee_available: boolean;
  reason?: string;
  change_tile?: string;
  zones?: GeoJSON.FeatureCollection;
  stats?: {
    stable_pct: number;
    degrading_pct: number;
    critical_pct: number;
    improving_pct: number;
  };
  date_range?: {
    current:  { from: string; to: string; n_images: number };
    baseline: { from: string; to: string; n_images: number };
  };
}

interface VegetationMapProps {
  plotId: string;
  geometry: GeoJSON.Polygon;
}

export default function VegetationMap({ plotId, geometry }: VegetationMapProps) {
  const container   = useRef<HTMLDivElement>(null);
  const map         = useRef<mapboxgl.Map | null>(null);
  const popup       = useRef<mapboxgl.Popup | null>(null);
  const hoverPopup  = useRef<mapboxgl.Popup | null>(null);

  const [mapReady,      setMapReady]      = useState(false);
  const [band,          setBand]          = useState<Band>("ndvi");
  const [opacity,       setOpacity]       = useState(80);
  const [tiles,         setTiles]         = useState<TilesData | null>(null);
  const [fetching,      setFetching]      = useState(true);
  const [changeData,    setChangeData]    = useState<ChangeData | null>(null);
  const [fetchingChange,setFetchingChange]= useState(false);

  // ── Map init ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!container.current || map.current) return;
    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";

    const coords = geometry.coordinates[0];
    const lons = coords.map((c) => c[0]);
    const lats = coords.map((c) => c[1]);

    map.current = new mapboxgl.Map({
      container: container.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      bounds: [
        [Math.min(...lons), Math.min(...lats)],
        [Math.max(...lons), Math.max(...lats)],
      ] as mapboxgl.LngLatBoundsLike,
      fitBoundsOptions: { padding: 120, maxZoom: 14 },
    });
    map.current.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.current.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.current.on("load", () => setMapReady(true));

    return () => {
      popup.current?.remove();
      hoverPopup.current?.remove();
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // ── Plot boundary ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;
    if (m.getSource("plot")) return;
    m.addSource("plot", {
      type: "geojson",
      data: { type: "Feature", geometry, properties: {} },
    });
    m.addLayer({
      id: "plot-outline",
      type: "line",
      source: "plot",
      paint: { "line-color": "#15803d", "line-width": 2.5, "line-dasharray": [4, 2] },
    });
  }, [mapReady, geometry]);

  // ── Fetch vegetation tiles ────────────────────────────────────────────────
  useEffect(() => {
    setFetching(true);
    (api.getVegetationTiles(plotId) as Promise<TilesData>)
      .then(setTiles)
      .catch(() => setTiles({ gee_available: false }))
      .finally(() => setFetching(false));
  }, [plotId]);

  // ── Fetch change-detection data when Change band is first selected ─────────
  useEffect(() => {
    if (band !== "change" || changeData !== null) return;
    setFetchingChange(true);
    (api.getChangeDetection(plotId) as Promise<ChangeData>)
      .then(setChangeData)
      .catch(() => setChangeData({ gee_available: false, reason: "fetch failed" }))
      .finally(() => setFetchingChange(false));
  }, [band, plotId]);

  // ── Auto-fit to plot when switching to Change view ────────────────────────
  useEffect(() => {
    if (band !== "change" || !mapReady || !map.current) return;
    const coords = geometry.coordinates[0];
    const lons   = coords.map((c) => c[0]);
    const lats   = coords.map((c) => c[1]);
    map.current.fitBounds(
      [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
      { padding: 80, maxZoom: 16, duration: 800 },
    );
  }, [band, mapReady, geometry]);

  // ── Raster overlay (static bands) ────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    if (band === "change") {
      // Remove static raster when switching to change view
      if (m.getLayer("veg-raster")) m.removeLayer("veg-raster");
      if (m.getSource("veg-tiles")) m.removeSource("veg-tiles");
      return;
    }

    if (!tiles?.gee_available || !tiles.tiles) return;
    const url = tiles.tiles[band as Exclude<Band, "change">];
    if (!url) return;

    try {
      if (m.getLayer("veg-raster")) m.removeLayer("veg-raster");
      if (m.getSource("veg-tiles")) m.removeSource("veg-tiles");

      m.addSource("veg-tiles", {
        type: "raster",
        tiles: [url],
        tileSize: 256,
        minzoom: 0,
        maxzoom: 18,
        attribution: "Google Earth Engine · Sentinel-2",
      });
      m.addLayer({
        id: "veg-raster",
        type: "raster",
        source: "veg-tiles",
        paint: { "raster-opacity": opacity / 100, "raster-fade-duration": 400 },
      });
      if (m.getLayer("plot-outline")) m.moveLayer("plot-outline");
    } catch (err) {
      console.error("[VegetationMap] Failed to add raster layer:", err);
    }
  }, [mapReady, tiles, band]);

  // ── Change detection raster + zone polygons ───────────────────────────────
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    // Remove change layers when switching away
    if (band !== "change") {
      if (m.getLayer("change-raster"))  m.removeLayer("change-raster");
      if (m.getSource("change-tiles"))  m.removeSource("change-tiles");
      if (m.getLayer("zones-labels"))   m.removeLayer("zones-labels");
      if (m.getLayer("zones-fill"))     m.removeLayer("zones-fill");
      if (m.getLayer("zones-outline"))  m.removeLayer("zones-outline");
      if (m.getSource("zones"))         m.removeSource("zones");
      popup.current?.remove();
      hoverPopup.current?.remove();
      m.getCanvas().style.cursor = "";
      return;
    }

    if (!changeData?.gee_available || !changeData.change_tile) return;

    try {
      // Change tile
      if (m.getLayer("change-raster")) m.removeLayer("change-raster");
      if (m.getSource("change-tiles")) m.removeSource("change-tiles");

      m.addSource("change-tiles", {
        type: "raster",
        tiles: [changeData.change_tile],
        tileSize: 256,
        minzoom: 0,
        maxzoom: 18,
        attribution: "Google Earth Engine · Sentinel-2 change detection",
      });
      m.addLayer({
        id: "change-raster",
        type: "raster",
        source: "change-tiles",
        paint: { "raster-opacity": opacity / 100, "raster-fade-duration": 400 },
      });

      // Zone polygons
      if (m.getLayer("zones-labels"))  m.removeLayer("zones-labels");
      if (m.getLayer("zones-fill"))    m.removeLayer("zones-fill");
      if (m.getLayer("zones-outline")) m.removeLayer("zones-outline");
      if (m.getSource("zones"))        m.removeSource("zones");

      if (changeData.zones?.features?.length) {
        m.addSource("zones", { type: "geojson", data: changeData.zones });

        // Coloured fill per zone
        m.addLayer({
          id: "zones-fill",
          type: "fill",
          source: "zones",
          paint: {
            "fill-color": [
              "match", ["get", "classification"],
              "critical",  ZONE_STYLES.critical.fill,
              "degrading", ZONE_STYLES.degrading.fill,
              "improving", ZONE_STYLES.improving.fill,
              ZONE_STYLES.stable.fill,
            ],
            "fill-opacity": 1,
          },
        });

        // Zone border
        m.addLayer({
          id: "zones-outline",
          type: "line",
          source: "zones",
          paint: {
            "line-color": [
              "match", ["get", "classification"],
              "critical",  ZONE_STYLES.critical.stroke,
              "degrading", ZONE_STYLES.degrading.stroke,
              "improving", ZONE_STYLES.improving.stroke,
              ZONE_STYLES.stable.stroke,
            ],
            "line-width": 1.5,
          },
        });

        // Permanent text label at the visual center of each non-stable zone
        m.addLayer({
          id: "zones-labels",
          type: "symbol",
          source: "zones",
          filter: ["!=", ["get", "classification"], "stable"],
          layout: {
            "text-field": [
              "match", ["get", "classification"],
              "critical",  "⚠ CRITICAL LOSS",
              "degrading", "↓ DEGRADING",
              "improving", "↑ IMPROVING",
              "",
            ],
            "text-font":          ["DIN Offc Pro Bold", "Arial Unicode MS Bold"],
            "text-size":          12,
            "text-anchor":        "center",
            "text-allow-overlap": false,
            "text-padding":       6,
          },
          paint: {
            "text-color": [
              "match", ["get", "classification"],
              "critical",  "#7f1d1d",
              "degrading", "#78350f",
              "improving", "#14532d",
              "#1e3a5f",
            ],
            "text-halo-color": "#ffffff",
            "text-halo-width": 2,
          },
        });

        // Hover popup — follows cursor, shows zone info in real time
        hoverPopup.current = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: [0, -8],
          maxWidth: "240px",
        });

        m.on("mousemove", "zones-fill", (e) => {
          if (!e.features?.length) return;
          const cls   = e.features[0].properties?.classification ?? "stable";
          const style = ZONE_STYLES[cls];
          m.getCanvas().style.cursor = "crosshair";
          hoverPopup.current!
            .setLngLat(e.lngLat)
            .setHTML(
              `<div style="font-family:sans-serif;padding:2px 0">
                <p style="font-weight:700;font-size:13px;margin:0 0 3px;color:${style.stroke}">
                  ${style.label}
                </p>
                <p style="font-size:11px;color:#555;margin:0;line-height:1.45">
                  ${style.desc}
                </p>
              </div>`
            )
            .addTo(m);
        });

        m.on("mouseleave", "zones-fill", () => {
          m.getCanvas().style.cursor = "";
          hoverPopup.current?.remove();
        });
      }

      if (m.getLayer("plot-outline")) m.moveLayer("plot-outline");
    } catch (err) {
      console.error("[VegetationMap] Failed to add change layer:", err);
    }
  }, [mapReady, changeData, band]);

  // ── Opacity sync ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;
    if (m.getLayer("veg-raster"))    m.setPaintProperty("veg-raster",    "raster-opacity", opacity / 100);
    if (m.getLayer("change-raster")) m.setPaintProperty("change-raster", "raster-opacity", opacity / 100);
  }, [mapReady, opacity]);

  // ── Derived display values ────────────────────────────────────────────────
  const activeBand  = STATIC_BANDS.find((b) => b.id === band);
  const isChange    = band === "change";
  const dr          = tiles?.date_range;
  const cdr         = changeData?.date_range;
  const stats       = changeData?.stats;

  return (
    <div className="bg-white rounded-2xl border border-[var(--color-border)] shadow-sm overflow-hidden">
      {/* Header + band switcher */}
      <div className="px-6 py-4 border-b border-[var(--color-border)] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-bold text-primary">Spatial vegetation map</h2>
          <p className="text-sm text-muted">
            {isChange && cdr
              ? `Change detection · ${cdr.current.from} vs ${cdr.baseline.from}–${cdr.baseline.to}`
              : dr
              ? `Sentinel-2 composite · ${dr.from} → ${dr.to} · ${dr.n_images} image${dr.n_images !== 1 ? "s" : ""}`
              : "Sentinel-2 satellite imagery · spectral indices overlay"}
          </p>
        </div>
        <div className="flex rounded-xl border border-[var(--color-border)] overflow-hidden text-xs font-semibold flex-shrink-0">
          {STATIC_BANDS.map((b) => (
            <button
              key={b.id}
              onClick={() => setBand(b.id)}
              title={b.desc}
              className={`px-3 py-1.5 transition-colors ${
                band === b.id ? "bg-terra-700 text-white" : "text-muted hover:bg-terra-50"
              }`}
            >
              {b.label}
            </button>
          ))}
          <button
            onClick={() => setBand("change")}
            title="Pixel-level change detection vs. 6-month baseline"
            className={`px-3 py-1.5 transition-colors border-l border-[var(--color-border)] ${
              isChange ? "bg-slate-800 text-white" : "text-muted hover:bg-slate-50"
            }`}
          >
            Change
          </button>
        </div>
      </div>

      {/* Map */}
      <div className="relative" style={{ height: 640 }}>
        <div ref={container} style={{ width: "100%", height: "100%" }} />

        {/* Main loading overlay */}
        {fetching && (
          <div className="absolute inset-0 bg-black/25 backdrop-blur-[2px] flex items-center justify-center">
            <div className="bg-white rounded-xl px-5 py-4 flex items-center gap-3 shadow-xl">
              <div className="w-5 h-5 border-2 border-terra-700 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-medium text-primary">Fetching satellite imagery…</span>
            </div>
          </div>
        )}

        {/* Change detection loading overlay */}
        {isChange && fetchingChange && (
          <div className="absolute inset-0 bg-black/25 backdrop-blur-[2px] flex items-center justify-center">
            <div className="bg-white rounded-xl px-5 py-5 flex flex-col items-center gap-3 shadow-xl max-w-xs text-center">
              <div className="w-6 h-6 border-2 border-slate-700 border-t-transparent rounded-full animate-spin" />
              <div>
                <p className="text-sm font-semibold text-primary">Computing change detection…</p>
                <p className="text-xs text-muted mt-0.5">
                  Comparing last 30 days to prior 6 months. This may take 20–40 s.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* GEE unavailable notice */}
        {!fetching && !tiles?.gee_available && !isChange && (
          <div className="absolute bottom-10 left-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 shadow-md max-w-xs">
            <p className="text-sm font-semibold text-amber-800">Spectral overlay unavailable</p>
            <p className="text-xs text-amber-700 mt-0.5">
              GEE service account required. Plot boundary is shown on the satellite basemap.
            </p>
          </div>
        )}

        {/* Change detection unavailable */}
        {isChange && !fetchingChange && changeData && !changeData.gee_available && (
          <div className="absolute bottom-10 left-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 shadow-md max-w-xs">
            <p className="text-sm font-semibold text-amber-800">Change detection unavailable</p>
            <p className="text-xs text-amber-700 mt-0.5">
              {changeData.reason ?? "Insufficient imagery for change detection in this period."}
            </p>
          </div>
        )}

        {/* ── Static band controls (NDVI / EVI / NBR / False Color) ───────── */}
        {!fetching && tiles?.gee_available && !isChange && (
          <>
            {/* Opacity slider */}
            <div className="absolute top-4 left-4 bg-white/96 backdrop-blur-sm rounded-xl border border-[var(--color-border)] shadow-lg p-3 w-44">
              <p className="text-xs font-semibold text-primary mb-2">Overlay opacity · {opacity}%</p>
              <input
                type="range" min={20} max={100} value={opacity}
                onChange={(e) => setOpacity(Number(e.target.value))}
                className="w-full accent-terra-700"
              />
            </div>

            {/* Legend */}
            {activeBand && (
              <div className="absolute bottom-8 right-4 bg-white/96 backdrop-blur-sm rounded-xl border border-[var(--color-border)] shadow-lg p-3 min-w-[190px]">
                <p className="text-xs font-bold text-primary mb-1.5">
                  {activeBand.label} — {activeBand.desc}
                </p>
                <div
                  className="h-3 rounded-full mb-1.5"
                  style={{ background: `linear-gradient(to right, ${activeBand.gradient.join(", ")})` }}
                />
                <div className="flex justify-between text-[10px] text-muted">
                  <span>{activeBand.low}</span>
                  <span>{activeBand.high}</span>
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Change detection controls ────────────────────────────────────── */}
        {isChange && !fetchingChange && changeData?.gee_available && (
          <>
            {/* Opacity slider */}
            <div className="absolute top-4 left-4 bg-white/96 backdrop-blur-sm rounded-xl border border-[var(--color-border)] shadow-lg p-3 w-44">
              <p className="text-xs font-semibold text-primary mb-2">Overlay opacity · {opacity}%</p>
              <input
                type="range" min={20} max={100} value={opacity}
                onChange={(e) => setOpacity(Number(e.target.value))}
                className="w-full accent-slate-700"
              />
            </div>

            {/* Change legend */}
            <div className="absolute bottom-8 right-4 bg-white/96 backdrop-blur-sm rounded-xl border border-[var(--color-border)] shadow-lg p-3 min-w-[190px]">
              <p className="text-xs font-bold text-primary mb-1.5">Δ NDVI — Change from baseline</p>
              <div
                className="h-3 rounded-full mb-1.5"
                style={{
                  background:
                    "linear-gradient(to right, #7f0000, #d73027, #fee08b, #ffffbf, #d9ef8b, #1a9850, #006837)",
                }}
              />
              <div className="flex justify-between text-[10px] text-muted">
                <span>Severe loss</span>
                <span>No change</span>
                <span>Strong gain</span>
              </div>
            </div>

            {/* Zone stats panel */}
            {stats && (
              <div className="absolute top-4 right-14 bg-white/96 backdrop-blur-sm rounded-xl border border-[var(--color-border)] shadow-lg p-3 w-52">
                <p className="text-xs font-bold text-primary mb-2">Plot change breakdown</p>
                {(
                  [
                    ["critical",  "Critical",  stats.critical_pct,  "#dc2626"],
                    ["degrading", "Degrading", stats.degrading_pct, "#f59e0b"],
                    ["stable",    "Stable",    stats.stable_pct,    "#3b82f6"],
                    ["improving", "Improving", stats.improving_pct, "#16a34a"],
                  ] as [string, string, number, string][]
                ).map(([, label, pct, color]) => (
                  <div key={label} className="mb-1.5">
                    <div className="flex justify-between text-[11px] mb-0.5">
                      <span className="font-medium" style={{ color }}>{label}</span>
                      <span className="text-muted font-semibold">{pct}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                ))}
                {changeData.zones?.features && (
                  <p className="text-[10px] text-muted mt-2">
                    Click a zone on the map for details
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
