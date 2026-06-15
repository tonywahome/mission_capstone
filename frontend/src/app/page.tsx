"use client";

import Image from "next/image";
import Link from "next/link";
import StatsBar from "@/components/StatsBar";
import HeroVideo from "@/components/HeroVideo";
import { useAuth } from "@/contexts/AuthContext";

export default function Home() {
  const { user, isAuthenticated } = useAuth();

  return (
    <div>
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="relative text-white overflow-hidden min-h-screen flex flex-col">
        <HeroVideo />

        <div className="relative flex-1 flex flex-col justify-center">
          <div className="max-w-6xl mx-auto px-4 pt-24 pb-16 text-center">

            <div className="animate-fade-up inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 text-white/90 text-xs font-semibold uppercase tracking-widest mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
              Rwanda · Continuous dMRV · A/R projects
            </div>

            <h1 className="animate-fade-up text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.07] tracking-tight drop-shadow-xl">
              Measurement you
              <br />
              <span className="text-terra-300">can audit.</span>
            </h1>

            <p className="animate-fade-up-delay-1 text-lg md:text-xl text-white/80 mt-7 max-w-2xl mx-auto leading-relaxed drop-shadow">
              Rwanda's continuous, satellite-driven Monitoring, Reporting and
              Verification platform for green projects
            </p>

            {!isAuthenticated ? (
              <div className="animate-fade-up-delay-2 mt-10 flex flex-col sm:flex-row gap-3 justify-center items-center">
                <Link
                  href="/signup"
                  className="rounded-xl bg-white text-terra-800 px-7 py-3.5 text-sm font-bold hover:bg-terra-50 transition-all shadow-xl hover:-translate-y-0.5"
                >
                  Request operator access
                </Link>
                <Link
                  href="/marketplace"
                  className="rounded-xl border border-white/40 bg-white/10 backdrop-blur-sm text-white px-7 py-3.5 text-sm font-semibold hover:bg-white/20 transition-all"
                >
                  Browse verified credits
                </Link>
                <Link
                  href="/registry"
                  className="rounded-xl border border-white/25 bg-white/5 backdrop-blur-sm text-white/80 px-7 py-3.5 text-sm font-medium hover:bg-white/15 hover:text-white transition-all"
                >
                  View public registry
                </Link>
              </div>
            ) : (
              <div className="animate-fade-up-delay-2 mt-10 flex flex-col sm:flex-row gap-3 justify-center">
                {user?.role === "landowner" ? (
                  <Link href="/landowner" className="rounded-xl bg-white text-terra-800 px-7 py-3.5 text-sm font-bold hover:bg-terra-50 shadow-xl hover:-translate-y-0.5 transition-all">
                    Go to monitoring desk
                  </Link>
                ) : user?.role === "admin" ? (
                  <Link href="/admin/dashboard" className="rounded-xl bg-white text-terra-800 px-7 py-3.5 text-sm font-bold hover:bg-terra-50 shadow-xl hover:-translate-y-0.5 transition-all">
                    Open admin console
                  </Link>
                ) : (
                  <Link href="/dashboard" className="rounded-xl bg-white text-terra-800 px-7 py-3.5 text-sm font-bold hover:bg-terra-50 shadow-xl hover:-translate-y-0.5 transition-all">
                    Buyer dashboard
                  </Link>
                )}
                <Link href="/marketplace" className="rounded-xl border border-white/40 bg-white/10 backdrop-blur-sm text-white px-7 py-3.5 text-sm font-semibold hover:bg-white/20 transition-all">
                  Credit registry
                </Link>
              </div>
            )}
          </div>
        </div>

        <StatsBar glassy />
      </section>

      {/* ── How it works ─────────────────────────────────────── */}
      <section className="relative py-24 overflow-hidden">
        <div className="absolute inset-0">
          <Image src="/forest-bg.jpg" alt="Rwanda forest" fill className="object-cover" />
          <div className="absolute inset-0 bg-gradient-to-b from-black/75 via-black/65 to-black/75" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4">
          <div className="text-center mb-14">
            <p className="text-xs uppercase tracking-[0.3em] text-terra-300 font-semibold">
              How TerraFoma works
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mt-3 text-white tracking-tight">
              Continuous dMRV, built for Rwanda
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <Pillar
              step="01"
              title="Multi-sensor fusion"
              body="Sentinel-2 optical and Sentinel-1 radar composites fused with NASA GEDI spaceborne LiDAR feed an XGBoost biomass model locally calibrated on Rwandan A/R sites — achieving ≥74% RMSE reduction over global products."
            />
            <Pillar
              step="02"
              title="Scientific additionality"
              body="SparseSC synthetic controls and BFAST breakpoint tests separate project signal from landscape trend before any VER is issued — aligned with ICVCM Core Carbon Principles."
            />
            <Pillar
              step="03"
              title="Auditable registry"
              body="Every verified emission reduction carries its integrity score, permanence risk, buffer discount, and retirement state in a public ledger — traceable from pixel to certificate."
            />
          </div>
        </div>
      </section>

      {/* ── Who it's for ──────────────────────────────────────── */}
      <section className="py-24 bg-[var(--color-surface-subtle)]">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-14">
            <p className="text-xs uppercase tracking-[0.3em] text-terra-700 font-semibold">
              Three roles, one source of truth
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mt-3 text-primary tracking-tight">
              Who TerraFoma is built for
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <RoleCard
              icon="🌱"
              title="Project operators"
              body="Register A/R sites, track site health, and request VER issuance once monitoring thresholds are met."
              cta="Request operator access"
              href="/signup"
              accent
            />
            <RoleCard
              icon="🏛️"
              title="Government of Rwanda"
              body="Aggregate national A/R portfolio signals for REMA reporting and NDC progress tracking against the 38% GHG reduction target by 2030."
              cta="View public registry"
              href="/registry"
            />
            <RoleCard
              icon="📊"
              title="Credit buyers"
              body="Procure verified emission reductions with full provenance — backed by continuous satellite monitoring, not annual attestations."
              cta="Browse credits"
              href="/marketplace"
            />
          </div>
        </div>
      </section>

      {/* ── Trust strip ──────────────────────────────────────── */}
      <section className="py-14 bg-[var(--color-surface-muted)] border-t border-[var(--color-border)]">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-xs uppercase tracking-[0.3em] text-terra-700 font-semibold mb-6">
            Built on open science
          </p>
          <div className="flex flex-wrap justify-center gap-x-10 gap-y-3">
            {["Sentinel-1 · ESA", "Sentinel-2 · ESA", "GEDI · NASA", "GHG Protocol", "Verra VCS", "ICVCM Core Carbon Principles", "Rwanda NDC 2030"].map((item) => (
              <span key={item} className="text-sm text-slate-600 font-medium">{item}</span>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function Pillar({ step, title, body }: { step: string; title: string; body: string }) {
  return (
    <div className="rounded-2xl p-7 border border-white/15 bg-white/8 backdrop-blur-sm hover:bg-white/12 hover:border-white/25 transition-all duration-300">
      <div className="text-xs font-bold text-terra-300 tracking-widest mb-3">{step}</div>
      <h3 className="text-lg font-bold text-white mb-3">{title}</h3>
      <p className="text-sm text-white/70 leading-relaxed">{body}</p>
    </div>
  );
}

function RoleCard({
  icon,
  title,
  body,
  cta,
  href,
  accent = false,
}: {
  icon: string;
  title: string;
  body: string;
  cta: string;
  href: string;
  accent?: boolean;
}) {
  return (
    <div className={`group rounded-2xl border p-7 transition-all duration-300 hover:-translate-y-1 hover:shadow-card-hover ${
      accent
        ? "border-terra-200 bg-terra-50 hover:border-terra-300"
        : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-terra-300"
    }`}>
      <div className="text-3xl mb-4">{icon}</div>
      <h3 className="text-lg font-bold text-primary mb-2">{title}</h3>
      <p className="text-sm text-secondary leading-relaxed mb-5">{body}</p>
      <Link
        href={href}
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-terra-700 hover:text-terra-800 transition-all"
      >
        {cta} →
      </Link>
    </div>
  );
}
