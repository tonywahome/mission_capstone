export function formatNumber(n: number, decimals = 1): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(decimals)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(decimals)}K`;
  return n.toFixed(decimals);
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "verified":
      return "bg-blue-100 text-blue-800";
    case "listed":
      return "bg-yellow-100 text-yellow-800";
    case "sold":
      return "bg-green-100 text-green-800";
    case "retired":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-600";
  }
}

export function getIntegrityColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

export function getIntegrityLabel(score: number): string {
  if (score >= 80) return "High";
  if (score >= 60) return "Medium";
  return "Low";
}
