'use client'

import { useState } from 'react'
import { Package, ShoppingCart, Zap } from 'lucide-react'
import { auth } from '@/lib/api'

export default function Home() {
  const [isLogin, setIsLogin] = useState(true)
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (!usuario || !password) {
      setError('Por favor completa todos los campos')
      setLoading(false)
      return
    }

    // El backend exige minimo 8 caracteres al registrar (ver
    // stockhogar/rutas/auth.py:registrar); en login no hay minimo (podria
    // ser una cuenta antigua con password mas corta).
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

      // Redirigir con delay para asegurar que la cookie de sesion se guardo.
      setTimeout(() => {
        window.location.href = '/dashboard'
      }, 300)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error de conexión con el servidor'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-950">
      {/* Hero Section */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          {/* Logo y Header */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 mb-4">
              <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                <Package className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Dreame!</h1>
                <p className="text-sm text-muted-foreground">Inventario del Hogar</p>
              </div>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Gestiona tu inventario del hogar y lista de compra de forma inteligente
            </p>
          </div>

          {/* Features Preview */}
          <div className="grid grid-cols-3 gap-2 mb-8">
            <div className="text-center p-3 bg-white dark:bg-slate-800 rounded-lg">
              <Package className="w-5 h-5 text-blue-500 mx-auto mb-1" />
              <p className="text-xs text-foreground font-medium">Stock</p>
            </div>
            <div className="text-center p-3 bg-white dark:bg-slate-800 rounded-lg">
              <ShoppingCart className="w-5 h-5 text-green-500 mx-auto mb-1" />
              <p className="text-xs text-foreground font-medium">Compras</p>
            </div>
            <div className="text-center p-3 bg-white dark:bg-slate-800 rounded-lg">
              <Zap className="w-5 h-5 text-yellow-500 mx-auto mb-1" />
              <p className="text-xs text-foreground font-medium">Rápido</p>
            </div>
          </div>

          {/* Form Card */}
          <div className="card mb-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Usuario</label>
                <input
                  type="text"
                  value={usuario}
                  onChange={(e) => setUsuario(e.target.value)}
                  placeholder="tu_usuario"
                  className="input-field"
                  required
                  disabled={loading}
                  autoCapitalize="none"
                  autoCorrect="off"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Contraseña</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-field"
                  required
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 text-sm rounded-lg">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full"
              >
                {loading ? 'Procesando...' : isLogin ? 'Iniciar Sesión' : 'Registrarse'}
              </button>
            </form>

            {/* Login con Google/Apple: navegacion normal (no fetch), ver
                stockhogar/rutas/oauth.py. /auth/* pasa por el proxy de Next
                (next.config.mjs) para que la cookie de sesion que fija el
                callback quede en este mismo origen. */}
            <div className="flex items-center gap-3 my-4">
              <div className="flex-1 h-px bg-border" />
              <span className="text-xs text-muted-foreground">o</span>
              <div className="flex-1 h-px bg-border" />
            </div>
            <div className="space-y-2">
              <a
                href="/auth/google"
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                Continuar con Google
              </a>
              <a
                href="/auth/apple"
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                Continuar con Apple
              </a>
            </div>
          </div>

          {/* Toggle */}
          <div className="text-center">
            <p className="text-sm text-muted-foreground mb-2">
              {isLogin ? '¿No tienes cuenta?' : '¿Ya tienes cuenta?'}
            </p>
            <button
              onClick={() => {
                setIsLogin(!isLogin)
                setError('')
                setUsuario('')
                setPassword('')
              }}
              className="text-sm font-medium text-accent hover:underline"
            >
              {isLogin ? 'Regístrate' : 'Inicia Sesión'}
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-4 text-xs text-muted-foreground border-t border-border">
        <p>© 2024 Dreame! - Inventario Inteligente del Hogar</p>
      </div>
    </main>
  )
}
