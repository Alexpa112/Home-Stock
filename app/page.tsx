'use client'

import { useState } from 'react'
import { Package, ShoppingCart, Zap, ArrowRight, Lock, User, Mail } from 'lucide-react'
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
      const message = err instanceof Error ? err.message : 'Error de conexión con el servidor'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

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

          <div className="mb-8 grid grid-cols-3 gap-2">
            <div className="rounded-lg border border-border bg-card p-3 text-center shadow-sm">
              <Package className="mx-auto mb-1 h-5 w-5 text-accent" />
              <p className="text-xs font-medium text-foreground">Stock</p>
            </div>
            <div className="rounded-lg border border-border bg-card p-3 text-center shadow-sm">
              <ShoppingCart className="mx-auto mb-1 h-5 w-5 text-accent" />
              <p className="text-xs font-medium text-foreground">Compras</p>
            </div>
            <div className="rounded-lg border border-border bg-card p-3 text-center shadow-sm">
              <Zap className="mx-auto mb-1 h-5 w-5 text-accent" />
              <p className="text-xs font-medium text-foreground">Rápido</p>
            </div>
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

            <div className="my-4 flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">o</span>
              <div className="h-px flex-1 bg-border" />
            </div>
            <div className="space-y-2">
              <a href="/auth/google" className="btn-secondary w-full gap-2">
                <Mail className="h-4 w-4" />
                Continuar con Google
              </a>
              <a href="/auth/apple" className="btn-secondary w-full gap-2">
                <Mail className="h-4 w-4" />
                Continuar con Apple
              </a>
            </div>
          </div>

          <div className="text-center">
            <p className="mb-2 text-sm text-muted-foreground">
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

      <div className="border-t border-border py-4 text-center text-xs text-muted-foreground">
        <p>© 2024 Dreame! - Inventario Inteligente del Hogar</p>
      </div>
    </main>
  )
}
