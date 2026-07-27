'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Package, User, Lock, ArrowRight } from 'lucide-react'
import { auth } from '@/lib/api'

// Patrón SVG de fondo con iconos del hogar que se repite en tile 120×120
function BgPattern() {
  return (
    <svg
      className="absolute inset-0 w-full h-full text-accent opacity-[0.15] dark:opacity-[0.22] pointer-events-none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <pattern id="lp" x="0" y="0" width="120" height="120" patternUnits="userSpaceOnUse">
          {/* Carrito */}
          <g transform="translate(8,8)" stroke="currentColor" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
            <path d="M1 1h4l2.68 11.39A2 2 0 0 0 9.62 14h9.76a2 2 0 0 0 1.94-1.58L23 6H6"/>
          </g>
          {/* Caja */}
          <g transform="translate(68,8)" stroke="currentColor" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>
            <path d="m3.29 7 8.71 5 8.71-5M12 22V12"/>
          </g>
          {/* Reloj */}
          <g transform="translate(8,68)" stroke="currentColor" fill="none" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </g>
          {/* Lista */}
          <g transform="translate(68,68)" stroke="currentColor" fill="none" strokeWidth="1.5" strokeLinecap="round">
            <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>
          </g>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#lp)"/>
    </svg>
  )
}

export default function Home() {
  const router = useRouter()
  const [isLogin, setIsLogin] = useState(true)
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Si ya hay sesión activa, redirigir directamente al dashboard
  useEffect(() => {
    fetch('/api/auth/estado', { credentials: 'include' })
      .then((r) => r.ok ? r.json() : null)
      .then((datos) => {
        if (datos?.usuario) router.replace('/dashboard')
      })
      .catch(() => {})
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (!usuario || !password) {
      setError('Por favor completa todos los campos')
      setLoading(false)
      return
    }

    // El backend exige mínimo 8 caracteres al registrar (stockhogar/rutas/auth.py)
    if (!isLogin && password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      setLoading(false)
      return
    }

    try {
      if (isLogin) {
        await auth.login(usuario, password)
      } else {
        await auth.registrar(usuario, password)
      }

      const estado = await auth.estado()
      if (!estado?.usuario) {
        throw new Error('No se pudo confirmar la sesión iniciada')
      }

      window.location.href = '/dashboard'
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de conexión con el servidor')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => { setIsLogin(!isLogin); setError(''); setUsuario(''); setPassword('') }

  return (
    <main className="min-h-screen flex flex-col bg-background text-foreground">
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 mb-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-accent-foreground shadow-sm">
                <Package className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight text-foreground">Dreame!</h1>
                <p className="text-sm text-muted-foreground">Inventario del Hogar</p>
              </div>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Gestiona tu inventario del hogar y lista de compra de forma inteligente
            </p>
          </div>

          <div className="card mb-4">
            <div className="mb-4 text-center">
              <h2 className="text-lg font-semibold text-foreground">
                {isLogin ? 'Inicia sesión' : 'Crea tu cuenta'}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {isLogin ? 'Accede a tu inventario y listas' : 'Regístrate para empezar'}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">Usuario</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    value={usuario}
                    onChange={(e) => setUsuario(e.target.value)}
                    placeholder="tu_usuario"
                    className="input-field pl-10"
                    required
                    disabled={loading}
                    autoCapitalize="none"
                    autoCorrect="off"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">Contraseña</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="input-field pl-10"
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full gap-2"
              >
                {loading ? 'Procesando...' : isLogin ? 'Iniciar Sesión' : 'Registrarse'}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>

          </div>

          {/* Toggle login/registro */}
          <p className="text-sm text-center text-muted-foreground">
            {isLogin ? '¿No tienes cuenta?' : '¿Ya tienes cuenta?'}{' '}
            <button onClick={resetForm} className="font-semibold text-accent hover:underline">
              {isLogin ? 'Crea una' : 'Inicia Sesión'}
            </button>
          </p>

          {/* Separador */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-border"/>
            <span className="text-xs text-muted-foreground">o</span>
            <div className="flex-1 h-px bg-border"/>
          </div>

          {/* OAuth — /auth/* proxiado por Next (next.config.mjs) para que la
              cookie de sesión quede en el mismo origen */}
          <div className="space-y-2">
            <a href="/auth/google" className="btn-secondary w-full flex items-center justify-center gap-2">
              <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908C16.658 12.013 17.64 9.706 17.64 6.965c0-.637-.057-1.251-.164-1.84z" fill="#4285F4"/>
                <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
                <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
              </svg>
              <strong>Continuar con Google</strong>
            </a>
            <a href="/auth/apple" className="btn-secondary w-full flex items-center justify-center gap-2">
              <svg width="15" height="18" viewBox="0 0 814 1000" xmlns="http://www.w3.org/2000/svg" className="fill-foreground" aria-hidden="true">
                <path d="M788.1 340.9c-5.8 4.5-108.2 62.2-108.2 190.5 0 148.4 130.3 200.9 134.2 202.2-.6 3.2-20.7 71.9-68.7 141.9-42.8 61.6-87.5 123.1-155.5 123.1s-85.5-39.5-164-39.5c-76 0-103.7 40.8-165.9 40.8s-105-28.4-149.5-71.1c-24.2-23.3-43.8-50.3-56.3-79.5C-8.3 788.2 0 727.5 0 724.3c0-4.5 0-9 .3-13.5 36.5-153.5 183.2-313.8 351.8-313.8 67.2 0 117.9 30.2 159.8 30.2 40.4 0 103.1-32.1 173.1-32.1zm-231-155.5c19.1-26.4 33-64.2 33-104.7 0-5.8-.3-11.9-.9-17.6-32.3 1.2-70.4 22.2-94.1 51.6-17.3 21.2-33 57.6-33 96.9 0 6.7.9 13.5 1.5 15.8 2.1.3 5.5.9 8.8.9 28.9 0 61.8-18.1 84.7-42.9z"/>
              </svg>
              <strong>Continuar con Apple</strong>
            </a>
          </div>

        </div>
      </div>
    </main>
  )
}
