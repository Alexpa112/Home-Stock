/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  reactStrictMode: true,
  productionBrowserSourceMaps: false,
  compress: true,
  
  // Headers de seguridad
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ]
  },

  // Rewrite de API y OAuth hacia el backend Flask
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/api/:path*`,
        },
        {
          // Login con Google/Apple (stockhogar/rutas/oauth.py): tiene que
          // pasar por este mismo proxy, no ser una llamada directa al
          // backend, para que la cookie de sesion que fija el callback
          // quede en el MISMO origen (este frontend) que luego hace las
          // llamadas a /api/*. Ver tambien APP_URL en el .env del backend:
          // debe apuntar a la URL publica de ESTE frontend (no a la del
          // backend) para que Google redirija aqui tras el login.
          source: '/auth/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/auth/:path*`,
        },
      ],
    }
  },
}

export default nextConfig
