"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { CarbonCredit } from "@/lib/types";
import { getStatusColor, getIntegrityColor } from "@/lib/utils";

const STATUS_FILTERS = ["all", "verified", "listed", "sold", "retired"];

export default function RegistryPage() {
  const [credits, setCredits] = useState<CarbonCredit[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const params = filter !== "all" ? { status: filter } : undefined;
    api
      .getCredits(params)
      .then((data) => setCredits(data as CarbonCredit[]))
      .catch((err) => setError(err?.message || "Failed to load credits. Is the backend running?"))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Credit Registry</h1>
        <p className="text-gray-500 mt-1">
          Transparent ledger of all verified carbon credits
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition ${
              filter === s
                ? "bg-terra-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 text-left text-sm text-gray-500">
              <th className="px-6 py-3">ID</th>
              <th className="px-6 py-3">Vintage</th>
              <th className="px-6 py-3">Quantity</th>
              <th className="px-6 py-3">Price/t</th>
              <th className="px-6 py-3">Integrity</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Date</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                  Loading...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-red-500">
                  {error}
                </td>
              </tr>
            ) : credits.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                  No credits found
                </td>
              </tr>
            ) : (
              credits.map((credit) => (
                <tr
                  key={credit.id}
                  className="border-t hover:bg-gray-50 transition"
                >
                  <td className="px-6 py-4 font-mono text-sm text-gray-600">
                    {credit.id.slice(0, 8)}
                  </td>
                  <td className="px-6 py-4">{credit.vintage_year}</td>
                  <td className="px-6 py-4 font-semibold">
                    {credit.quantity_tco2e.toFixed(1)} tCO2e
                  </td>
                  <td className="px-6 py-4">
                    ${credit.price_per_tonne.toFixed(2)}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`font-semibold ${getIntegrityColor(
                        credit.integrity_score
                      )}`}
                    >
                      {credit.integrity_score.toFixed(0)}/100
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        credit.status
                      )}`}
                    >
                      {credit.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {credit.created_at
                      ? new Date(credit.created_at).toLocaleDateString()
                      : "--"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
