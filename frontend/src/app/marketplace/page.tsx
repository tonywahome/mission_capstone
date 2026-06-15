"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { CarbonCredit } from "@/lib/types";
import IntegrityBadge from "@/components/IntegrityBadge";
import RiskGauge from "@/components/RiskGauge";

export default function MarketplacePage() {
  const [credits, setCredits] = useState<CarbonCredit[]>([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [purchased, setPurchased] = useState<string[]>([]);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "premium" | "standard">("all");

  useEffect(() => {
    api
      .getCredits({ status: "listed" })
      .then((data) => {
        let items = data as CarbonCredit[];
        // Also show verified credits if no listed ones
        if (items.length === 0) {
          api.getCredits({ status: "verified" }).then((d) => {
            setCredits(d as CarbonCredit[]);
            setLoading(false);
          });
        } else {
          setCredits(items);
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
  }, []);

  const calculateCommunityBenefit = (credit: CarbonCredit) => {
    const totalValue = credit.price_per_tonne * credit.quantity_tco2e;
    const communityShare = totalValue * 0.6; // 60% to communities
    return communityShare;
  };

  const getQualityTier = (credit: CarbonCredit) => {
    if (credit.integrity_score >= 90 && credit.risk_score < 0.15)
      return { label: "Premium", color: "emerald" };
    if (credit.integrity_score >= 75 && credit.risk_score < 0.3)
      return { label: "High Quality", color: "green" };
    if (credit.integrity_score >= 60 && credit.risk_score < 0.45)
      return { label: "Standard", color: "blue" };
    return { label: "Basic", color: "gray" };
  };

  const handlePurchase = async (credit: CarbonCredit) => {
    setPurchasing(credit.id);
    setCheckoutError(null);
    try {
      const res = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          creditId: credit.id,
          creditName: credit.plot_name ?? `Credit ${credit.id.slice(0, 8)}`,
          quantity: credit.quantity_tco2e,
          totalPrice: credit.price_per_tonne * credit.quantity_tco2e,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Checkout failed");

      window.location.href = data.url;
    } catch (err: any) {
      console.error("Purchase failed:", err);
      setCheckoutError(
        err?.message ?? "Failed to start checkout. Please try again.",
      );
      setPurchasing(null);
    }
  };

  const filteredCredits = credits.filter((c) => {
    if (filter === "all") return true;
    const tier = getQualityTier(c);
    if (filter === "premium")
      return tier.label === "Premium" || tier.label === "High Quality";
    return tier.label === "Standard" || tier.label === "Basic";
  });

  const totalCommunityImpact = credits.reduce(
    (sum, c) => sum + calculateCommunityBenefit(c),
    0,
  );
  const totalCarbon = credits.reduce((sum, c) => sum + c.quantity_tco2e, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header Section */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          Carbon Credit Marketplace
        </h1>
        <p className="text-lg text-gray-600">
          Support conservation efforts while offsetting your carbon footprint.
          Every purchase directly benefits local communities.
        </p>
      </div>

      {/* Impact Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border border-green-200">
          <div className="text-sm font-medium text-green-700 mb-1">
            Available Carbon Credits
          </div>
          <div className="text-3xl font-bold text-green-900">
            {totalCarbon.toFixed(0)}
          </div>
          <div className="text-sm text-green-600 mt-1">tonnes CO₂e</div>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border border-blue-200">
          <div className="text-sm font-medium text-blue-700 mb-1">
            Community Impact Fund
          </div>
          <div className="text-3xl font-bold text-blue-900">
            ${totalCommunityImpact.toFixed(0)}
          </div>
          <div className="text-sm text-blue-600 mt-1">
            60% goes to local communities
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border border-purple-200">
          <div className="text-sm font-medium text-purple-700 mb-1">
            Active Projects
          </div>
          <div className="text-3xl font-bold text-purple-900">
            {credits.length}
          </div>
          <div className="text-sm text-purple-600 mt-1">
            Verified conservation areas
          </div>
        </div>
      </div>

      {/* Checkout Error Banner */}
      {checkoutError && (
        <div className="mb-6 flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 rounded-xl px-5 py-4">
          <svg
            className="w-5 h-5 mt-0.5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div className="flex-1">
            <p className="font-semibold text-sm">Checkout failed</p>
            <p className="text-sm mt-0.5 text-red-600">{checkoutError}</p>
          </div>
          <button
            onClick={() => setCheckoutError(null)}
            className="text-red-400 hover:text-red-600"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <button
          onClick={() => setFilter("all")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            filter === "all"
              ? "border-terra-600 text-terra-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          All Credits ({credits.length})
        </button>
        <button
          onClick={() => setFilter("premium")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            filter === "premium"
              ? "border-terra-600 text-terra-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Premium Quality
        </button>
        <button
          onClick={() => setFilter("standard")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            filter === "standard"
              ? "border-terra-600 text-terra-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Standard
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-terra-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-500">Loading carbon credits...</p>
        </div>
      ) : credits.length === 0 ? (
        <div className="text-center py-16 bg-gray-50 rounded-xl border-2 border-dashed border-gray-300">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
          <h3 className="mt-4 text-lg font-medium text-gray-900">
            No credits available yet
          </h3>
          <p className="mt-2 text-sm text-gray-500">
            Run a land scan to generate and verify carbon credits.
          </p>
          <a
            href="/scan"
            className="mt-4 inline-block bg-terra-600 text-white px-6 py-2 rounded-lg hover:bg-terra-700 transition"
          >
            Start Scanning
          </a>
        </div>
      ) : filteredCredits.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No credits match this filter.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCredits.map((credit) => {
            const tier = getQualityTier(credit);
            const communityBenefit = calculateCommunityBenefit(credit);
            return (
              <div
                key={credit.id}
                className="bg-white rounded-xl border-2 shadow-lg overflow-hidden hover:shadow-xl hover:border-terra-400 transition-all duration-200"
              >
                {/* Header with Quality Badge */}
                <div className="bg-gradient-to-r from-terra-50 to-green-50 p-4 border-b">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`px-2 py-0.5 text-xs font-semibold rounded-full bg-${tier.color}-100 text-${tier.color}-700`}
                        >
                          {tier.label}
                        </span>
                      </div>
                      <h3 className="font-bold text-gray-900 text-lg">
                        {credit.plot_name || `Credit ${credit.id.slice(0, 8)}`}
                      </h3>
                      <p className="text-sm text-gray-600 flex items-center gap-1">
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                          />
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                          />
                        </svg>
                        {credit.region || "Rwanda"} • {credit.vintage_year}
                      </p>
                    </div>
                    <IntegrityBadge score={credit.integrity_score} size="sm" />
                  </div>
                </div>

                <div className="p-5 space-y-4">
                  {/* Carbon & Price */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-green-50 rounded-lg p-3">
                      <div className="text-xs text-green-700 font-medium mb-1">
                        Carbon Offset
                      </div>
                      <div className="text-2xl font-bold text-green-900">
                        {credit.quantity_tco2e.toFixed(1)}
                      </div>
                      <div className="text-xs text-green-600">tonnes CO₂e</div>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-3">
                      <div className="text-xs text-blue-700 font-medium mb-1">
                        Price per Tonne
                      </div>
                      <div className="text-2xl font-bold text-blue-900">
                        ${credit.price_per_tonne.toFixed(2)}
                      </div>
                      <div className="text-xs text-blue-600">USD</div>
                    </div>
                  </div>

                  {/* Community Benefit */}
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <svg
                        className="w-4 h-4 text-purple-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                        />
                      </svg>
                      <span className="text-xs font-semibold text-purple-700">
                        Community Benefit
                      </span>
                    </div>
                    <div className="text-lg font-bold text-purple-900">
                      ${communityBenefit.toFixed(2)}
                    </div>
                    <div className="text-xs text-purple-600">
                      60% goes directly to local communities
                    </div>
                  </div>

                  {/* Risk Score */}
                  <RiskGauge
                    score={credit.risk_score}
                    label="Risk Assessment"
                  />

                  {/* Total Price */}
                  <div className="border-t pt-3">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-sm font-medium text-gray-600">
                        Total Investment
                      </span>
                      <span className="text-2xl font-bold text-gray-900">
                        $
                        {(
                          credit.price_per_tonne * credit.quantity_tco2e
                        ).toFixed(2)}
                      </span>
                    </div>

                    {/* Purchase Button */}
                    {purchased.includes(credit.id) ? (
                      <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-lg p-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <svg
                            className="w-5 h-5 text-green-600"
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
                          <span className="text-green-700 font-bold">
                            Purchased Successfully!
                          </span>
                        </div>
                        <p className="text-xs text-green-600 mt-1">
                          Certificate will be emailed shortly
                        </p>
                      </div>
                    ) : (
                      <button
                        onClick={() => handlePurchase(credit)}
                        disabled={purchasing === credit.id}
                        className="w-full bg-gradient-to-r from-terra-600 to-green-600 text-white py-3 rounded-lg font-bold hover:from-terra-700 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                      >
                        {purchasing === credit.id ? (
                          <>
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                            Processing...
                          </>
                        ) : (
                          <>
                            <svg
                              className="w-5 h-5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
                              />
                            </svg>
                            Purchase Now
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Info Footer */}
      <div className="mt-12 bg-gradient-to-r from-terra-50 to-green-50 rounded-xl p-8 border border-terra-200">
        <div className="grid md:grid-cols-3 gap-8">
          <div>
            <div className="bg-white rounded-lg p-4 inline-block mb-3">
              <svg
                className="w-8 h-8 text-terra-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="font-bold text-gray-900 mb-2">
              Verified & Transparent
            </h3>
            <p className="text-sm text-gray-600">
              Every credit is verified using satellite monitoring and on-ground
              validation. Full transparency in pricing and impact.
            </p>
          </div>
          <div>
            <div className="bg-white rounded-lg p-4 inline-block mb-3">
              <svg
                className="w-8 h-8 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                />
              </svg>
            </div>
            <h3 className="font-bold text-gray-900 mb-2">
              Community-First Approach
            </h3>
            <p className="text-sm text-gray-600">
              60% of every purchase goes directly to local communities managing
              conservation efforts. Empowering sustainable livelihoods.
            </p>
          </div>
          <div>
            <div className="bg-white rounded-lg p-4 inline-block mb-3">
              <svg
                className="w-8 h-8 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="font-bold text-gray-900 mb-2">
              Real Climate Impact
            </h3>
            <p className="text-sm text-gray-600">
              Nature-based carbon sequestration from verified A/R and
              conservation projects in Rwanda — continuously monitored by satellite.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
