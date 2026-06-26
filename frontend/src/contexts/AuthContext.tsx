"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

// Roles per the revised capstone proposal (Section 3.4 class diagram):
//   steward          — registers projects, uploads field/scan data
//   verifier_analyst — reviews submitted scans, confirms/flags for the audit trail
//   research_admin   — exclusive access to full-precision (unrounded) data
export type UserRole = "steward" | "verifier_analyst" | "research_admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  company_name?: string;
  precise_location_consent?: boolean;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (data: SignupData) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

interface SignupData {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  company_name?: string;
  precise_location_consent?: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session in localStorage
    const storedUser = localStorage.getItem("terrafoma_user");
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (error) {
        console.error("Failed to parse stored user:", error);
        localStorage.removeItem("terrafoma_user");
      }
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch(`/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: "Login failed",
        }));
        throw new Error(error.detail || "Invalid credentials");
      }

      const data = await response.json();
      setUser(data.user);
      localStorage.setItem("terrafoma_user", JSON.stringify(data.user));
      localStorage.setItem("terrafoma_token", data.token);
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    }
  };

  const signup = async (data: SignupData) => {
    try {
      const response = await fetch(`/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: "Signup failed",
        }));
        throw new Error(error.detail || "Failed to create account");
      }

      const result = await response.json();
      setUser(result.user);
      localStorage.setItem("terrafoma_user", JSON.stringify(result.user));
      localStorage.setItem("terrafoma_token", result.token);
    } catch (error) {
      console.error("Signup error:", error);
      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("terrafoma_user");
    localStorage.removeItem("terrafoma_token");
    window.location.href = "/";
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
