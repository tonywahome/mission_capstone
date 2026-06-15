"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { useState, useEffect } from "react";

export default function Navbar() {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const { user, logout, isAuthenticated, loading } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    if (!isHome) return;
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [isHome]);

  // Close menu on route change
  useEffect(() => {
    setShowUserMenu(false);
  }, [pathname]);

  const getLinks = () => {
    if (!user) return [{ href: "/", label: "Home" }];

    const base = [
      { href: "/", label: "Home" },
      { href: "/registry", label: "Registry" },
      { href: "/marketplace", label: "Marketplace" },
    ];

    if (user.role === "landowner")
      return [...base, { href: "/landowner", label: "Dashboard" }, { href: "/landowner/pending-scans", label: "Pending scans" }, { href: "/request-registration", label: "Register site" }];
    if (user.role === "business")
      return [...base, { href: "/dashboard", label: "Dashboard" }];
    if (user.role === "admin")
      return [...base, { href: "/admin/requests", label: "Registrations" }, { href: "/scan", label: "Scan" }, { href: "/admin/dashboard", label: "Console" }];

    return base;
  };

  const links = getLinks();

  const navBg = isHome
    ? scrolled
      ? "bg-white/90 backdrop-blur-md shadow-sm border-b border-[var(--color-border)]"
      : "bg-transparent"
    : "bg-white border-b border-[var(--color-border)] shadow-sm";

  const linkBase = "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-muted)]";

  const linkActive = isHome
    ? scrolled
      ? "bg-[var(--color-surface-muted)] text-[var(--color-text-primary)] font-semibold"
      : "bg-white/15 text-white font-semibold"
    : "bg-[var(--color-surface-muted)] text-[var(--color-text-primary)] font-semibold";

  const handleLogout = () => {
    setShowUserMenu(false);
    logout();
  };

  return (
    <>
      {/* Transparent backdrop — clicking outside the dropdown closes it */}
      {showUserMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowUserMenu(false)}
        />
      )}

      <nav className={`top-0 z-50 w-full transition-all duration-300 ${isHome ? "fixed" : "sticky"} ${navBg}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">

            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 group">
              <Image
                src="/logo.png"
                alt="TerraFoma"
                width={100}
                height={100}
                className="object-contain transition-opacity group-hover:opacity-80"
              />
              <span className={`text-lg font-bold tracking-tight transition-colors ${
                isHome ? "text-white drop-shadow" : "text-[var(--color-text-primary)]"
              }`}>
                TerraFoma
              </span>
            </Link>

            {/* Links */}
            <div className="hidden md:flex items-center gap-0.5">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    pathname === link.href ? linkActive : linkBase
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            {/* Auth section */}
            {!loading && (
              <div className="flex items-center gap-2">
                {isAuthenticated && user ? (
                  <div className="relative z-50">
                    <button
                      onClick={() => setShowUserMenu((v) => !v)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                        isHome
                          ? "text-white/90 hover:bg-white/10 border border-white/20"
                          : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)] border border-[var(--color-border)]"
                      }`}
                    >
                      <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold bg-terra-700 text-white">
                        {user.full_name.charAt(0).toUpperCase()}
                      </div>
                      <span className="hidden sm:block">{user.full_name.split(" ")[0]}</span>
                      <svg
                        className={`w-3.5 h-3.5 transition-transform duration-200 ${showUserMenu ? "rotate-180" : ""}`}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    {showUserMenu && (
                      <div className="absolute right-0 mt-2 w-60 rounded-2xl shadow-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] overflow-hidden animate-scale-in">
                        <div className="px-4 py-3 bg-[var(--color-surface-muted)] border-b border-[var(--color-border)]">
                          <p className="text-sm font-semibold text-[var(--color-text-primary)]">{user.full_name}</p>
                          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{user.email}</p>
                          <span className="inline-block mt-2 px-2.5 py-0.5 text-xs font-semibold rounded-full bg-terra-700 text-white">
                            {user.role === "landowner"
                              ? "Project operator"
                              : user.role === "admin"
                              ? "Platform admin"
                              : "Credit buyer"}
                          </span>
                        </div>
                        <div className="p-2">
                          <button
                            onClick={handleLogout}
                            className="w-full text-left px-3 py-2 text-sm font-medium rounded-lg text-red-600 transition-colors hover:bg-red-50"
                          >
                            Sign out
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Link
                      href="/login"
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        isHome
                          ? "text-white/90 hover:bg-white/10"
                          : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)]"
                      }`}
                    >
                      Sign in
                    </Link>
                    <Link
                      href="/signup"
                      className="px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-sm bg-terra-700 text-white hover:bg-terra-800"
                    >
                      Get access
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </nav>
    </>
  );
}
