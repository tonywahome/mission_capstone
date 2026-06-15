"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CreditStats } from "@/lib/types";

export default function StatsBar({ glassy = false }: { glassy?: boolean }) {
  const [stats, setStats] = useState<CreditStats | null>(null);

  useEffect(() => {
    api.getCreditStats().then((data) => setStats(data as CreditStats)).catch(() => {});
  }, []);

  const items = stats
    ? [
        { label: "Credits verified", value: stats.total_credits.toLocaleString(), icon: "✓" },
        { label: "tCO₂e offset", value: Number(stats.total_tco2e.toFixed(0)).toLocaleString(), icon: "🌿" },
        { label: "Avg integrity", value: `${stats.avg_integrity.toFixed(0)}/100`, icon: "◎" },
        { label: "Avg price", value: `$${stats.avg_price.toFixed(2)}/t`, icon: "◈" },
      ]
    : [
        { label: "Credits verified", value: "—", icon: "✓" },
        { label: "tCO₂e offset", value: "—", icon: "🌿" },
        { label: "Avg integrity", value: "—", icon: "◎" },
        { label: "Avg price", value: "—", icon: "◈" },
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
