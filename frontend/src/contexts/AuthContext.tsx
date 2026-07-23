"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";

// Roles per the revised capstone proposal (Section 3.4 class diagram):
//   steward        — registers projects, uploads field/scan data
//   analyst        — reviews submitted scans, confirms/flags for the audit trail
//   research_admin — exclusive access to full-precision (unrounded) data
export type UserRole = "steward" | "analyst" | "research_admin";

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
  // true right after signUp() until the confirmation email is clicked —
  // lets the signup page show a "check your email" state instead of
  // assuming an immediately logged-in user.
  pendingConfirmation: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (data: SignupData) => Promise<void>;
  logout: () => Promise<void>;
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
  const [pendingConfirmation, setPendingConfirmation] = useState(false);

  const loadProfile = async (accessToken: string) => {
    const res = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) return null;
    return (await res.json()) as User;
  };

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (session && mounted) {
        const profile = await loadProfile(session.access_token);
        if (mounted) setUser(profile);
      }
      if (mounted) setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (session) {
          const profile = await loadProfile(session.access_token);
          setUser(profile);
        } else {
          setUser(null);
        }
      }
    );

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const login = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message);
  };

  const signup = async (data: SignupData) => {
    const { data: signUpData, error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
    });
    if (error) throw new Error(error.message);

    const session = signUpData.session;
    if (!session) {
      // Email confirmation is required and no session was issued yet.
      setPendingConfirmation(true);
      return;
    }

    const res = await fetch("/api/auth/set-role", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        role: data.role,
        full_name: data.full_name,
        company_name: data.company_name,
        precise_location_consent: data.precise_location_consent,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to assign role" }));
      throw new Error(err.detail || "Failed to assign role");
    }

    // A session already existed (email confirmation is off on this
    // project), and set-role just succeeded — the user is already logged
    // in, so set them directly instead of telling them to check email.
    const profile = await res.json();
    setUser({
      id: profile.id,
      email: profile.email,
      full_name: profile.full_name,
      role: profile.role,
      company_name: profile.company_name,
      precise_location_consent: profile.precise_location_consent,
      created_at: profile.created_at,
    });
  };

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
    window.location.href = "/";
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        pendingConfirmation,
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
