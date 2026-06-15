interface IntegrityBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

export default function IntegrityBadge({ score, size = "md" }: IntegrityBadgeProps) {
  const rounded = Math.round(score);

  const { ring, bg, text, label } =
    score >= 80
      ? { ring: "#15803d", bg: "#f0fdf4", text: "#14532d", label: "High integrity" }
      : score >= 60
      ? { ring: "#c9820a", bg: "#fffbeb", text: "#92400e", label: "Medium integrity" }
      : { ring: "#b42318", bg: "#fef2f2", text: "#7f1d1d", label: "Low integrity" };

  const dim = size === "sm" ? 48 : size === "lg" ? 72 : 60;
  const strokeW = size === "sm" ? 3 : 3.5;
  const r = (dim - strokeW * 2) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={strokeW} />
          <circle
            cx={dim / 2} cy={dim / 2} r={r}
            fill="none"
            stroke={ring}
            strokeWidth={strokeW}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circ}`}
            style={{ transition: "stroke-dasharray 0.6s cubic-bezier(0.22,1,0.36,1)" }}
          />
        </svg>
        <div
          className="absolute inset-0 flex items-center justify-center rounded-full"
          style={{ background: bg }}
        >
          <span
            className="font-bold leading-none"
            style={{
              color: text,
              fontSize: size === "sm" ? 13 : size === "lg" ? 20 : 16,
            }}
          >
            {rounded}
          </span>
        </div>
      </div>
      <span className="text-xs font-medium" style={{ color: text }}>{label}</span>
    </div>
  );
}
