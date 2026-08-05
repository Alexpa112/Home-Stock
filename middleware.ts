import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Prefijos de rutas protegidas (todo lo demas se trata como publico); antes
// se hacia al reves (lista de rutas publicas con '/' incluido), lo que con
// startsWith hacia que TODA ruta empezara por '/' y la comprobacion de
// sesion de mas abajo nunca se llegara a ejecutar (bug real, sin proteccion
// real a nivel de middleware, solo el chequeo en cliente de ProtectedRoute).
const RUTAS_PROTEGIDAS = ['/dashboard']

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname

  // Rutas protegidas necesitan sesión
  if (RUTAS_PROTEGIDAS.some((prefijo) => pathname.startsWith(prefijo))) {
    // Verificar si hay sesión válida mediante cookie
    const hasSession = request.cookies.has('session') || request.cookies.has('Authorization')

    if (!hasSession) {
      // Redirigir a login si no hay sesión
      const loginUrl = new URL('/', request.url)
      return NextResponse.redirect(loginUrl)
    }
  }

  // CSP con nonce por peticion (S-12): antes la CSP era estatica
  // (next.config.mjs::headers()), lo que obligaba a dejar 'unsafe-inline'
  // en script-src para el script anti-FOUC de app/layout.tsx (no hay forma
  // de generar un nonce distinto por peticion desde un fichero de
  // configuracion estatico). Aqui si se puede: el nonce se fija como
  // cabecera de REQUEST (x-nonce) para que app/layout.tsx la lea via
  // next/headers y la aplique a su script inline, y como cabecera de
  // RESPUESTA (Content-Security-Policy) para que el navegador solo
  // ejecute scripts marcados con ese nonce exacto. 'strict-dynamic' permite
  // que los scripts que Next.js inyecta para la hidratacion (que el propio
  // framework marca con el mismo nonce al detectar esta cabecera) carguen
  // los suyos sin necesitar cada uno su propio nonce.
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
  const csp = `
    default-src 'self';
    script-src 'self' 'nonce-${nonce}' 'strict-dynamic';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: blob:;
    font-src 'self' data:;
    connect-src 'self';
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
    object-src 'none';
  `.replace(/\s{2,}/g, ' ').trim()

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-nonce', nonce)
  requestHeaders.set('Content-Security-Policy', csp)

  const response = NextResponse.next({ request: { headers: requestHeaders } })
  response.headers.set('Content-Security-Policy', csp)
  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - api / auth: son reescrituras hacia Flask (ver next.config.mjs) y su
     *   autorización la hace el propio backend, así que pasar por aquí solo
     *   añadía latencia a CADA llamada de la app (varias por pulsación). No
     *   necesitan CSP tampoco: son respuestas JSON/redirects, no HTML que
     *   ejecute scripts.
     */
    '/((?!_next/static|_next/image|api/|auth/|favicon.ico).*)',
  ],
}
