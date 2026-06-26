/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["mapbox-gl", "@mapbox/mapbox-gl-draw"],

  // Proxy all /api/* requests to the backend so the browser never needs
  // to know the backend URL (no NEXT_PUBLIC_API_URL required at build time).
  async rewrites() {
    const backendUrl =
      process.env.BACKEND_URL ||
      (process.env.NODE_ENV === 'production'
        ? 'https://terrafoma-api-production-58dc.up.railway.app'
        : 'http://localhost:8002');
    return {
      // afterFiles: only proxy to backend if no local Next.js route handler matches.
      // This ensures /api/config, /api/checkout, /api/confirm-payment, /api/webhooks
      // are served by their local route handlers, not forwarded to FastAPI.
      afterFiles: [
        {
          source: '/api/:path*',
          destination: `${backendUrl}/api/:path*`,
        },
      ],
    };
  },

  // Optimize for production deployment
  output: 'standalone',
  
  // Reduce memory usage during build
  experimental: {
    optimizePackageImports: ['recharts', 'mapbox-gl'],
  },
  
  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  
  // Webpack optimizations
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    
    // Reduce bundle size
    config.optimization = {
      ...config.optimization,
      moduleIds: 'deterministic',
    };
    
    return config;
  },
};

module.exports = nextConfig;
