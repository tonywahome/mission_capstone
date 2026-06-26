"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import mapboxgl from "mapbox-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import "mapbox-gl/dist/mapbox-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";

function RequestRegistrationContent() {
  const { user } = useAuth();
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const draw = useRef<MapboxDraw | null>(null);

  const [formData, setFormData] = useState({
    landLocation: "",
    landSize: "",
    landType: "forest",
    additionalInfo: "",
  });
  const [drawnGeometry, setDrawnGeometry] = useState<any>(null);
  const [area, setArea] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  // Initialize Mapbox
  useEffect(() => {
    if (map.current) return;
    if (!mapContainer.current) return;

    // Fetch token at runtime from server-side API route — avoids build-time baking
    fetch('/api/config')
      .then(r => r.json())
      .then((config) => {
        console.log('=== CLIENT CONFIG DEBUG ===');
        console.log('Full config response:', config);
        console.log('Token length:', config.mapboxToken?.length || 0);
        console.log('Debug info:', config.debug);
        console.log('==========================');
        
        const { mapboxToken } = config;
        if (!mapboxToken) {
          console.error('❌ Mapbox token not configured - token is empty or undefined');
          console.error('This usually means NEXT_PUBLIC_MAPBOX_TOKEN is not set in Railway');
          alert('Map configuration error: Mapbox token not found. Please contact administrator.');
          return;
        }
        // @ts-ignore
        mapboxgl.workerUrl = '/mapbox-gl-csp-worker.js';
        mapboxgl.accessToken = mapboxToken;
        console.log('✓ Mapbox token set successfully');
        initMap();
      })
      .catch(err => {
        console.error('Failed to load config:', err);
        alert('Failed to load map configuration. Please refresh the page.');
      });

    function initMap() {
      if (!mapContainer.current) return;
      try {
        const mapInstance = new mapboxgl.Map({
          container: mapContainer.current,
          style: "mapbox://styles/mapbox/satellite-streets-v12",
          // Bugesera/Rulindo study area, Rwanda (was a stale Nairobi-area,
          // Kenya default from the pre-rescope marketplace prototype).
          center: [29.97, -1.95],
          zoom: 9,
        });

      map.current = mapInstance;

      const drawInstance = new MapboxDraw({
        displayControlsDefault: false,
        controls: {
          polygon: true,
          trash: true,
        },
        defaultMode: "simple_select",
      });

      draw.current = drawInstance;

      mapInstance.addControl(drawInstance);
      mapInstance.addControl(new mapboxgl.NavigationControl(), "top-right");

      mapInstance.on("draw.create", updateArea);
      mapInstance.on("draw.delete", updateArea);
      mapInstance.on("draw.update", updateArea);

      mapInstance.on("load", () => {
        console.log("Map loaded successfully!");
      });
      } catch (error) {
        console.error("Failed to initialize Mapbox:", error);
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
        const coords = (feature.geometry as any).coordinates[0];
        const areaHa = calculatePolygonArea(coords);
        setArea(areaHa);
        setFormData({ ...formData, landSize: areaHa.toFixed(2) });
      }
    } else {
      setDrawnGeometry(null);
      setArea(0);
    }
  }

  function calculatePolygonArea(coords: number[][]): number {
    let area = 0;
    for (let i = 0; i < coords.length - 1; i++) {
      const [x1, y1] = coords[i];
      const [x2, y2] = coords[i + 1];
      area += x1 * y2 - x2 * y1;
    }
    area = Math.abs(area / 2);
    return area * 111 * 111 * 100; // Convert to hectares
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `/api/registration/request`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            owner_name: user?.full_name,
            owner_email: user?.email,
            owner_id: user?.id,
            land_location: formData.landLocation,
            land_size: formData.landSize,
            land_type: formData.landType,
            additional_info: formData.additionalInfo,
            geometry: drawnGeometry,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to submit request");
      }

      setSuccess(true);
      setFormData({
        landLocation: "",
        landSize: "",
        landType: "forest",
        additionalInfo: "",
      });
      setDrawnGeometry(null);
      setArea(0);
      // Clear the drawn polygon
      if (draw.current) {
        draw.current.deleteAll();
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit request. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-terra-50 to-green-50 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-block p-4 bg-terra-100 rounded-full mb-4">
            <span className="text-4xl">🌳</span>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            Register Your Land as a TerraFoma Project
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Submit your land details and our research team will scan your property
            using AI satellite analysis. You'll be notified once a verifier/analyst
            has reviewed the results.
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {success ? (
            <div className="text-center py-12">
              <div className="inline-block p-6 bg-green-100 rounded-full mb-6">
                <svg
                  className="w-16 h-16 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                Request Submitted Successfully!
              </h2>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                Your land registration request has been sent to our admin team
                at <strong>mangamhizha@gmail.com</strong>. They will scan your
                land and contact you with the results.
              </p>
              <button
                onClick={() => setSuccess(false)}
                className="bg-terra-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-terra-700 transition"
              >
                Submit Another Request
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                  {error}
                </div>
              )}

              {/* Map Section */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Draw Your Land Boundary <span className="text-red-500">*</span>
                </label>
                <div className="border-2 border-gray-300 rounded-lg overflow-hidden">
                  <div
                    ref={mapContainer}
                    className="w-full"
                    style={{ height: "400px" }}
                  />
                </div>
                <div className="mt-2 flex items-center justify-between text-sm">
                  <p className="text-gray-500">
                    Click the polygon tool on the map to draw your land boundary
                  </p>
                  {drawnGeometry && (
                    <span className="text-green-600 font-medium">
                      ✓ Area: {area.toFixed(2)} hectares
                    </span>
                  )}
                </div>
              </div>

              {/* Owner Info (readonly) */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Your Information
                </h3>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      Name
                    </label>
                    <p className="text-sm font-medium">{user?.full_name}</p>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      Email
                    </label>
                    <p className="text-sm font-medium">{user?.email}</p>
                  </div>
                </div>
              </div>

              {/* Land Location */}
              <div>
                <label
                  htmlFor="landLocation"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Land Location <span className="text-red-500">*</span>
                </label>
                <input
                  id="landLocation"
                  type="text"
                  required
                  value={formData.landLocation}
                  onChange={(e) =>
                    setFormData({ ...formData, landLocation: e.target.value })
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-terra-500 focus:border-transparent"
                  placeholder="e.g., Nyamata, Bugesera or GPS coordinates"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Provide county, region, or GPS coordinates of your land
                </p>
              </div>

              {/* Land Size */}
              <div>
                <label
                  htmlFor="landSize"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Land Size (hectares) <span className="text-red-500">*</span>
                </label>
                <input
                  id="landSize"
                  type="number"
                  step="0.01"
                  required
                  value={formData.landSize}
                  readOnly={!!drawnGeometry}
                  onChange={(e) =>
                    setFormData({ ...formData, landSize: e.target.value })
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-terra-500 focus:border-transparent disabled:bg-gray-100"
                  placeholder="e.g., 25.5 (or draw on map)"
                />
                <p className="text-xs text-gray-500 mt-1">
                  {drawnGeometry
                    ? "Auto-calculated from drawn boundary"
                    : "Enter manually or draw on the map above"}
                </p>
              </div>

              {/* Land Type */}
              <div>
                <label
                  htmlFor="landType"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Land Type <span className="text-red-500">*</span>
                </label>
                <select
                  id="landType"
                  value={formData.landType}
                  onChange={(e) =>
                    setFormData({ ...formData, landType: e.target.value })
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-terra-500 focus:border-transparent"
                >
                  <option value="forest">Forest</option>
                  <option value="grassland">Grassland</option>
                  <option value="cropland">Cropland</option>
                  <option value="wetland">Wetland</option>
                  <option value="agroforestry">Agroforestry</option>
                </select>
              </div>

              {/* Additional Info */}
              <div>
                <label
                  htmlFor="additionalInfo"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Additional Information (Optional)
                </label>
                <textarea
                  id="additionalInfo"
                  rows={4}
                  value={formData.additionalInfo}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      additionalInfo: e.target.value,
                    })
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-terra-500 focus:border-transparent"
                  placeholder="Any additional details about your land, conservation efforts, or questions..."
                />
              </div>

              {/* Submit Button */}
              <div className="pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-terra-600 to-terra-700 text-white py-4 rounded-lg font-semibold hover:from-terra-700 hover:to-terra-800 disabled:opacity-50 transition-all shadow-lg"
                >
                  {loading ? "Submitting Request..." : "Submit Registration Request"}
                </button>
              </div>

              {/* Info Box */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <svg
                    className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="text-sm text-blue-800">
                    <p className="font-semibold mb-1">What happens next?</p>
                    <ul className="space-y-1 text-blue-700">
                      <li>• Admin receives your request via email</li>
                      <li>
                        • Your land is scanned using AI satellite imagery
                      </li>
                      <li>• Above-ground biomass and carbon stock (tCO₂e) are estimated</li>
                      <li>
                        • A verifier/analyst reviews the result and it is added to the audit trail
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </form>
          )}
        </div>

        {/* Contact Info */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <p>
            Questions? Contact our admin team at{" "}
            <a
              href="mailto:mangamhizha@gmail.com"
              className="text-terra-600 hover:text-terra-700 font-medium"
            >
              mangamhizha@gmail.com
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function RequestRegistrationPage() {
  return (
    <ProtectedRoute allowedRoles={["steward"]}>
      <RequestRegistrationContent />
    </ProtectedRoute>
  );
}
