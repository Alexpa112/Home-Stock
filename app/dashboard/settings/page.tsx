'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun, LogOut, AlertCircle, Globe, History, Grid3x3, List, Layers, Eye, EyeOff, Lock, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { auth, idiomas as idiomasApi } from '@/lib/api'
import { useListPreferences } from '@/contexts/ListPreferencesContext'
import { useTranslation } from '@/contexts/TranslationContext'

export default function SettingsPage() {
  const { preferences, updatePreferences } = useListPreferences()
  const { t, cambiarIdioma: aplicarIdiomaContexto } = useTranslation()
  const [darkMode, setDarkMode] = useState(false)
  const [user, setUser] = useState<{ usuario?: string; email?: string | null; id?: number }>({})
  const [dobleFactorActivo, setDobleFactorActivo] = useState(false)
  const [cargandoDobleFactor, setCargandoDobleFactor] = useState(false)
  const [confirmandoLogout, setConfirmandoLogout] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')
  const [idiomasDisponibles, setIdiomasDisponibles] = useState<Record<string, { nombre: string; nativo: string }>>({})
  const [idiomaActual, setIdiomaActual] = useState('es')

  // Estado para editar nombre de usuario
  const [editandoNombre, setEditandoNombre] = useState(false)
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [cargandoNombre, setCargandoNombre] = useState(false)

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
        setUser({ usuario: data.usuario, email: data.email, id: data.usuario_id })
        setNuevoNombre(data.usuario || '')
        setDobleFactorActivo(!!data.doble_factor_activo)

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

  const handleActualizarNombre = async () => {
    if (!nuevoNombre.trim()) {
      setError(t('err_nombre_usuario_vacio'))
      return
    }
    setCargandoNombre(true)
    setError('')
    setExito('')
    try {
      await auth.actualizarPerfil({ nombre: nuevoNombre })
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

  const handleCambiarPassword = async () => {
    if (!passwordActual || !passwordNueva || !passwordConfirmacion) {
      setError(t('err_campos_obligatorios'))
      return
    }
    if (passwordNueva !== passwordConfirmacion) {
      setError(t('error_contrasenas_no_coinciden'))
      return
    }
    if (passwordNueva.length < 8) {
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

      {/* Account Section */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold">{t('seccion_cuenta')}</h2>

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <label className="text-sm text-muted-foreground">{t('usuario')}</label>
            {editandoNombre ? (
              <div className="space-y-2 mt-2">
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
                    className="flex-1 px-3 py-2 bg-accent text-white rounded-lg font-medium transition-colors disabled:opacity-50 min-h-[44px]"
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
              <div className="flex items-center justify-between mt-1">
                <p className="text-foreground font-medium">{user.usuario || t('cargando')}</p>
                <button
                  onClick={() => setEditandoNombre(true)}
                  className="text-sm text-accent hover:underline"
                >
                  {t('editar')}
                </button>
              </div>
            )}
          </div>

          {user.email && (
            <div>
              <label className="text-sm text-muted-foreground">{t('correo_electronico')}</label>
              <p className="text-foreground font-medium mt-1">{user.email}</p>
            </div>
          )}

          <div className="border-t border-border pt-4 flex items-center justify-between gap-4">
            <div>
              <p className="font-medium">{t('doble_factor_titulo')}</p>
              <p className="text-sm text-muted-foreground mt-0.5">
                {user.email ? t('doble_factor_descripcion') : t('err_doble_factor_requiere_email')}
              </p>
            </div>
            <button
              onClick={() => cambiarDobleFactor(!dobleFactorActivo)}
              disabled={!user.email || cargandoDobleFactor}
              role="switch"
              aria-checked={dobleFactorActivo}
              aria-label={t('doble_factor_titulo')}
              className={`relative w-12 h-7 rounded-full transition-colors shrink-0 disabled:opacity-40 ${dobleFactorActivo ? 'bg-accent' : 'bg-muted'}`}
            >
              <span
                className={`absolute top-1 left-1 w-5 h-5 rounded-full bg-white shadow transition-transform ${dobleFactorActivo ? 'translate-x-5' : ''}`}
              />
            </button>
          </div>

          <div className="border-t border-border pt-4">
            <button
              onClick={() => setEditandoPassword(!editandoPassword)}
              className="w-full flex items-center gap-2 px-4 py-3 rounded-lg bg-muted hover:bg-muted/80 transition-colors font-medium min-h-[44px]"
            >
              <Lock className="w-4 h-4" />
              {t('btn_cambiar_password')}
            </button>

            {editandoPassword && (
              <div className="space-y-3 mt-4 pt-4 border-t border-border">
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
                      onClick={() => setMostrarPassword({ ...mostrarPassword, actual: !mostrarPassword.actual })}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      tabIndex={-1}
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
                      onClick={() => setMostrarPassword({ ...mostrarPassword, nueva: !mostrarPassword.nueva })}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      tabIndex={-1}
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
                      onClick={() => setMostrarPassword({ ...mostrarPassword, confirmacion: !mostrarPassword.confirmacion })}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      tabIndex={-1}
                    >
                      {mostrarPassword.confirmacion ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={handleCambiarPassword}
                    disabled={cargandoPassword}
                    className="flex-1 px-3 py-3 bg-accent text-white rounded-lg font-medium transition-colors disabled:opacity-50 min-h-[44px]"
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
      </div>

      {/* Theme Section */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold">{t('seccion_apariencia')}</h2>

        <div className="border-t border-border pt-4">
          <div className="flex items-center justify-between mb-4 min-h-[44px]">
            <div className="flex items-center gap-3">
              {darkMode ? (
                <Moon className="w-5 h-5 text-accent" />
              ) : (
                <Sun className="w-5 h-5 text-accent" />
              )}
              <div>
                <p className="font-medium">{t('modo_oscuro')}</p>
                <p className="text-sm text-muted-foreground">
                  {darkMode ? t('activado') : t('desactivado')}
                </p>
              </div>
            </div>

            <button
              onClick={toggleDarkMode}
              className={`relative inline-flex items-center h-8 w-14 rounded-full transition-colors min-h-[44px] min-w-[44px] justify-center ${
                darkMode ? 'bg-accent' : 'bg-muted'
              }`}
              aria-label={darkMode ? t('aria_desactivar_modo_oscuro') : t('aria_activar_modo_oscuro')}
              aria-pressed={darkMode}
            >
              <div
                className={`absolute left-1 w-6 h-6 bg-white rounded-full transition-transform ${
                  darkMode ? 'translate-x-6' : ''
                }`}
              />
            </button>
          </div>

          <p className="text-sm text-muted-foreground">
            {t('nota_tema_inmediato')}
          </p>
        </div>
      </div>

      {/* Idioma */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Globe className="w-5 h-5 text-accent" /> {t('idioma')}
        </h2>
        <div className="border-t border-border pt-4 space-y-2">
          <label htmlFor="sel-idioma" className="sr-only">{t('aria_idioma_interfaz')}</label>
          <select
            id="sel-idioma"
            value={idiomaActual}
            onChange={(e) => cambiarIdioma(e.target.value)}
            className="input-field"
          >
            {Object.entries(idiomasDisponibles).map(([codigo, info]) => (
              <option key={codigo} value={codigo}>
                {info.nativo}
              </option>
            ))}
          </select>
          <p className="text-sm text-muted-foreground">
            {t('nota_idioma_completo')}
          </p>
        </div>
      </div>

      {/* Preferencias de Listas */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Layers className="w-5 h-5 text-accent" /> {t('seccion_preferencias_listas')}
        </h2>
        <div className="border-t border-border pt-4 space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-3">{t('vista_lista_compra_label')}</p>
            <div className="flex gap-2">
              <button
                onClick={() => updatePreferences({ vista_lista_compra: 'lista' })}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-colors text-sm font-medium ${
                  preferences.vista_lista_compra === 'lista'
                    ? 'bg-accent text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                <List className="w-4 h-4" /> {t('vista_lista')}
              </button>
              <button
                onClick={() => updatePreferences({ vista_lista_compra: 'recuadros' })}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-colors text-sm font-medium ${
                  preferences.vista_lista_compra === 'recuadros'
                    ? 'bg-accent text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                <Grid3x3 className="w-4 h-4" /> {t('recuadros')}
              </button>
            </div>
          </div>

          <div className="border-t border-border pt-4">
            <label className="flex items-center justify-between">
              <div>
                <p className="font-medium">{t('agrupar_por_categoria')}</p>
                <p className="text-sm text-muted-foreground">{t('en_listas_compra_y_stock')}</p>
              </div>
              <button
                onClick={() => updatePreferences({ agrupar_categorias: preferences.agrupar_categorias === 'on' ? 'off' : 'on' })}
                className={`relative inline-flex items-center h-8 w-14 rounded-full transition-colors min-h-[44px] min-w-[44px] justify-center ${
                  preferences.agrupar_categorias === 'on' ? 'bg-accent' : 'bg-muted'
                }`}
                aria-label={t('agrupar_por_categoria')}
                aria-pressed={preferences.agrupar_categorias === 'on'}
              >
                <div
                  className={`absolute left-1 w-6 h-6 bg-white rounded-full transition-transform ${
                    preferences.agrupar_categorias === 'on' ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </label>
          </div>
        </div>
      </div>

      {/* Historial — acceso directo ya que no está en el tab bar móvil */}
      <Link
        href="/dashboard/historial"
        className="card flex items-center gap-3 hover:bg-muted transition-colors"
      >
        <History className="w-5 h-5 text-accent shrink-0" />
        <div>
          <p className="font-medium">{t('historial_consumo')}</p>
          <p className="text-sm text-muted-foreground">{t('ver_productos_consumidos')}</p>
        </div>
      </Link>

      {/* Danger Zone */}
      <div className="card space-y-4 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30">
        <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">{t('zona_riesgo')}</h2>

        <div className="border-t border-red-200 dark:border-red-900 pt-4 space-y-4">
          {/* Logout */}
          <div>
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
              <>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors min-h-[44px]"
                >
                  <LogOut className="w-5 h-5" />
                  {t('cerrar_sesion_titulo')}
                </button>
                <p className="text-sm text-red-600 dark:text-red-400 text-center mt-2">
                  {t('nota_cerrar_sesion_dispositivo')}
                </p>
              </>
            )}
          </div>

          <div className="border-t border-red-200 dark:border-red-900 pt-4">
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
              <>
                <button
                  onClick={handleEliminarCuenta}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors min-h-[44px]"
                >
                  <Trash2 className="w-5 h-5" />
                  {t('eliminar_cuenta_titulo')}
                </button>
                <p className="text-sm text-red-600 dark:text-red-400 text-center mt-2">
                  {t('nota_eliminar_cuenta_irreversible')}
                </p>
              </>
            )}
          </div>
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
