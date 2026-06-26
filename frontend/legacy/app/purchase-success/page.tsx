"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

interface PaymentResult {
  transactionId: string;
  creditName: string;
  quantityTco2e: number;
  totalPrice: number;
}

function SuccessContent() {
  const searchParams = useSearchParams();
  const checkoutId = searchParams.get("checkout_id");

  const [state, setState] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [result, setResult] = useState<PaymentResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (!checkoutId) {
      setErrorMsg(
        "No checkout ID found. Please contact support if you completed a payment.",
      );
      setState("error");
      return;
    }

    fetch(`/api/confirm-payment?checkout_id=${encodeURIComponent(checkoutId)}`)
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok)
          throw new Error(data.error ?? "Payment confirmation failed");
        return data;
      })
      .then((data: PaymentResult) => {
        setResult(data);
        setState("success");
      })
      .catch((err: Error) => {
        setErrorMsg(err.message);
        setState("error");
      });
  }, [checkoutId]);

  if (state === "loading") {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="bg-white rounded-2xl border shadow-sm p-12">
          <div className="inline-block h-14 w-14 animate-spin rounded-full border-4 border-solid border-terra-600 border-r-transparent mb-6" />
          <h1 className="text-2xl font-bold text-gray-800 mb-2">
            Confirming your payment...
          </h1>
          <p className="text-gray-500 text-sm">
            Please wait while we verify your purchase and issue your carbon
            offset certificate.
          </p>
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="bg-white rounded-2xl border border-red-200 shadow-sm p-12">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-gray-800 mb-2">
            Payment Confirmation Failed
          </h1>
          <p className="text-red-600 text-sm bg-red-50 rounded-lg px-4 py-3 mb-6">
            {errorMsg}
          </p>
          <p className="text-gray-500 text-xs mb-6">
            If you were charged, please contact support with your checkout ID:{" "}
            <span className="font-mono text-gray-700">{checkoutId ?? "—"}</span>
          </p>
          <Link
            href="/marketplace"
            className="inline-block bg-terra-600 text-white px-6 py-2.5 rounded-lg font-semibold hover:bg-terra-700 transition"
          >
            Back to Marketplace
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <div className="bg-white rounded-2xl border border-green-200 shadow-lg overflow-hidden">
        {/* Green top bar */}
        <div className="bg-gradient-to-r from-green-500 to-emerald-600 h-2" />

        <div className="p-10 text-center">
          {/* Success checkmark */}
          <div className="w-20 h-20 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
            <svg
              className="w-10 h-10 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Purchase Complete!
          </h1>
          <p className="text-gray-500 mb-8">
            Your carbon credit has been purchased, verified, and retired on your
            behalf.
          </p>

          {/* Purchase summary */}
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-6 mb-8 text-left space-y-3">
            <h2 className="text-sm font-bold text-green-800 uppercase tracking-wide mb-3">
              Purchase Summary
            </h2>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Credit</span>
              <span className="text-sm font-semibold text-gray-800 max-w-xs text-right">
                {result?.creditName}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Carbon Offset</span>
              <span className="text-sm font-bold text-green-700">
                {result?.quantityTco2e.toFixed(2)} tCO₂e
              </span>
            </div>
            <div className="flex justify-between items-center border-t border-green-200 pt-3 mt-3">
              <span className="text-sm font-bold text-gray-700">
                Total Paid
              </span>
              <span className="text-lg font-bold text-gray-900">
                ${result?.totalPrice.toFixed(2)}{" "}
                <span className="text-sm font-normal text-gray-500">USD</span>
              </span>
            </div>
          </div>

          {/* Certificate section */}
          <div className="bg-terra-50 border border-terra-200 rounded-xl p-6 mb-8">
            <div className="inline-block bg-terra-600 text-white px-3 py-1 rounded-full text-xs font-semibold mb-3">
              TerraFoma Verified
            </div>
            <p className="text-terra-800 text-sm mb-5 leading-relaxed">
              Your carbon offset certificate confirms this credit has been
              independently verified by our AI-powered dMRV platform using
              satellite monitoring. Download it as a PDF for your records or
              compliance reporting.
            </p>
            <Link
              href={`/certificate/${result?.transactionId}`}
              className="inline-flex items-center gap-2 bg-terra-600 text-white px-8 py-3 rounded-lg font-bold hover:bg-terra-700 transition shadow-md hover:shadow-lg"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
              Download Certificate
            </Link>
          </div>

          {/* Transaction reference */}
          <p className="text-xs text-gray-400 mb-6">
            Transaction reference:{" "}
            <span className="font-mono text-gray-600">
              {result?.transactionId?.slice(0, 8)}...
            </span>
          </p>

          <div className="flex items-center justify-center gap-6">
            <Link
              href="/marketplace"
              className="text-sm text-gray-400 hover:text-gray-600 transition"
            >
              Back to Marketplace
            </Link>
            <span className="text-gray-300">|</span>
            <Link
              href="/registry"
              className="text-sm text-gray-400 hover:text-gray-600 transition"
            >
              View Registry
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PurchaseSuccessPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-xl mx-auto px-4 py-20 text-center">
          <div className="bg-white rounded-2xl border shadow-sm p-12">
            <div className="inline-block h-14 w-14 animate-spin rounded-full border-4 border-solid border-terra-600 border-r-transparent mx-auto" />
          </div>
        </div>
      }
    >
      <SuccessContent />
    </Suspense>
  );
}
