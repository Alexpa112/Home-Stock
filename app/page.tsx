'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import { User, Lock, ArrowRight, ShieldCheck, Mail } from 'lucide-react'
import { auth } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

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

function HomeContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useTranslation()

  // M-12: validar que 'next' sea una ruta relativa del origen, no un redirect
  // a otro dominio. Acepta rutas que empiezan con / y no contienen :/
  const _validar_ruta_relativa = (ruta: string): boolean => {
    return ruta.startsWith('/') && !ruta.includes('://')
  }

  const nextParam = searchParams.get('next') || '/dashboard'
  const destino = _validar_ruta_relativa(nextParam) ? nextParam : '/dashboard'
  const [isLogin, setIsLogin] = useState(true)
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // 'codigo_2fa=1' lo pone el callback OAuth (stockhogar/rutas/oauth.py,
  // PARAM_CODIGO_2FA) cuando el usuario tiene 2FA activo: la sesion aun no
  // existe, solo queda pendiente meter el codigo, asi que se abre directamente
  // este formulario en vez del de usuario/contrasena. El login por contrasena
  // llega al mismo sitio por otra via (respuesta.requiere_codigo, mas abajo).
  const [requiereCodigo, setRequiereCodigo] = useState(
    searchParams.get('codigo_2fa') === '1'
  )
  const [codigo, setCodigo] = useState('')
  const [aceptaTerminos, setAceptaTerminos] = useState(false)
  const [reenviando, setReenviando] = useState(false)
  const [reenviado, setReenviado] = useState(false)
  const [mostrarOlvidoPassword, setMostrarOlvidoPassword] = useState(false)
  const [identificadorReset, setIdentificadorReset] = useState('')
  const [resetEnviando, setResetEnviando] = useState(false)
  const [resetMensaje, setResetMensaje] = useState('')

  // Si ya hay sesión activa, redirigir directamente al dashboard
  useEffect(() => {
    fetch('/api/auth/estado', { credentials: 'include' })
      .then((r) => r.ok ? r.json() : null)
      .then((datos) => {
        if (datos?.usuario) router.replace(destino)
      })
      .catch(() => {})
  }, [router, destino])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (!usuario || !password) {
      setError(t('err_campos_requeridos'))
      setLoading(false)
      return
    }

    // El backend exige minimo 10 caracteres al registrar (stockhogar/config.py LONGITUD_PASSWORD_MINIMA)
    if (!isLogin && password.length < 10) {
      setError(t('err_password_min_8'))
      setLoading(false)
      return
    }

    if (!isLogin && !aceptaTerminos) {
      setError(t('err_debe_aceptar_terminos'))
      setLoading(false)
      return
    }

    try {
      if (isLogin) {
        const respuesta: any = await auth.login(usuario, password)
        if (respuesta?.requiere_codigo) {
          setRequiereCodigo(true)
          setLoading(false)
          return
        }
      } else {
        await auth.registrar(usuario, password, aceptaTerminos)
      }

      const estado = await auth.estado()
      if (!estado?.usuario) {
        throw new Error(t('err_sesion_no_confirmada'))
      }

      window.location.href = destino
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setLoading(false)
    }
  }

  const handleVerificarCodigo = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await auth.verificarCodigo(codigo.trim())
      const estado = await auth.estado()
      if (!estado?.usuario) {
        throw new Error(t('err_sesion_no_confirmada'))
      }
      window.location.href = destino
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setLoading(false)
    }
  }

  const handleReenviarCodigo = async () => {
    setReenviando(true)
    setError('')
    try {
      await auth.reenviarCodigo()
      setReenviado(true)
      setTimeout(() => setReenviado(false), 4000)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setReenviando(false)
    }
  }

  const handleSolicitarReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setResetEnviando(true)
    setResetMensaje('')
    try {
      const datos: any = await auth.solicitarResetPassword(identificadorReset)
      setResetMensaje(t(datos.mensaje || 'mensaje_reset_generico'))
    } catch (err) {
      setResetMensaje(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setResetEnviando(false)
    }
  }

  const resetForm = () => {
    setIsLogin(!isLogin)
    setError('')
    setUsuario('')
    setPassword('')
    setRequiereCodigo(false)
    setCodigo('')
    setAceptaTerminos(false)
    setMostrarOlvidoPassword(false)
    setResetMensaje('')
  }

  return (
    <main className="min-h-screen flex flex-col bg-background text-foreground">
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 mb-4">
              <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-xl shadow-sm">
                <Image src="/icon.svg" alt="" width={48} height={48} priority />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight text-foreground">Dreame!</h1>
                <p className="text-sm text-muted-foreground">{t('subtitulo_app')}</p>
              </div>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {t('app_descripcion')}
            </p>
          </div>

          <div className="card mb-4">
            <div className="mb-4 text-center">
              <h2 className="text-lg font-semibold text-foreground">
                {requiereCodigo ? t('titulo_verificacion_codigo') : isLogin ? t('titulo_login') : t('titulo_registro')}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {requiereCodigo ? t('subtitulo_verificacion_codigo') : isLogin ? t('subtitulo_login') : t('subtitulo_registro')}
              </p>
            </div>

            {requiereCodigo ? (
              <form onSubmit={handleVerificarCodigo} className="space-y-6">
                {/* Security icon */}
                <div className="flex justify-center mb-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10">
                    <ShieldCheck className="h-8 w-8 text-accent" />
                  </div>
                </div>

                {/* Info message */}
                <div className="rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 p-4 flex gap-3">
                  <Mail className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-blue-700 dark:text-blue-200">
                    {t('subtitulo_verificacion_codigo')}
                  </p>
                </div>

                {/* Code input with visual feedback */}
                <div className="space-y-3">
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                    placeholder="000000"
                    className={`input-field text-center text-2xl font-bold tracking-[0.5em] transition-all ${
                      codigo.length === 6 ? 'border-accent shadow-lg shadow-accent/20' : 'border-border'
                    }`}
                    maxLength={6}
                    required
                    autoFocus
                    disabled={loading}
                  />
                  <p className="text-xs text-muted-foreground text-center">
                    {codigo.length}/6 {t('digitos')}
                  </p>
                </div>

                {error && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200 flex gap-2">
                    <span className="text-lg">⚠️</span>
                    <span>{error}</span>
                  </div>
                )}
                {reenviado && (
                  <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700 dark:border-green-900 dark:bg-green-950/30 dark:text-green-200 flex gap-2">
                    <span className="text-lg">✓</span>
                    <span>{t('codigo_reenviado')}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || codigo.length !== 6}
                  className={`btn-primary w-full gap-2 transition-all ${
                    codigo.length === 6 ? '' : 'opacity-50'
                  }`}
                >
                  {loading ? t('procesando') : t('btn_verificar_codigo')}
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </button>

                <div className="border-t border-border pt-4">
                  <p className="text-xs text-muted-foreground text-center mb-3">
                    {t('no_recibiste_codigo')}
                  </p>
                  <button
                    type="button"
                    onClick={handleReenviarCodigo}
                    disabled={reenviando}
                    className="w-full px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {reenviando ? t('reenviando') : t('reenviar_codigo')}
                  </button>
                </div>
              </form>
            ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">{t('usuario')}</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    value={usuario}
                    onChange={(e) => setUsuario(e.target.value)}
                    placeholder={t('placeholder_tu_usuario')}
                    className="input-field pl-10"
                    required
                    disabled={loading}
                    autoCapitalize="none"
                    autoCorrect="off"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">{t('contraseña')}</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t('placeholder_tu_contrasena')}
                    className="input-field pl-10"
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {!isLogin && (
                <div className="space-y-1.5">
                  <label className="flex items-start gap-2 text-sm text-foreground cursor-pointer">
                    <input
                      type="checkbox"
                      checked={aceptaTerminos}
                      onChange={(e) => setAceptaTerminos(e.target.checked)}
                      className="mt-0.5 h-4 w-4 shrink-0 rounded border-border accent-accent"
                      disabled={loading}
                      required
                    />
                    <span>{t('acepta_terminos_texto')}</span>
                  </label>
                  <p className="pl-6 text-xs text-muted-foreground">
                    <a href="/legal/terminos" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                      {t('enlace_terminos')}
                    </a>
                    {' · '}
                    <a href="/legal/privacidad" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                      {t('enlace_privacidad')}
                    </a>
                  </p>
                </div>
              )}

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
                {loading ? t('procesando') : isLogin ? t('btn_iniciar_sesion') : t('btn_registrarse')}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>

              {isLogin && (
                <button
                  type="button"
                  onClick={() => { setMostrarOlvidoPassword(!mostrarOlvidoPassword); setResetMensaje('') }}
                  className="w-full text-center text-sm text-accent hover:underline"
                >
                  {t('olvidaste_password')}
                </button>
              )}
            </form>
            )}

            {isLogin && mostrarOlvidoPassword && !requiereCodigo && (
              <form onSubmit={handleSolicitarReset} className="mt-4 space-y-3 border-t border-border pt-4">
                <input
                  type="text"
                  value={identificadorReset}
                  onChange={(e) => setIdentificadorReset(e.target.value)}
                  placeholder={t('placeholder_usuario_o_email')}
                  className="input-field"
                  required
                  disabled={resetEnviando}
                  autoCapitalize="none"
                  autoCorrect="off"
                />
                {resetMensaje && (
                  <p className="text-sm text-muted-foreground">{resetMensaje}</p>
                )}
                <button type="submit" disabled={resetEnviando} className="btn-secondary w-full">
                  {resetEnviando ? t('procesando') : t('btn_enviar_enlace_reset')}
                </button>
              </form>
            )}

          </div>

          {!requiereCodigo && (
          <>
          {/* Toggle login/registro */}
          <p className="text-sm text-center text-muted-foreground">
            {isLogin ? t('no_tienes_cuenta') : t('ya_tienes_cuenta')}{' '}
            <button onClick={resetForm} className="font-semibold text-accent hover:underline">
              {isLogin ? t('crea_una') : t('inicia_sesion_link')}
            </button>
          </p>

          {/* Separador */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-border"/>
            <span className="text-xs text-muted-foreground">{t('separador_o')}</span>
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
              <strong>{t('continuar_google')}</strong>
            </a>
            <a href="/auth/apple" className="btn-secondary w-full flex items-center justify-center gap-2">
              <svg width="15" height="18" viewBox="0 0 814 1000" xmlns="http://www.w3.org/2000/svg" className="fill-foreground" aria-hidden="true">
                <path d="M788.1 340.9c-5.8 4.5-108.2 62.2-108.2 190.5 0 148.4 130.3 200.9 134.2 202.2-.6 3.2-20.7 71.9-68.7 141.9-42.8 61.6-87.5 123.1-155.5 123.1s-85.5-39.5-164-39.5c-76 0-103.7 40.8-165.9 40.8s-105-28.4-149.5-71.1c-24.2-23.3-43.8-50.3-56.3-79.5C-8.3 788.2 0 727.5 0 724.3c0-4.5 0-9 .3-13.5 36.5-153.5 183.2-313.8 351.8-313.8 67.2 0 117.9 30.2 159.8 30.2 40.4 0 103.1-32.1 173.1-32.1zm-231-155.5c19.1-26.4 33-64.2 33-104.7 0-5.8-.3-11.9-.9-17.6-32.3 1.2-70.4 22.2-94.1 51.6-17.3 21.2-33 57.6-33 96.9 0 6.7.9 13.5 1.5 15.8 2.1.3 5.5.9 8.8.9 28.9 0 61.8-18.1 84.7-42.9z"/>
              </svg>
              <strong>{t('continuar_apple')}</strong>
            </a>
          </div>
          </>
          )}

        </div>
      </div>

      <footer className="pb-6 px-4 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <a href="/legal/aviso-legal" className="hover:text-foreground hover:underline">{t('enlace_aviso_legal')}</a>
        <a href="/legal/privacidad" className="hover:text-foreground hover:underline">{t('enlace_privacidad')}</a>
        <a href="/legal/terminos" className="hover:text-foreground hover:underline">{t('enlace_terminos')}</a>
        <a href="/legal/cookies" className="hover:text-foreground hover:underline">{t('enlace_cookies')}</a>
      </footer>
    </main>
  )
}

export default function Home() {
  return (
    <Suspense fallback={null}>
      <HomeContent />
    </Suspense>
  )
}
