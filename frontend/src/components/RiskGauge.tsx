interface RiskGaugeProps {
  score: number;
  label?: string;
}

export default function RiskGauge({ score, label = "Risk" }: RiskGaugeProps) {
  const pct = Math.round(score * 100);

  const { color, bg, labelColor } =
    pct <= 30
      ? { color: "var(--color-risk-low)", bg: "#dcfce7", labelColor: "var(--color-risk-low)" }
      : pct <= 60
      ? { color: "var(--color-risk-medium)", bg: "#fef3c7", labelColor: "var(--color-risk-medium)" }
      : { color: "var(--color-risk-high)", bg: "#fee2e2", labelColor: "var(--color-risk-high)" };

  const tier = pct <= 30 ? "Low" : pct <= 60 ? "Medium" : "High";

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-muted uppercase tracking-wide">{label}</span>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: bg, color: labelColor }}>
          {tier} · {pct}%
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-[var(--color-surface-muted)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}
