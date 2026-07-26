import type { Metadata, Viewport } from 'next'
import './globals.css'
import RootLayoutClient from './RootLayoutClient'

export const metadata: Metadata = {
  title: 'Dreame! - Inventario del Hogar',
  description: 'Gestiona tu inventario del hogar y lista de compra de forma fácil',
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-icon.png',
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
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
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}else{document.documentElement.classList.add('light')}})()`,
          }}
        />
        <RootLayoutClient>{children}</RootLayoutClient>
      </body>
    </html>
  )
}
