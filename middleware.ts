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

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
