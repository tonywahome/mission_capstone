import { NextResponse } from "next/server";

export async function GET() {
  // MAPBOX_TOKEN (no NEXT_PUBLIC_ prefix) is a plain server-side env var —
  // Next.js never inlines it at build time, so it's always read fresh at runtime.
  // NEXT_PUBLIC_MAPBOX_TOKEN is kept as a fallback for local .env.local setups.
  const token =
    process.env.MAPBOX_TOKEN ||
    process.env.NEXT_PUBLIC_MAPBOX_TOKEN ||
    "";

  return NextResponse.json({ mapboxToken: token });
}
