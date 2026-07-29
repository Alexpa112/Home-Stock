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
  
  // Headers de seguridad y caché
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
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            // Sin uso de camara/microfono/geolocalizacion en la app (el
            // escaneo de tickets usa <input type="file">, no getUserMedia):
            // se desactivan explicitamente en vez de dejarlas disponibles
            // por defecto para cualquier script que se cuele.
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), payment=()',
          },
          {
            // Solo tiene efecto cuando se sirve por HTTPS (el tunel de
            // Cloudflare hace la terminacion TLS); en HTTP local el
            // navegador la ignora, así que es seguro tenerla siempre.
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains',
          },
          {
            // 'unsafe-inline' en script-src: el anti-FOUC de app/layout.tsx
            // usa dangerouslySetInnerHTML con un <script> inline (aplica el
            // tema oscuro/claro antes del primer render). 'unsafe-eval' se
            // deja por compatibilidad con el runtime de Next/webpack; si en
            // el futuro se confirma que la build de produccion no lo
            // necesita, se puede retirar para endurecer la politica.
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              "font-src 'self' data:",
              "connect-src 'self'",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "object-src 'none'",
            ].join('; '),
          },
        ],
      },
      {
        source: '/',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0',
          },
        ],
      },
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0',
          },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
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
