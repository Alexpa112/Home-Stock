'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun, LogOut, AlertCircle, Globe, History, Grid3x3, List, Layers, Eye, EyeOff, Lock, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { auth, idiomas as idiomasApi } from '@/lib/api'
import { useListPreferences } from '@/contexts/ListPreferencesContext'

export default function SettingsPage() {
  const { preferences, updatePreferences } = useListPreferences()
  const [darkMode, setDarkMode] = useState(false)
  const [user, setUser] = useState<{ usuario?: string; email?: string | null; id?: number }>({})
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
    setIdiomaActual(codigo)
    try {
      await idiomasApi.cambiar(codigo)
      localStorage.setItem('idioma_preferido', codigo)
      setTimeout(() => {
        window.location.reload()
      }, 300)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cambiar el idioma')
      setIdiomaActual(idiomaActual)
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
      setError('Error al cerrar sesión')
      setConfirmandoLogout(false)
    }
  }

  const handleActualizarNombre = async () => {
    if (!nuevoNombre.trim()) {
      setError('El nombre de usuario no puede estar vacío')
      return
    }
    setCargandoNombre(true)
    setError('')
    setExito('')
    try {
      await auth.actualizarPerfil({ nombre: nuevoNombre })
      setUser({ ...user, usuario: nuevoNombre })
      setEditandoNombre(false)
      setExito('Nombre de usuario actualizado correctamente')
      setTimeout(() => setExito(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al actualizar el nombre')
    } finally {
      setCargandoNombre(false)
    }
  }

  const handleCambiarPassword = async () => {
    if (!passwordActual || !passwordNueva || !passwordConfirmacion) {
      setError('Todos los campos son obligatorios')
      return
    }
    if (passwordNueva !== passwordConfirmacion) {
      setError('Las nuevas contraseñas no coinciden')
      return
    }
    if (passwordNueva.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
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
      setExito('Contraseña cambiada correctamente')
      setTimeout(() => setExito(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cambiar la contraseña')
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
      setError(err instanceof Error ? err.message : 'Error al eliminar la cuenta')
      setConfirmandoEliminar(false)
      setCargandoEliminar(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">Ajustes</h1>
        <p className="text-muted-foreground mt-1">Personaliza tu experiencia</p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Error</p>
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
        <h2 className="text-lg font-semibold">Cuenta</h2>

        <div className="space-y-4 border-t border-border pt-4">
          <div>
            <label className="text-sm text-muted-foreground">Usuario</label>
            {editandoNombre ? (
              <div className="space-y-2 mt-2">
                <input
                  type="text"
                  value={nuevoNombre}
                  onChange={(e) => setNuevoNombre(e.target.value)}
                  className="input-field"
                  placeholder="Nuevo nombre de usuario"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleActualizarNombre}
                    disabled={cargandoNombre}
                    className="flex-1 px-3 py-2 bg-accent text-white rounded-lg font-medium transition-colors disabled:opacity-50 min-h-[44px]"
                  >
                    {cargandoNombre ? 'Guardando...' : 'Guardar'}
                  </button>
                  <button
                    onClick={() => {
                      setEditandoNombre(false)
                      setNuevoNombre(user.usuario || '')
                    }}
                    disabled={cargandoNombre}
                    className="flex-1 px-3 py-2 bg-muted rounded-lg font-medium transition-colors min-h-[44px]"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between mt-1">
                <p className="text-foreground font-medium">{user.usuario || 'Cargando...'}</p>
                <button
                  onClick={() => setEditandoNombre(true)}
                  className="text-sm text-accent hover:underline"
                >
                  Editar
                </button>
              </div>
            )}
          </div>

          {user.email && (
            <div>
              <label className="text-sm text-muted-foreground">Correo Electrónico</label>
              <p className="text-foreground font-medium mt-1">{user.email}</p>
            </div>
          )}

          <div className="border-t border-border pt-4">
            <button
              onClick={() => setEditandoPassword(!editandoPassword)}
              className="w-full flex items-center gap-2 px-4 py-3 rounded-lg bg-muted hover:bg-muted/80 transition-colors font-medium min-h-[44px]"
            >
              <Lock className="w-4 h-4" />
              Cambiar Contraseña
            </button>

            {editandoPassword && (
              <div className="space-y-3 mt-4 pt-4 border-t border-border">
                <div>
                  <label className="text-sm text-muted-foreground">Contraseña Actual</label>
                  <div className="relative mt-1">
                    <input
                      type={mostrarPassword.actual ? 'text' : 'password'}
                      value={passwordActual}
                      onChange={(e) => setPasswordActual(e.target.value)}
                      className="input-field pr-10"
                      placeholder="Tu contraseña actual"
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
                  <label className="text-sm text-muted-foreground">Nueva Contraseña</label>
                  <div className="relative mt-1">
                    <input
                      type={mostrarPassword.nueva ? 'text' : 'password'}
                      value={passwordNueva}
                      onChange={(e) => setPasswordNueva(e.target.value)}
                      className="input-field pr-10"
                      placeholder="Mínimo 8 caracteres"
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
                  <label className="text-sm text-muted-foreground">Confirmar Nueva Contraseña</label>
                  <div className="relative mt-1">
                    <input
                      type={mostrarPassword.confirmacion ? 'text' : 'password'}
                      value={passwordConfirmacion}
                      onChange={(e) => setPasswordConfirmacion(e.target.value)}
                      className="input-field pr-10"
                      placeholder="Confirma tu nueva contraseña"
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
                    {cargandoPassword ? 'Cambiando...' : 'Cambiar Contraseña'}
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
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Theme Section */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold">Apariencia</h2>

        <div className="border-t border-border pt-4">
          <div className="flex items-center justify-between mb-4 min-h-[44px]">
            <div className="flex items-center gap-3">
              {darkMode ? (
                <Moon className="w-5 h-5 text-accent" />
              ) : (
                <Sun className="w-5 h-5 text-accent" />
              )}
              <div>
                <p className="font-medium">Modo Oscuro</p>
                <p className="text-sm text-muted-foreground">
                  {darkMode ? 'Activado' : 'Desactivado'}
                </p>
              </div>
            </div>

            <button
              onClick={toggleDarkMode}
              className={`relative inline-flex items-center h-8 w-14 rounded-full transition-colors min-h-[44px] min-w-[44px] justify-center ${
                darkMode ? 'bg-accent' : 'bg-muted'
              }`}
              aria-label={darkMode ? 'Desactivar modo oscuro' : 'Activar modo oscuro'}
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
            El cambio de tema se aplica inmediatamente en toda la aplicación
          </p>
        </div>
      </div>

      {/* Idioma */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Globe className="w-5 h-5 text-accent" /> Idioma
        </h2>
        <div className="border-t border-border pt-4 space-y-2">
          <label htmlFor="sel-idioma" className="sr-only">Idioma de la interfaz</label>
          <select
            id="sel-idioma"
            value={idiomaActual}
            onChange={(e) => cambiarIdioma(e.target.value)}
            className="input-field"
          >
            {Object.entries(idiomasDisponibles).map(([codigo, info]) => (
              <option key={codigo} value={codigo}>
                {info.nombre} - {info.nativo}
              </option>
            ))}
          </select>
          <p className="text-sm text-muted-foreground">
            Se guarda tu preferencia; los textos de esta nueva interfaz siguen en español por ahora.
          </p>
        </div>
      </div>

      {/* Preferencias de Listas */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Layers className="w-5 h-5 text-accent" /> Preferencias de Listas
        </h2>
        <div className="border-t border-border pt-4 space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-3">Vista de la lista de compra</p>
            <div className="flex gap-2">
              <button
                onClick={() => updatePreferences({ vista_lista_compra: 'lista' })}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-colors text-sm font-medium ${
                  preferences.vista_lista_compra === 'lista'
                    ? 'bg-accent text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                <List className="w-4 h-4" /> Lista
              </button>
              <button
                onClick={() => updatePreferences({ vista_lista_compra: 'recuadros' })}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-colors text-sm font-medium ${
                  preferences.vista_lista_compra === 'recuadros'
                    ? 'bg-accent text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                <Grid3x3 className="w-4 h-4" /> Recuadros
              </button>
            </div>
          </div>

          <div className="border-t border-border pt-4">
            <label className="flex items-center justify-between">
              <div>
                <p className="font-medium">Agrupar por categoría</p>
                <p className="text-sm text-muted-foreground">En listas de compra y stock</p>
              </div>
              <button
                onClick={() => updatePreferences({ agrupar_categorias: preferences.agrupar_categorias === 'on' ? 'off' : 'on' })}
                className={`relative inline-flex items-center h-8 w-14 rounded-full transition-colors min-h-[44px] min-w-[44px] justify-center ${
                  preferences.agrupar_categorias === 'on' ? 'bg-accent' : 'bg-muted'
                }`}
                aria-label="Agrupar por categoría"
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
          <p className="font-medium">Historial de consumo</p>
          <p className="text-sm text-muted-foreground">Ver los productos más consumidos y el catálogo aprendido</p>
        </div>
      </Link>

      {/* Danger Zone */}
      <div className="card space-y-4 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30">
        <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">Zona de Riesgo</h2>

        <div className="border-t border-red-200 dark:border-red-900 pt-4 space-y-4">
          {/* Logout */}
          <div>
            {confirmandoLogout ? (
              <div className="space-y-2">
                <p className="text-sm text-center text-red-700 dark:text-red-300 font-medium">¿Seguro que quieres cerrar sesión?</p>
                <div className="flex gap-2">
                  <button
                    onClick={handleLogout}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors min-h-[44px]"
                  >
                    <LogOut className="w-4 h-4" /> Sí, cerrar sesión
                  </button>
                  <button
                    onClick={() => setConfirmandoLogout(false)}
                    className="flex-1 flex items-center justify-center px-4 py-3 bg-muted rounded-xl font-medium transition-colors min-h-[44px]"
                  >
                    Cancelar
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
                  Cerrar Sesión
                </button>
                <p className="text-sm text-red-600 dark:text-red-400 text-center mt-2">
                  Se cerrará tu sesión en este dispositivo
                </p>
              </>
            )}
          </div>

          <div className="border-t border-red-200 dark:border-red-900 pt-4">
            {confirmandoEliminar ? (
              <div className="space-y-2">
                <p className="text-sm text-center text-red-700 dark:text-red-300 font-medium">
                  ¿Estás seguro? Esta acción no puede deshacerse. Se eliminarán todos tus datos.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={handleEliminarCuenta}
                    disabled={cargandoEliminar}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 min-h-[44px]"
                  >
                    <Trash2 className="w-4 h-4" /> {cargandoEliminar ? 'Eliminando...' : 'Sí, eliminar cuenta'}
                  </button>
                  <button
                    onClick={() => setConfirmandoEliminar(false)}
                    disabled={cargandoEliminar}
                    className="flex-1 flex items-center justify-center px-4 py-3 bg-muted rounded-xl font-medium transition-colors min-h-[44px]"
                  >
                    Cancelar
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
                  Eliminar Cuenta
                </button>
                <p className="text-sm text-red-600 dark:text-red-400 text-center mt-2">
                  Esta acción es irreversible. Se eliminarán permanentemente todos tus datos.
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="text-center py-6 text-sm text-muted-foreground border-t border-border">
        <p>Dreame! v2.0 • Inventario del Hogar</p>
        <p className="text-xs mt-1">© 2024 Todos los derechos reservados</p>
      </div>
    </div>
  )
}
