'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun, LogOut, AlertCircle, Globe, History, Grid3x3, List, Layers } from 'lucide-react'
import Link from 'next/link'
import { auth, idiomas as idiomasApi } from '@/lib/api'
import { useListPreferences } from '@/contexts/ListPreferencesContext'

export default function SettingsPage() {
  const { preferences, updatePreferences } = useListPreferences()
  const [darkMode, setDarkMode] = useState(false)
  const [user, setUser] = useState<{ usuario?: string; email?: string | null }>({})
  const [confirmandoLogout, setConfirmandoLogout] = useState(false)
  const [error, setError] = useState('')
  // idiomas.disponibles() devuelve un diccionario {codigo: {nombre, nativo}},
  // no un array (ver stockhogar/translator.py:obtener_idiomas).
  const [idiomasDisponibles, setIdiomasDisponibles] = useState<Record<string, { nombre: string; nativo: string }>>({})
  const [idiomaActual, setIdiomaActual] = useState('es')

  useEffect(() => {
    // Preferencia visual inmediata (evita parpadeo) mientras llega la real
    // del backend en loadUser().
    const isDark = document.documentElement.classList.contains('dark')
    setDarkMode(isDark)

    // Cargar datos del usuario (incluye tema_preferido real del backend)
    loadUser()

    // Nota: el resto de la interfaz sigue solo en español por ahora; esto
    // permite elegir y persistir el idioma preferido (sesion + BD), listo
    // para cuando se traduzcan los textos de la UI.
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
      // Guardar preferencia localmente y recargar para aplicar traducc. a toda la app
      localStorage.setItem('idioma_preferido', codigo)
      setTimeout(() => {
        window.location.reload()
      }, 300)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cambiar el idioma')
      setIdiomaActual(idiomaActual) // Revertir en la UI si falla
    }
  }

  const loadUser = async () => {
    try {
      const response = await fetch('/api/auth/estado', {
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setUser({ usuario: data.usuario, email: data.email })

        // tema_preferido puede ser 'light'/'dark'/'auto'; 'auto' sigue la
        // preferencia del sistema. Esta UI simplificada solo expone un
        // toggle binario, pero respeta lo guardado en el backend al cargar.
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

      {/* Account Section */}
      <div className="card space-y-4">
        <h2 className="text-lg font-semibold">Cuenta</h2>
        
        <div className="space-y-3 border-t border-border pt-4">
          <div>
            <label className="text-sm text-muted-foreground">Usuario</label>
            <p className="text-foreground font-medium mt-1">{user.usuario || 'Cargando...'}</p>
          </div>
          {user.email && (
            <div>
              <label className="text-sm text-muted-foreground">Correo Electrónico</label>
              <p className="text-foreground font-medium mt-1">{user.email}</p>
            </div>
          )}
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

        <div className="border-t border-red-200 dark:border-red-900 pt-4 space-y-2">
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
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors min-h-[44px]"
            >
              <LogOut className="w-5 h-5" />
              Cerrar Sesión
            </button>
          )}
          <p className="text-sm text-red-600 dark:text-red-400 text-center">
            Se cerrará tu sesión en este dispositivo
          </p>
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
