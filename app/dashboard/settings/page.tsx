'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun, LogOut, AlertCircle, Globe, History, Grid3x3, List, Layers, Eye, EyeOff, Lock, Trash2, ChevronRight, User, Mail, ShieldCheck, ScrollText, Cookie, Tags, CloudOff, Bell } from 'lucide-react'
import Link from 'next/link'
import { auth, idiomas as idiomasApi } from '@/lib/api'
import { useListPreferences } from '@/contexts/ListPreferencesContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { usePushNotifications } from '@/lib/usePushNotifications'

export default function SettingsPage() {
  const { preferences, updatePreferences } = useListPreferences()
  const { t, cambiarIdioma: aplicarIdiomaContexto } = useTranslation()
  const notificacionesPush = usePushNotifications()
  const [darkMode, setDarkMode] = useState(false)
  const [user, setUser] = useState<{ usuario?: string; nombre?: string | null; email?: string | null; id?: number }>({})
  const [dobleFactorActivo, setDobleFactorActivo] = useState(false)
  const [cargandoDobleFactor, setCargandoDobleFactor] = useState(false)
  const [emailVerificado, setEmailVerificado] = useState(true)
  const [ocrLocal, setOcrLocal] = useState(false)
  const [cargandoOcrLocal, setCargandoOcrLocal] = useState(false)
  const [enviandoVerificacion, setEnviandoVerificacion] = useState(false)
  const [verificacionEnviada, setVerificacionEnviada] = useState(false)
  const [cerrandoOtrasSesiones, setCerrandoOtrasSesiones] = useState(false)
  const [eventosSeguridad, setEventosSeguridad] = useState<{ evento: string; resultado: string; fecha: number }[]>([])
  const [exportandoDatos, setExportandoDatos] = useState(false)
  const [confirmandoLogout, setConfirmandoLogout] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')
  const [idiomasDisponibles, setIdiomasDisponibles] = useState<Record<string, { nombre: string; nativo: string }>>({})
  const [idiomaActual, setIdiomaActual] = useState('es')

  // Estado para editar usuario (login)
  const [editandoNombre, setEditandoNombre] = useState(false)
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [cargandoNombre, setCargandoNombre] = useState(false)

  // Estado para editar nombre a mostrar (independiente del usuario de login)
  const [editandoNombreMostrar, setEditandoNombreMostrar] = useState(false)
  const [nuevoNombreMostrar, setNuevoNombreMostrar] = useState('')
  const [cargandoNombreMostrar, setCargandoNombreMostrar] = useState(false)

  // Estado para cambiar contraseña
  const [editandoPassword, setEditandoPassword] = useState(false)
  const [passwordActual, setPasswordActual] = useState('')
  const [passwordNueva, setPasswordNueva] = useState('')
  const [passwordConfirmacion, setPasswordConfirmacion] = useState('')
  const [cargandoPassword, setCargandoPassword] = useState(false)
  const [mostrarPassword, setMostrarPassword] = useState({ actual: false, nueva: false, confirmacion: false })

  // Estado para eliminar cuenta
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false)
  const [cargandoEliminar, setCargandoEliminar] = useState(false)

  useEffect(() => {
    const isDark = document.documentElement.classList.contains('dark')
    setDarkMode(isDark)
    loadUser()
    cargarEventosSeguridad()
    idiomasApi
      .disponibles()
      .then((data: any) => {
        setIdiomasDisponibles(data.idiomas || {})
        setIdiomaActual(data.actual || 'es')
      })
      .catch(() => {})
  }, [])

  const cambiarIdioma = async (codigo: string) => {
    const idiomaAnterior = idiomaActual
    setIdiomaActual(codigo)
    try {
      await idiomasApi.cambiar(codigo)
      await aplicarIdiomaContexto(codigo)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_cambiar_idioma'))
      setIdiomaActual(idiomaAnterior)
    }
  }

  const cambiarDobleFactor = async (activo: boolean) => {
    setCargandoDobleFactor(true)
    setError('')
    try {
      await auth.cambiarDobleFactor(activo)
      setDobleFactorActivo(activo)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_doble_factor_requiere_email'))
    } finally {
      setCargandoDobleFactor(false)
    }
  }

  const loadUser = async () => {
    try {
      const response = await fetch('/api/auth/estado', {
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setUser({ usuario: data.usuario, nombre: data.nombre, email: data.email, id: data.usuario_id })
        setNuevoNombre(data.usuario || '')
        setNuevoNombreMostrar(data.nombre || '')
        setDobleFactorActivo(!!data.doble_factor_activo)
        setEmailVerificado(!!data.email_verificado)
        setOcrLocal(!!data.ocr_local)

        const pref = data.tema_preferido || 'auto'
        const aplicarOscuro =
          pref === 'dark' || (pref === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)
        setDarkMode(aplicarOscuro)
        document.documentElement.classList.toggle('dark', aplicarOscuro)
      }
    } catch (err) {
      console.error('Error al cargar usuario:', err)
    }
  }

  const toggleDarkMode = async () => {
    const newDarkMode = !darkMode
    setDarkMode(newDarkMode)
    document.documentElement.classList.toggle('dark', newDarkMode)
    localStorage.setItem('theme', newDarkMode ? 'dark' : 'light')

    try {
      await auth.cambiarTema(newDarkMode ? 'dark' : 'light')
    } catch (err) {
      console.error('Error al guardar el tema:', err)
    }
  }

  const handleLogout = async () => {
    if (!confirmandoLogout) { setConfirmandoLogout(true); return }
    try {
      await auth.logout()
      window.location.href = '/'
    } catch {
      setError(t('err_cerrar_sesion'))
      setConfirmandoLogout(false)
    }
  }

  const cambiarOcrLocal = async (activo: boolean) => {
    setCargandoOcrLocal(true)
    setError('')
    try {
      await auth.cambiarPreferenciaOcr(activo)
      setOcrLocal(activo)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setCargandoOcrLocal(false)
    }
  }

  const handleEnviarVerificacionEmail = async () => {
    setEnviandoVerificacion(true)
    setError('')
    try {
      await auth.enviarVerificacionEmail()
      setVerificacionEnviada(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setEnviandoVerificacion(false)
    }
  }

  const handleCerrarOtrasSesiones = async () => {
    setCerrandoOtrasSesiones(true)
    setError('')
    setExito('')
    try {
      const datos: any = await auth.cerrarOtrasSesiones()
      setExito(t(datos.mensaje || 'sesiones_cerradas_confirmacion'))
      setTimeout(() => setExito(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setCerrandoOtrasSesiones(false)
    }
  }

  const handleExportarMisDatos = async () => {
    setExportandoDatos(true)
    setError('')
    try {
      await auth.exportarMisDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
    } finally {
      setExportandoDatos(false)
    }
  }

  const cargarEventosSeguridad = async () => {
    try {
      const eventos: any = await auth.misEventosSeguridad()
      setEventosSeguridad(eventos || [])
    } catch {
      // No critico: si falla, simplemente no se muestra la lista.
    }
  }

  const handleActualizarNombre = async () => {
    if (!nuevoNombre.trim()) {
      setError(t('err_nombre_usuario_vacio'))
      return
    }
    setCargandoNombre(true)
    setError('')
    setExito('')
    try {
      await auth.actualizarPerfil({ usuario: nuevoNombre })
      setUser({ ...user, usuario: nuevoNombre })
      setEditandoNombre(false)
      setExito(t('nombre_usuario_actualizado'))
      setTimeout(() => setExito(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar_nombre'))
    } finally {
      setCargandoNombre(false)
    }
  }

  const handleActualizarNombreMostrar = async () => {
    setCargandoNombreMostrar(true)
    setError('')
    setExito('')
    try {
      await auth.actualizarPerfil({ nombre: nuevoNombreMostrar })
      setUser({ ...user, nombre: nuevoNombreMostrar })
      setEditandoNombreMostrar(false)
      setExito(t('nombre_actualizado'))
      setTimeout(() => setExito(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar_nombre_mostrar'))
    } finally {
      setCargandoNombreMostrar(false)
    }
  }

  const handleCambiarPassword = async () => {
    if (!passwordActual || !passwordNueva || !passwordConfirmacion) {
      setError(t('err_campos_obligatorios'))
      return
    }
    if (passwordNueva !== passwordConfirmacion) {
      setError(t('error_contrasenas_no_coinciden'))
      return
    }
    if (passwordNueva.length < 10) {
      setError(t('err_password_min_8'))
      return
    }
    setCargandoPassword(true)
    setError('')
    setExito('')
    try {
      await auth.cambiarPassword(passwordActual, passwordNueva, passwordConfirmacion)
      setPasswordActual('')
      setPasswordNueva('')
      setPasswordConfirmacion('')
      setEditandoPassword(false)
      setExito(t('password_cambiada_correctamente'))
      setTimeout(() => setExito(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_cambiar_password'))
    } finally {
      setCargandoPassword(false)
    }
  }

  const handleEliminarCuenta = async () => {
    if (!confirmandoEliminar) { setConfirmandoEliminar(true); return }
    if (!user.id) return
    setCargandoEliminar(true)
    setError('')
    try {
      await auth.eliminarCuenta(user.id)
      window.location.href = '/'
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_cuenta'))
      setConfirmandoEliminar(false)
      setCargandoEliminar(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">{t('ajustes')}</h1>
        <p className="text-muted-foreground mt-1">{t('subtitulo_ajustes')}</p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{t('error')}</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Success Message */}
      {exito && (
        <div className="p-4 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="font-medium">{exito}</p>
        </div>
      )}

      {/* Grupo: Cuenta */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden divide-y divide-border">
        {/* Nombre a mostrar */}
        <div className="px-4 py-3">
          {editandoNombreMostrar ? (
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">{t('nombre')}</label>
              <input
                type="text"
                value={nuevoNombreMostrar}
                onChange={(e) => setNuevoNombreMostrar(e.target.value)}
                className="input-field"
                placeholder={t('placeholder_nuevo_nombre')}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleActualizarNombreMostrar}
                  disabled={cargandoNombreMostrar}
                  className="flex-1 px-3 py-2 bg-accent text-accent-foreground rounded-lg font-medium transition-colors disabled:opacity-50 min-h-[44px]"
                >
                  {cargandoNombreMostrar ? t('guardando') : t('guardar')}
                </button>
                <button
                  onClick={() => {
                    setEditandoNombreMostrar(false)
                    setNuevoNombreMostrar(user.nombre || '')
                  }}
                  disabled={cargandoNombreMostrar}
                  className="flex-1 px-3 py-2 bg-muted rounded-lg font-medium transition-colors min-h-[44px]"
                >
                  {t('cancelar')}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setEditandoNombreMostrar(true)}
              className="w-full flex items-center gap-3 min-h-[44px] text-left"
            >
              <User className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
              <span className="flex-1 text-sm">{t('nombre')}</span>
              <span className="text-sm text-muted-foreground truncate max-w-[40%]">{user.nombre || t('placeholder_nuevo_nombre')}</span>
              <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
            </button>
          )}
        </div>

        {/* Usuario */}
        <div className="px-4 py-3">
          {editandoNombre ? (
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">{t('usuario')}</label>
              <input
                type="text"
                value={nuevoNombre}
                onChange={(e) => setNuevoNombre(e.target.value)}
                className="input-field"
                placeholder={t('placeholder_nuevo_nombre_usuario')}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleActualizarNombre}
                  disabled={cargandoNombre}
                  className="flex-1 px-3 py-2 bg-accent text-accent-foreground rounded-lg font-medium transition-colors disabled:opacity-50 min-h-[44px]"
                >
                  {cargandoNombre ? t('guardando') : t('guardar')}
                </button>
                <button
                  onClick={() => {
                    setEditandoNombre(false)
                    setNuevoNombre(user.usuario || '')
                  }}
                  disabled={cargandoNombre}
                  className="flex-1 px-3 py-2 bg-muted rounded-lg font-medium transition-colors min-h-[44px]"
                >
                  {t('cancelar')}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setEditandoNombre(true)}
              className="w-full flex items-center gap-3 min-h-[44px] text-left"
            >
              <User className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
              <span className="flex-1 text-sm">{t('usuario')}</span>
              <span className="text-sm text-muted-foreground truncate max-w-[40%]">{user.usuario || t('cargando')}</span>
              <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
            </button>
          )}
        </div>

        {/* Email */}
        {user.email && (
          <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
            <Mail className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
            <span className="flex-1 text-sm">{t('correo_electronico')}</span>
            <span className="text-sm text-muted-foreground truncate max-w-[50%]">{user.email}</span>
          </div>
        )}

        {/* Aviso de email sin verificar (S-07) */}
        {user.email && !emailVerificado && (
          <div className="px-4 py-3 flex items-center gap-3 min-h-[44px] bg-amber-50 dark:bg-amber-950/20">
            <AlertCircle className="w-[18px] h-[18px] text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="flex-1 text-sm text-amber-700 dark:text-amber-300">{t('email_no_verificado_aviso')}</span>
            {verificacionEnviada ? (
              <span className="text-xs text-muted-foreground">{t('verificacion_email_enviada')}</span>
            ) : (
              <button
                onClick={handleEnviarVerificacionEmail}
                disabled={enviandoVerificacion}
                className="text-sm font-medium text-accent hover:underline disabled:opacity-50 shrink-0"
              >
                {t('btn_verificar_email')}
              </button>
            )}
          </div>
        )}

        {/* Doble factor */}
        <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
          <ShieldCheck className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          <div className="flex-1">
            <p className="text-sm">{t('doble_factor_titulo')}</p>
            {!user.email && (
              <p className="text-xs text-muted-foreground mt-0.5">{t('err_doble_factor_requiere_email')}</p>
            )}
          </div>
          <button
            onClick={() => cambiarDobleFactor(!dobleFactorActivo)}
            disabled={!user.email || cargandoDobleFactor}
            role="switch"
            aria-checked={dobleFactorActivo}
            aria-label={t('doble_factor_titulo')}
            className={`relative w-14 h-8 rounded-full transition-all duration-300 shrink-0 disabled:opacity-50 border-2 ${
              dobleFactorActivo
                ? 'bg-accent border-accent shadow-lg shadow-accent/30'
                : 'bg-muted border-border hover:border-muted-foreground'
            }`}
          >
            <span
              className={`absolute top-1.5 left-1.5 w-5 h-5 rounded-full bg-white shadow-md transition-all duration-300 ${
                dobleFactorActivo ? 'translate-x-6' : ''
              }`}
            />
          </button>
        </div>

        {/* Notificaciones push (P-01) */}
        {notificacionesPush.soportado && (
          <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
            <Bell className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
            <div className="flex-1">
              <p className="text-sm">{t('notificaciones_push_titulo')}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{t('notificaciones_push_descripcion')}</p>
              {notificacionesPush.error && (
                <p className="text-xs text-red-500 mt-0.5">{t(notificacionesPush.error)}</p>
              )}
            </div>
            <button
              onClick={() => (notificacionesPush.suscrito ? notificacionesPush.desactivar() : notificacionesPush.activar())}
              disabled={notificacionesPush.cargando}
              role="switch"
              aria-checked={notificacionesPush.suscrito}
              aria-label={t('notificaciones_push_titulo')}
              className={`relative w-14 h-8 rounded-full transition-all duration-300 shrink-0 disabled:opacity-50 border-2 ${
                notificacionesPush.suscrito
                  ? 'bg-accent border-accent shadow-lg shadow-accent/30'
                  : 'bg-muted border-border hover:border-muted-foreground'
              }`}
            >
              <span
                className={`absolute top-1.5 left-1.5 w-5 h-5 rounded-full bg-white shadow-md transition-all duration-300 ${
                  notificacionesPush.suscrito ? 'translate-x-6' : ''
                }`}
              />
            </button>
          </div>
        )}

        {/* Opt-out del OCR en la nube (S-26) */}
        <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
          <CloudOff className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          <div className="flex-1">
            <p className="text-sm">{t('ocr_local_titulo')}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{t('ocr_local_descripcion')}</p>
          </div>
          <button
            onClick={() => cambiarOcrLocal(!ocrLocal)}
            disabled={cargandoOcrLocal}
            role="switch"
            aria-checked={ocrLocal}
            aria-label={t('ocr_local_titulo')}
            className={`relative w-14 h-8 rounded-full transition-all duration-300 shrink-0 disabled:opacity-50 border-2 ${
              ocrLocal
                ? 'bg-accent border-accent shadow-lg shadow-accent/30'
                : 'bg-muted border-border hover:border-muted-foreground'
            }`}
          >
            <span
              className={`absolute top-1.5 left-1.5 w-5 h-5 rounded-full bg-white shadow-md transition-all duration-300 ${
                ocrLocal ? 'translate-x-6' : ''
              }`}
            />
          </button>
        </div>

        {/* Contraseña */}
        <div className="px-4 py-3">
          <button
            onClick={() => setEditandoPassword(!editandoPassword)}
            className="w-full flex items-center gap-3 min-h-[44px] text-left"
          >
            <Lock className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
            <span className="flex-1 text-sm">{t('btn_cambiar_password')}</span>
            <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
          </button>

          {editandoPassword && (
            <div className="space-y-3 mt-3 pt-3 border-t border-border">
              <div>
                <label className="text-sm text-muted-foreground">{t('password_actual')}</label>
                <div className="relative mt-1">
                  <input
                    type={mostrarPassword.actual ? 'text' : 'password'}
                    value={passwordActual}
                    onChange={(e) => setPasswordActual(e.target.value)}
                    className="input-field pr-10"
                    placeholder={t('placeholder_tu_password_actual')}
                  />
                  <button
                    type="button"
                    onClick={() => setMostrarPassword({ ...mostrarPassword, actual: !mostrarPassword.actual })}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    tabIndex={-1}
                    aria-label={mostrarPassword.actual ? t('ocultar_password') : t('mostrar_password')}
                  >
                    {mostrarPassword.actual ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="text-sm text-muted-foreground">{t('password_nueva')}</label>
                <div className="relative mt-1">
                  <input
                    type={mostrarPassword.nueva ? 'text' : 'password'}
                    value={passwordNueva}
                    onChange={(e) => setPasswordNueva(e.target.value)}
                    className="input-field pr-10"
                    placeholder={t('minimo_8_caracteres')}
                  />
                  <button
                    type="button"
                    onClick={() => setMostrarPassword({ ...mostrarPassword, nueva: !mostrarPassword.nueva })}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    tabIndex={-1}
                    aria-label={mostrarPassword.nueva ? t('ocultar_password') : t('mostrar_password')}
                  >
                    {mostrarPassword.nueva ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="text-sm text-muted-foreground">{t('confirmar_nueva_password')}</label>
                <div className="relative mt-1">
                  <input
                    type={mostrarPassword.confirmacion ? 'text' : 'password'}
                    value={passwordConfirmacion}
                    onChange={(e) => setPasswordConfirmacion(e.target.value)}
                    className="input-field pr-10"
                    placeholder={t('placeholder_confirma_contrasena')}
                  />
                  <button
                    type="button"
                    onClick={() => setMostrarPassword({ ...mostrarPassword, confirmacion: !mostrarPassword.confirmacion })}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    tabIndex={-1}
                    aria-label={mostrarPassword.confirmacion ? t('ocultar_password') : t('mostrar_password')}
                  >
                    {mostrarPassword.confirmacion ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleCambiarPassword}
                  disabled={cargandoPassword}
                  className="flex-1 px-3 py-3 bg-accent text-accent-foreground rounded-lg font-medium transition-colors disabled:opacity-50 min-h-[44px]"
                >
                  {cargandoPassword ? t('cambiando') : t('btn_cambiar_password')}
                </button>
                <button
                  onClick={() => {
                    setEditandoPassword(false)
                    setPasswordActual('')
                    setPasswordNueva('')
                    setPasswordConfirmacion('')
                  }}
                  disabled={cargandoPassword}
                  className="flex-1 px-3 py-3 bg-muted rounded-lg font-medium transition-colors min-h-[44px]"
                >
                  {t('cancelar')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Grupo: Apariencia e idioma */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden divide-y divide-border">
        {/* Modo oscuro */}
        <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
          {darkMode ? (
            <Moon className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          ) : (
            <Sun className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          )}
          <span className="flex-1 text-sm">{t('modo_oscuro')}</span>
          <button
            onClick={toggleDarkMode}
            className={`relative inline-flex items-center h-8 w-14 rounded-full transition-all duration-300 shrink-0 border-2 ${
              darkMode
                ? 'bg-accent border-accent shadow-lg shadow-accent/30'
                : 'bg-muted border-border hover:border-muted-foreground'
            }`}
            aria-label={darkMode ? t('aria_desactivar_modo_oscuro') : t('aria_activar_modo_oscuro')}
            aria-pressed={darkMode}
          >
            <span
              className={`absolute top-1.5 left-1.5 w-5 h-5 bg-white rounded-full shadow-md transition-all duration-300 ${
                darkMode ? 'translate-x-6' : ''
              }`}
            />
          </button>
        </div>

        {/* Idioma */}
        <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
          <Globe className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          <label htmlFor="sel-idioma" className="flex-1 text-sm">{t('idioma')}</label>
          <select
            id="sel-idioma"
            value={idiomaActual}
            onChange={(e) => cambiarIdioma(e.target.value)}
            className="!min-h-0 !w-auto !py-1.5 !px-2 text-sm rounded-lg border border-border bg-transparent"
            aria-label={t('aria_idioma_interfaz')}
          >
            {Object.entries(idiomasDisponibles).map(([codigo, info]) => (
              <option key={codigo} value={codigo}>
                {info.nativo}
              </option>
            ))}
          </select>
        </div>

        {/* Vista lista de compra */}
        <div className="px-4 py-3">
          <div className="flex items-center gap-3 min-h-[44px]">
            <Layers className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
            <span className="flex-1 text-sm">{t('vista_lista_compra_label')}</span>
          </div>
          <div className="flex gap-2 mt-2 pl-[30px]">
            <button
              onClick={() => updatePreferences({ vista_lista_compra: 'lista' })}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-colors text-sm font-medium ${
                preferences.vista_lista_compra === 'lista'
                  ? 'bg-accent text-accent-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              <List className="w-4 h-4" /> {t('vista_lista')}
            </button>
            <button
              onClick={() => updatePreferences({ vista_lista_compra: 'recuadros' })}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-colors text-sm font-medium ${
                preferences.vista_lista_compra === 'recuadros'
                  ? 'bg-accent text-accent-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              <Grid3x3 className="w-4 h-4" /> {t('recuadros')}
            </button>
          </div>
        </div>

        {/* Agrupar por categoría */}
        <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
          <div className="w-[18px] shrink-0" />
          <div className="flex-1">
            <p className="text-sm">{t('agrupar_por_categoria')}</p>
            <p className="text-xs text-muted-foreground">{t('en_listas_compra_y_stock')}</p>
          </div>
          <button
            onClick={() => updatePreferences({ agrupar_categorias: preferences.agrupar_categorias === 'on' ? 'off' : 'on' })}
            className={`relative inline-flex items-center h-8 w-14 rounded-full transition-all duration-300 shrink-0 border-2 ${
              preferences.agrupar_categorias === 'on'
                ? 'bg-accent border-accent shadow-lg shadow-accent/30'
                : 'bg-muted border-border hover:border-muted-foreground'
            }`}
            aria-label={t('agrupar_por_categoria')}
            aria-pressed={preferences.agrupar_categorias === 'on'}
          >
            <span
              className={`absolute top-1.5 left-1.5 w-5 h-5 bg-white rounded-full shadow-md transition-all duration-300 ${
                preferences.agrupar_categorias === 'on' ? 'translate-x-6' : ''
              }`}
            />
          </button>
        </div>
      </div>

      {/* Historial y categorías de gasto — accesos directos que no están en el tab bar móvil */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden divide-y divide-border">
        <Link
          href="/dashboard/historial"
          className="px-4 py-3 flex items-center gap-3 min-h-[44px] hover:bg-muted transition-colors"
        >
          <History className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          <span className="flex-1 text-sm">{t('historial_consumo')}</span>
          <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
        </Link>
        <Link
          href="/dashboard/gastos/categorias"
          className="px-4 py-3 flex items-center gap-3 min-h-[44px] hover:bg-muted transition-colors"
        >
          <Tags className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          <span className="flex-1 text-sm">{t('categorias_gasto')}</span>
          <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
        </Link>
      </div>

      {/* Actividad de la cuenta y sesiones (S-08, S-09) */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden divide-y divide-border">
        <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
          <ShieldCheck className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          <span className="flex-1 text-sm">{t('btn_cerrar_otras_sesiones')}</span>
          <button
            onClick={handleCerrarOtrasSesiones}
            disabled={cerrandoOtrasSesiones}
            className="text-sm font-medium text-accent hover:underline disabled:opacity-50 shrink-0"
          >
            {cerrandoOtrasSesiones ? t('procesando') : t('btn_cerrar_otras_sesiones')}
          </button>
        </div>
        {eventosSeguridad.length > 0 && (
          <div className="px-4 py-3">
            <p className="text-sm font-medium mb-2">{t('titulo_eventos_seguridad')}</p>
            <ul className="space-y-1.5 max-h-48 overflow-y-auto">
              {eventosSeguridad.map((ev, i) => (
                <li key={i} className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{ev.evento}</span>
                  <span className={ev.resultado === 'fallo' ? 'text-red-500' : ''}>
                    {new Date(ev.fecha * 1000).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {/* Exportacion de datos personales (S-22, RGPD) */}
        <div className="px-4 py-3 flex items-center gap-3 min-h-[44px]">
          <History className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
          <span className="flex-1 text-sm">{t('btn_exportar_mis_datos')}</span>
          <button
            onClick={handleExportarMisDatos}
            disabled={exportandoDatos}
            className="text-sm font-medium text-accent hover:underline disabled:opacity-50 shrink-0"
          >
            {exportandoDatos ? t('procesando') : t('btn_exportar_mis_datos')}
          </button>
        </div>
      </div>

      {/* Legal */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden divide-y divide-border">
        {[
          { href: '/legal/aviso-legal', label: t('enlace_aviso_legal') },
          { href: '/legal/privacidad', label: t('enlace_privacidad') },
          { href: '/legal/terminos', label: t('enlace_terminos') },
          { href: '/legal/cookies', label: t('enlace_cookies') },
        ].map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-3 flex items-center gap-3 min-h-[44px] hover:bg-muted transition-colors"
          >
            {href === '/legal/cookies' ? (
              <Cookie className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
            ) : (
              <ScrollText className="w-[18px] h-[18px] text-muted-foreground shrink-0" />
            )}
            <span className="flex-1 text-sm">{label}</span>
            <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
          </Link>
        ))}
      </div>

      {/* Grupo: Zona de riesgo */}
      <div className="rounded-2xl border border-red-200 dark:border-red-900 bg-card overflow-hidden divide-y divide-red-200 dark:divide-red-900">
        <div className="px-4 py-3">
          {confirmandoLogout ? (
            <div className="space-y-2">
              <p className="text-sm text-center text-red-700 dark:text-red-300 font-medium">{t('confirmar_cerrar_sesion_pregunta')}</p>
              <div className="flex gap-2">
                <button
                  onClick={handleLogout}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors min-h-[44px]"
                >
                  <LogOut className="w-4 h-4" /> {t('si_cerrar_sesion')}
                </button>
                <button
                  onClick={() => setConfirmandoLogout(false)}
                  className="flex-1 flex items-center justify-center px-4 py-3 bg-muted rounded-xl font-medium transition-colors min-h-[44px]"
                >
                  {t('cancelar')}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 min-h-[44px] text-left text-red-700 dark:text-red-300"
            >
              <LogOut className="w-[18px] h-[18px] shrink-0" />
              <span className="flex-1 text-sm font-medium">{t('cerrar_sesion_titulo')}</span>
            </button>
          )}
        </div>

        <div className="px-4 py-3">
          {confirmandoEliminar ? (
            <div className="space-y-2">
              <p className="text-sm text-center text-red-700 dark:text-red-300 font-medium">
                {t('confirmar_eliminar_cuenta_pregunta')}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleEliminarCuenta}
                  disabled={cargandoEliminar}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 min-h-[44px]"
                >
                  <Trash2 className="w-4 h-4" /> {cargandoEliminar ? t('eliminando') : t('si_eliminar_cuenta')}
                </button>
                <button
                  onClick={() => setConfirmandoEliminar(false)}
                  disabled={cargandoEliminar}
                  className="flex-1 flex items-center justify-center px-4 py-3 bg-muted rounded-xl font-medium transition-colors min-h-[44px]"
                >
                  {t('cancelar')}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={handleEliminarCuenta}
              className="w-full flex items-center gap-3 min-h-[44px] text-left text-red-700 dark:text-red-300"
            >
              <Trash2 className="w-[18px] h-[18px] shrink-0" />
              <span className="flex-1 text-sm font-medium">{t('eliminar_cuenta_titulo')}</span>
            </button>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="text-center py-6 text-sm text-muted-foreground border-t border-border">
        <p>Dreame! v2.0 • {t('subtitulo_app')}</p>
        <p className="text-xs mt-1">{t('footer_copyright')}</p>
      </div>
    </div>
  )
}
