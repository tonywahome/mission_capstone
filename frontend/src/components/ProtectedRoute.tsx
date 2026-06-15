"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth, UserRole } from "@/contexts/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
  requireAuth?: boolean;
}

export default function ProtectedRoute({
  children,
  allowedRoles,
  requireAuth = true,
}: ProtectedRouteProps) {
  const router = useRouter();
  const { user, loading, isAuthenticated } = useAuth();

  useEffect(() => {
    if (loading) return;

    // Require authentication
    if (requireAuth && !isAuthenticated) {
      router.push("/login");
      return;
    }

    // Check role permissions
    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
      // Redirect to appropriate page based on role
      if (user.role === "landowner") {
        router.push("/scan");
      } else if (user.role === "business") {
        router.push("/dashboard");
      } else {
        router.push("/");
      }
    }
  }, [loading, isAuthenticated, user, requireAuth, allowedRoles, router]);

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-terra-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show nothing while redirecting
  if (requireAuth && !isAuthenticated) {
    return null;
  }

  // Check role authorization
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}
