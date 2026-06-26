"use client";

// Capstone re-scope note: this previously called api.getCreditStats() →
// GET /api/credits/stats, served by backend/legacy/routers/credits.py —
// a router that is no longer mounted in backend/main.py (see
// backend/legacy/README.md). The call was silently swallowed by a
// .catch(() => {}), so the public landing page always rendered placeholder
// dashes rather than surfacing the failure. Replaced with static,
// proposal-accurate figures rather than wiring up a new live aggregate-
// stats endpoint, since "credits/price/integrity" framing is marketplace
// language this capstone is explicitly out of scope for (see README
// "Project Scope"). If a future live research-summary endpoint is added,
// these can become dynamic again.

export default function StatsBar({ glassy = false }: { glassy?: boolean }) {
  const items = [
    { label: "Validation districts", value: "Bugesera · Rulindo", icon: "📍" },
    { label: "Sensors fused", value: "S1 · S2 · GEDI", icon: "🛰️" },
    { label: "Target RMSE reduction", value: "≥ 40%", icon: "📉" },
    { label: "Roles", value: "Steward · Analyst · Admin", icon: "🛡️" },
  ];

  return (
    <div className={glassy
      ? "relative bg-black/30 backdrop-blur-md border-t border-white/10 text-white py-5"
      : "bg-terra-800 text-white py-5"
    }>
      <div className="max-w-7xl mx-auto px-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-0 md:divide-x md:divide-white/10">
          {items.map((item, i) => (
            <div key={item.label} className={`text-center px-4 ${i > 0 ? "md:border-l-0" : ""}`}>
              <div className="text-2xl font-bold tracking-tight">{item.value}</div>
              <div className={`text-xs mt-0.5 uppercase tracking-wider font-medium ${
                glassy ? "text-white/60" : "text-terra-300"
              }`}>
                {item.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
