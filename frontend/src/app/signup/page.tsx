"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useAuth, UserRole } from "@/contexts/AuthContext";

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
    role: "steward" as UserRole,
    company_name: "",
    precise_location_consent: false,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await signup(formData);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-terra-50 to-green-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex justify-center">
            <Image src="/logo.png" alt="TerraFoma" width={120} height={120} className="object-contain" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Join the TerraFoma biomass-monitoring research prototype
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="bg-white rounded-2xl shadow-lg p-8 space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            {/* Account Type Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                I am a...
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, role: "steward" })
                  }
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    formData.role === "steward"
                      ? "border-terra-600 bg-terra-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="text-2xl mb-2">🌳</div>
                  <div className="font-semibold text-sm">Land Steward</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Register projects, upload field data
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, role: "verifier_analyst" })
                  }
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    formData.role === "verifier_analyst"
                      ? "border-terra-600 bg-terra-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="text-2xl mb-2">🔎</div>
                  <div className="font-semibold text-sm">Verifier / Analyst</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Review scans for the audit trail
                  </div>
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor="full_name"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Full Name
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                required
                value={formData.full_name}
                onChange={(e) =>
                  setFormData({ ...formData, full_name: e.target.value })
                }
                className="appearance-none relative block w-full px-4 py-3 border border-gray-300 rounded-lg placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-2 focus:ring-terra-500 focus:border-transparent"
                placeholder="John Doe"
              />
            </div>

            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                className="appearance-none relative block w-full px-4 py-3 border border-gray-300 rounded-lg placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-2 focus:ring-terra-500 focus:border-transparent"
                placeholder="you@example.com"
              />
            </div>

            {formData.role === "verifier_analyst" && (
              <div>
                <label
                  htmlFor="company_name"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Organization (Optional)
                </label>
                <input
                  id="company_name"
                  name="company_name"
                  type="text"
                  value={formData.company_name}
                  onChange={(e) =>
                    setFormData({ ...formData, company_name: e.target.value })
                  }
                  className="appearance-none relative block w-full px-4 py-3 border border-gray-300 rounded-lg placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-2 focus:ring-terra-500 focus:border-transparent"
                  placeholder="Your Company"
                />
              </div>
            )}

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
                className="appearance-none relative block w-full px-4 py-3 border border-gray-300 rounded-lg placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-2 focus:ring-terra-500 focus:border-transparent"
                placeholder="••••••••"
              />
              <p className="mt-1 text-xs text-gray-500">
                Must be at least 8 characters
              </p>
            </div>

            {formData.role === "steward" && (
              <div className="flex items-start gap-2">
                <input
                  id="precise_location_consent"
                  type="checkbox"
                  checked={formData.precise_location_consent}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      precise_location_consent: e.target.checked,
                    })
                  }
                  className="mt-1 h-4 w-4 rounded border-gray-300 text-terra-600 focus:ring-terra-500"
                />
                <label
                  htmlFor="precise_location_consent"
                  className="text-xs text-gray-600"
                >
                  I consent to TerraFoma storing the precise (unrounded) GPS
                  coordinates of my project for research purposes. Without
                  this consent, only coordinates rounded to ~100m are stored
                  outside of Research-Administrator access (see Section 3.6
                  of the research proposal).
                </label>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-gradient-to-r from-terra-600 to-terra-700 hover:from-terra-700 hover:to-terra-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-terra-500 disabled:opacity-50 transition-all"
            >
              {loading ? "Creating account..." : "Create account"}
            </button>
          </div>
        </form>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-semibold text-terra-600 hover:text-terra-700"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
