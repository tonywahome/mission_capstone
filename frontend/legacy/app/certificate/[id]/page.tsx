"use client";

import { useParams } from "next/navigation";
import { api } from "@/lib/api";

export default function CertificatePage() {
  const params = useParams();
  const txId = params.id as string;
  const downloadUrl = api.getCertificateURL(txId);

  return (
    <div className="max-w-2xl mx-auto px-4 py-16 text-center">
      <div className="bg-white rounded-xl border shadow-sm p-8">
        <div className="w-16 h-16 bg-terra-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-3xl">📜</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Carbon Offset Certificate
        </h1>
        <p className="text-gray-500 mb-6">
          Transaction: {txId.slice(0, 8)}...
        </p>

        <div className="bg-terra-50 rounded-lg p-6 mb-6">
          <div className="inline-block bg-terra-600 text-white px-4 py-1.5 rounded-full text-sm font-semibold mb-3">
            TerraFoma Verified
          </div>
          <p className="text-terra-800 text-sm">
            This certificate confirms that the carbon credits associated with
            this transaction have been verified through our AI-powered dMRV
            platform and have been officially retired.
          </p>
        </div>

        <a
          href={downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block bg-terra-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-terra-700 transition"
        >
          Download PDF Certificate
        </a>
      </div>
    </div>
  );
}
