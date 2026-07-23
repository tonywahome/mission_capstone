"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");

    if (!code) {
      setError("No confirmation code found in the link.");
      return;
    }

    supabase.auth.exchangeCodeForSession(code).then(({ error }) => {
      if (error) {
        setError(error.message);
        return;
      }
      router.push("/");
    });
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-terra-50 to-green-50">
      <div className="text-center">
        {error ? (
          <>
            <p className="text-red-700 font-semibold mb-2">
              Couldn&apos;t confirm your account
            </p>
            <p className="text-sm text-gray-600">{error}</p>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-terra-600 mx-auto mb-4" />
            <p className="text-gray-600">Confirming your account…</p>
          </>
        )}
      </div>
    </div>
  );
}
