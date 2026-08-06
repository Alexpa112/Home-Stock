import type { Metadata, Viewport } from 'next'
import { headers } from 'next/headers'
import './globals.css'
import RootLayoutClient from './RootLayoutClient'

export const metadata: Metadata = {
  title: 'Dreame! - Inventario del Hogar',
  description: 'Gestiona tu inventario del hogar y lista de compra de forma fácil',
  icons: {
    icon: [
      { rel: 'icon', url: '/favicon.ico' },
      { rel: 'icon', url: '/favicon-32x32.png', sizes: '32x32' },
      { rel: 'icon', url: '/favicon-16x16.png', sizes: '16x16' },
    ],
    apple: '/apple-touch-icon.png',
    shortcut: '/apple-touch-icon.png',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  // S-12: nonce generado por peticion en middleware.ts (cabecera de request
  // x-nonce), leido aqui para que el script anti-FOUC pueda ejecutarse bajo
  // una CSP sin 'unsafe-inline'. Sin este nonce exacto, el navegador
  // bloquearia el script y la app arrancaria siempre en el tema por
  // defecto, ignorando la preferencia guardada del usuario.
  const nonce = (await headers()).get('x-nonce') ?? undefined

  return (
    <html lang="es" className="bg-background">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Dreame!" />
        <meta name="description" content="Gestiona tu inventario del hogar y lista de compra de forma inteligente" />
        <meta property="og:title" content="Dreame! - Inventario del Hogar" />
        <meta property="og:description" content="Gestiona tu inventario del hogar y lista de compra de forma inteligente" />
        <meta name="twitter:card" content="summary_large_image" />
      </head>
      <body className="antialiased text-foreground">
        {/* Anti-FOUC: aplica clase dark/light antes del primer render */}
        <script
          nonce={nonce}
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}else{document.documentElement.classList.add('light')}})()`,
          }}
        />
        <RootLayoutClient>{children}</RootLayoutClient>
      </body>
    </html>
  )
}
