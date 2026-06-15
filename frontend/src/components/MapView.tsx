"use client";

import { useRef, useEffect, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

interface MapViewProps {
  geojsonUrl?: string;
  geojsonData?: GeoJSON.FeatureCollection;
  onPlotClick?: (feature: GeoJSON.Feature) => void;
  center?: [number, number];
  zoom?: number;
  interactive?: boolean;
}

export default function MapView({
  geojsonUrl,
  geojsonData,
  onPlotClick,
  center = [36.8, -0.4],
  zoom = 8,
  interactive = true,
}: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!mapContainer.current) return;

    mapboxgl.accessToken =
      process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center,
      zoom,
      interactive,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      setLoaded(true);
    });

    return () => {
      map.current?.remove();
    };
  }, []);

  // Add GeoJSON data when loaded
  useEffect(() => {
    if (!loaded || !map.current) return;

    const loadData = async () => {
      let data = geojsonData;
      if (!data && geojsonUrl) {
        try {
          const res = await fetch(geojsonUrl);
          data = await res.json();
        } catch {
          return;
        }
      }
      if (!data) return;

      // Remove existing source/layers if re-rendering
      if (map.current!.getSource("plots")) {
        map.current!.removeLayer("plots-fill");
        map.current!.removeLayer("plots-outline");
        map.current!.removeSource("plots");
      }

      map.current!.addSource("plots", {
        type: "geojson",
        data,
      });

      map.current!.addLayer({
        id: "plots-fill",
        type: "fill",
        source: "plots",
        paint: {
          "fill-color": [
            "match",
            ["get", "land_use"],
            "forest", "#166534",
            "agroforestry", "#65a30d",
            "grassland", "#ca8a04",
            "cropland", "#d97706",
            "wetland", "#0891b2",
            "#16a34a",
          ],
          "fill-opacity": 0.5,
        },
      });

      map.current!.addLayer({
        id: "plots-outline",
        type: "line",
        source: "plots",
        paint: {
          "line-color": "#ffffff",
          "line-width": 2,
        },
      });

      // Click handler
      if (onPlotClick) {
        map.current!.on("click", "plots-fill", (e) => {
          if (e.features && e.features[0]) {
            onPlotClick(e.features[0] as unknown as GeoJSON.Feature);
          }
        });

        map.current!.on("mouseenter", "plots-fill", () => {
          map.current!.getCanvas().style.cursor = "pointer";
        });

        map.current!.on("mouseleave", "plots-fill", () => {
          map.current!.getCanvas().style.cursor = "";
        });
      }
    };

    loadData();
  }, [loaded, geojsonData, geojsonUrl]);

  return (
    <div ref={mapContainer} className="w-full h-full min-h-[400px] rounded-lg" />
  );
}
