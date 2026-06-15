"use client";

import { useState, useEffect } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api } from "@/lib/api";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import Link from "next/link";

interface AdminStats {
  registrationRequests: {
    total: number;
    pending: number;
    approved: number;
    rejected: number;
  };
  scans: {
    total: number;
    completed: number;
    pending: number;
  };
  credits: {
    total: number;
    pending_approval: number;
    listed: number;
    sold: number;
    retired: number;
    total_tco2e: number;
  };
  users: {
    total: number;
    landowners: number;
    businesses: number;
    admins: number;
  };
}

export default function AdminDashboardPage() {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <AdminDashboardContent />
    </ProtectedRoute>
  );
}

function AdminDashboardContent() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Fetch registration requests
      const requests = await fetch(`/api/registration/requests`).then(r => r.json());
      
      // Fetch credit stats
      const creditStats: any = await api.getCreditStats();

      // Build admin stats
      const adminStats: AdminStats = {
        registrationRequests: {
          total: requests.length,
          pending: requests.filter((r: any) => r.status === "pending").length,
          approved: requests.filter((r: any) => r.status === "approved").length,
          rejected: requests.filter((r: any) => r.status === "rejected").length,
        },
        scans: {
          total: 0,
          completed: 0,
          pending: 0,
        },
        credits: {
          total: creditStats.total_credits || 0,
          pending_approval: creditStats.total_pending_approval || 0,
          listed: creditStats.total_listed || 0,
          sold: creditStats.total_sold || 0,
          retired: creditStats.total_retired || 0,
          total_tco2e: creditStats.total_tco2e || 0,
        },
        users: {
          total: 0,
          landowners: 0,
          businesses: 0,
          admins: 0,
        },
      };

      setStats(adminStats);
      setLoading(false);
    } catch (err) {
      console.error("Failed to load admin dashboard data:", err);
      setLoading(false);
    }
  };

  const creditStatusData = stats
    ? [
        { name: "Pending Approval", value: stats.credits.pending_approval, color: "#f59e0b" },
        { name: "Listed", value: stats.credits.listed, color: "#3b82f6" },
        { name: "Sold", value: stats.credits.sold, color: "#22c55e" },
        { name: "Retired", value: stats.credits.retired, color: "#6366f1" },
      ]
    : [];

  const registrationStatusData = stats
    ? [
        { name: "Pending", value: stats.registrationRequests.pending, color: "#f59e0b" },
        { name: "Approved", value: stats.registrationRequests.approved, color: "#22c55e" },
        { name: "Rejected", value: stats.registrationRequests.rejected, color: "#ef4444" },
      ]
    : [];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-terra-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Admin Dashboard
          </h1>
          <p className="text-gray-600 text-lg">
            System overview and management center
          </p>
        </div>

        {/* Key Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {/* Registration Requests */}
          <Link href="/admin/requests">
            <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl p-6 text-white shadow-lg hover:shadow-xl transition-shadow cursor-pointer">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium opacity-90">
                  Registration Requests
                </h3>
                <span className="text-2xl">📋</span>
              </div>
              <p className="text-3xl font-bold">
                {stats?.registrationRequests.pending || 0}
              </p>
              <p className="text-xs opacity-80 mt-1">Pending review</p>
              <div className="mt-3 flex items-center text-xs">
                <span className="bg-yellow-400 bg-opacity-30 px-2 py-1 rounded">
                  {stats?.registrationRequests.total || 0} total
                </span>
              </div>
            </div>
          </Link>

          {/* Carbon Credits */}
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium opacity-90">Carbon Credits</h3>
              <span className="text-2xl">🌿</span>
            </div>
            <p className="text-3xl font-bold">
              {stats?.credits.total || 0}
            </p>
            <p className="text-xs opacity-80 mt-1">Total credits generated</p>
            <div className="mt-3 flex items-center text-xs">
              <span className="bg-blue-400 bg-opacity-30 px-2 py-1 rounded">
                {stats?.credits.total_tco2e.toFixed(1) || 0} tCO₂e
              </span>
            </div>
          </div>

          {/* Marketplace Activity */}
          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium opacity-90">
                Listed Credits
              </h3>
              <span className="text-2xl">💹</span>
            </div>
            <p className="text-3xl font-bold">
              {stats?.credits.listed || 0}
            </p>
            <p className="text-xs opacity-80 mt-1">Available for purchase</p>
            <div className="mt-3 flex items-center text-xs">
              <span className="bg-green-400 bg-opacity-30 px-2 py-1 rounded">
                {stats?.credits.sold || 0} sold
              </span>
            </div>
          </div>

          {/* System Health */}
          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium opacity-90">System Status</h3>
              <span className="text-2xl">✅</span>
            </div>
            <p className="text-3xl font-bold">Healthy</p>
            <p className="text-xs opacity-80 mt-1">All systems operational</p>
            <div className="mt-3 flex items-center text-xs">
              <span className="bg-purple-400 bg-opacity-30 px-2 py-1 rounded">
                API: Online
              </span>
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Credit Status Distribution */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Credit Status Distribution
            </h2>
            {stats && creditStatusData.some(d => d.value > 0) ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={creditStatusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      `${name}: ${(percent * 100).toFixed(0)}%`
                    }
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {creditStatusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-400">
                No credit data available
              </div>
            )}
          </div>

          {/* Registration Requests */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Registration Request Status
            </h2>
            {stats && registrationStatusData.some(d => d.value > 0) ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={registrationStatusData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8884d8">
                    {registrationStatusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-400">
                No registration data available
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/admin/requests"
              className="flex items-center p-4 border-2 border-gray-200 rounded-lg hover:border-terra-600 hover:bg-terra-50 transition-colors"
            >
              <span className="text-2xl mr-3">📋</span>
              <div>
                <p className="font-semibold text-gray-900">Review Requests</p>
                <p className="text-sm text-gray-600">
                  {stats?.registrationRequests.pending || 0} pending
                </p>
              </div>
            </Link>

            <Link
              href="/scan"
              className="flex items-center p-4 border-2 border-gray-200 rounded-lg hover:border-terra-600 hover:bg-terra-50 transition-colors"
            >
              <span className="text-2xl mr-3">🛰️</span>
              <div>
                <p className="font-semibold text-gray-900">Scan Land</p>
                <p className="text-sm text-gray-600">AI-powered analysis</p>
              </div>
            </Link>

            <Link
              href="/marketplace"
              className="flex items-center p-4 border-2 border-gray-200 rounded-lg hover:border-terra-600 hover:bg-terra-50 transition-colors"
            >
              <span className="text-2xl mr-3">💰</span>
              <div>
                <p className="font-semibold text-gray-900">View Marketplace</p>
                <p className="text-sm text-gray-600">
                  {stats?.credits.listed || 0} credits listed
                </p>
              </div>
            </Link>
          </div>
        </div>

        {/* System Information */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            System Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">
                Platform Statistics
              </h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex justify-between">
                  <span>Total Credits Generated:</span>
                  <span className="font-medium">{stats?.credits.total || 0}</span>
                </li>
                <li className="flex justify-between">
                  <span>Total CO₂e Offset:</span>
                  <span className="font-medium">
                    {stats?.credits.total_tco2e.toFixed(2) || 0} tonnes
                  </span>
                </li>
                <li className="flex justify-between">
                  <span>Credits Retired:</span>
                  <span className="font-medium">{stats?.credits.retired || 0}</span>
                </li>
                <li className="flex justify-between">
                  <span>Pending Approvals:</span>
                  <span className="font-medium text-yellow-600">
                    {stats?.credits.pending_approval || 0}
                  </span>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">
                Registration Pipeline
              </h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex justify-between">
                  <span>Total Requests:</span>
                  <span className="font-medium">
                    {stats?.registrationRequests.total || 0}
                  </span>
                </li>
                <li className="flex justify-between">
                  <span>Approved:</span>
                  <span className="font-medium text-green-600">
                    {stats?.registrationRequests.approved || 0}
                  </span>
                </li>
                <li className="flex justify-between">
                  <span>Pending:</span>
                  <span className="font-medium text-yellow-600">
                    {stats?.registrationRequests.pending || 0}
                  </span>
                </li>
                <li className="flex justify-between">
                  <span>Rejected:</span>
                  <span className="font-medium text-red-600">
                    {stats?.registrationRequests.rejected || 0}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
