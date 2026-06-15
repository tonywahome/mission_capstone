"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";

interface RegistrationRequest {
  id: string;
  owner_name: string;
  owner_email: string;
  land_location: string;
  land_size: string;
  land_type: string;
  additional_info?: string;
  geometry?: any; // GeoJSON geometry
  status: "pending" | "approved" | "rejected";
  created_at: string;
  processed_at?: string;
  processed_by?: string;
  notes?: string;
}

export default function AdminRegistrationsPage() {
  const [requests, setRequests] = useState<RegistrationRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "approved" | "rejected">("all");
  const [selectedRequest, setSelectedRequest] = useState<RegistrationRequest | null>(null);

  const handleScanWithGeometry = (request: RegistrationRequest) => {
    if (request.geometry) {
      // Store geometry and request info in localStorage for the scan page
      localStorage.setItem("scanGeometry", JSON.stringify(request.geometry));
      localStorage.setItem("scanRequestId", request.id);
      localStorage.setItem("scanOwnerInfo", JSON.stringify({
        name: request.owner_name,
        email: request.owner_email,
        location: request.land_location,
        size: request.land_size,
        type: request.land_type,
      }));
      // Navigate to scan page
      window.location.href = "/scan";
    } else {
      alert("This registration doesn't have geometry data. Please use manual scanning.");
    }
  };

  useEffect(() => {
    fetchRequests();
  }, [filter]);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const url = filter === "all" 
        ? `/api/registration/requests`
        : `/api/registration/requests?status=${filter}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error("Failed to fetch registration requests");
      }
      
      const data = await response.json();
      setRequests(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const baseClasses = "px-3 py-1 rounded-full text-xs font-medium";
    switch (status) {
      case "pending":
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      case "approved":
        return `${baseClasses} bg-green-100 text-green-800`;
      case "rejected":
        return `${baseClasses} bg-red-100 text-red-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <div className="min-h-screen bg-gray-50 pt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Land Registration Requests
            </h1>
            <p className="text-gray-600">
              Review and manage landowner registration requests
            </p>
          </div>

          {/* Filters */}
          <div className="mb-6 flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700">Filter:</span>
            <button
              onClick={() => setFilter("all")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === "all"
                  ? "bg-terra-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-100"
              }`}
            >
              All ({requests.length})
            </button>
            <button
              onClick={() => setFilter("pending")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === "pending"
                  ? "bg-yellow-500 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-100"
              }`}
            >
              Pending
            </button>
            <button
              onClick={() => setFilter("approved")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === "approved"
                  ? "bg-green-500 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-100"
              }`}
            >
              Approved
            </button>
            <button
              onClick={() => setFilter("rejected")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === "rejected"
                  ? "bg-red-500 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-100"
              }`}
            >
              Rejected
            </button>
            <button
              onClick={fetchRequests}
              className="ml-auto px-4 py-2 bg-white text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-100 transition-colors"
            >
              🔄 Refresh
            </button>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-terra-600"></div>
              <p className="mt-4 text-gray-600">Loading requests...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-red-800 font-medium">Error: {error}</p>
              <button
                onClick={fetchRequests}
                className="mt-2 text-sm text-red-600 hover:text-red-700 underline"
              >
                Try again
              </button>
            </div>
          )}

          {/* Requests Table */}
          {!loading && !error && (
            <>
              {requests.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-8 text-center">
                  <p className="text-gray-500 text-lg">No registration requests found</p>
                  <p className="text-gray-400 text-sm mt-2">
                    {filter !== "all" 
                      ? `No ${filter} requests at the moment`
                      : "Landowners can submit requests via the 'Register Land' page"}
                  </p>
                </div>
              ) : (
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Landowner
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Location
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Land Details
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Submitted
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {requests.map((request) => (
                          <tr key={request.id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div>
                                <div className="text-sm font-medium text-gray-900">
                                  {request.owner_name}
                                </div>
                                <div className="text-sm text-gray-500">
                                  {request.owner_email}
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="text-sm text-gray-900">
                                {request.land_location}
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="text-sm text-gray-900">
                                {request.land_size} hectares
                              </div>
                              <div className="text-sm text-gray-500 capitalize">
                                {request.land_type}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={getStatusBadge(request.status)}>
                                {request.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {formatDate(request.created_at)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm space-x-3">
                              <button
                                onClick={() => setSelectedRequest(request)}
                                className="text-terra-600 hover:text-terra-700 font-medium"
                              >
                                View Details
                              </button>
                              {request.status === "pending" && (
                                <>
                                  {request.geometry ? (
                                    <button
                                      onClick={() => handleScanWithGeometry(request)}
                                      className="text-blue-600 hover:text-blue-700 font-medium"
                                    >
                                      🛰️ Auto Scan
                                    </button>
                                  ) : (
                                    <Link
                                      href="/scan"
                                      className="text-blue-600 hover:text-blue-700 font-medium"
                                    >
                                      🛰️ Manual Scan
                                    </Link>
                                  )}
                                </>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Detail Modal */}
        {selectedRequest && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex justify-between items-start mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">
                    Registration Request Details
                  </h2>
                  <button
                    onClick={() => setSelectedRequest(null)}
                    className="text-gray-400 hover:text-gray-600 text-2xl"
                  >
                    ×
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Request ID</h3>
                    <p className="text-sm text-gray-900 font-mono">{selectedRequest.id}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Landowner Name</h3>
                      <p className="text-sm text-gray-900">{selectedRequest.owner_name}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Email</h3>
                      <p className="text-sm text-gray-900">{selectedRequest.owner_email}</p>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Land Location</h3>
                    <p className="text-sm text-gray-900">{selectedRequest.land_location}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Land Size</h3>
                      <p className="text-sm text-gray-900">{selectedRequest.land_size} hectares</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Land Type</h3>
                      <p className="text-sm text-gray-900 capitalize">{selectedRequest.land_type}</p>
                    </div>
                  </div>

                  {selectedRequest.additional_info && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Additional Information</h3>
                      <p className="text-sm text-gray-900 whitespace-pre-wrap">
                        {selectedRequest.additional_info}
                      </p>
                    </div>
                  )}

                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Status</h3>
                    <span className={getStatusBadge(selectedRequest.status)}>
                      {selectedRequest.status}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Submitted At</h3>
                    <p className="text-sm text-gray-900">{formatDate(selectedRequest.created_at)}</p>
                  </div>

                  {selectedRequest.processed_at && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Processed At</h3>
                      <p className="text-sm text-gray-900">{formatDate(selectedRequest.processed_at)}</p>
                    </div>
                  )}

                  {selectedRequest.notes && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Admin Notes</h3>
                      <p className="text-sm text-gray-900 whitespace-pre-wrap">
                        {selectedRequest.notes}
                      </p>
                    </div>
                  )}

                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Land Boundary</h3>
                    {selectedRequest.geometry ? (
                      <div className="flex items-center space-x-2">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✓ Geometry Available
                        </span>
                        <span className="text-xs text-gray-500">
                          Ready for automatic scanning
                        </span>
                      </div>
                    ) : (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        Manual Drawing Required
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-6 flex justify-between">
                  <div>
                    {selectedRequest.status === "pending" && (
                      <>
                        {selectedRequest.geometry ? (
                          <button
                            onClick={() => handleScanWithGeometry(selectedRequest)}
                            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center space-x-2 font-medium"
                          >
                            <span>🛰️</span>
                            <span>Auto Scan with Boundary</span>
                          </button>
                        ) : (
                          <Link
                            href="/scan"
                            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center space-x-2 font-medium"
                          >
                            <span>🛰️</span>
                            <span>Manual Scan (Draw Boundary)</span>
                          </Link>
                        )}
                      </>
                    )}
                  </div>
                  <div className="flex space-x-3">
                    {selectedRequest.status === "pending" && (
                      <>
                        <button
                          onClick={() => {
                            // TODO: Implement approve functionality
                            alert("Approve functionality coming soon");
                          }}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                        >
                          ✓ Approve
                        </button>
                        <button
                          onClick={() => {
                            // TODO: Implement reject functionality
                            alert("Reject functionality coming soon");
                          }}
                          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                        >
                          ✗ Reject
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => setSelectedRequest(null)}
                      className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
