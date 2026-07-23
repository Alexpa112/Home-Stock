'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun, LogOut, AlertCircle, Globe } from 'lucide-react'
import { auth, idiomas as idiomasApi } from '@/lib/api'

export default function SettingsPage() {
  const [darkMode, setDarkMode] = useState(false)
  const [user, setUser] = useState<{ usuario?: string; email?: string | null }>({})
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
        setIdiomasDisponibles(data.idiomas || [])
        setIdiomaActual(data.actual || 'es')
      })
      .catch(() => {})
  }, [])

  const cambiarIdioma = async (codigo: string) => {
    setIdiomaActual(codigo)
    try {
      await idiomasApi.cambiar(codigo)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cambiar el idioma')
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
    if (!confirm('¿Cerrar sesión?')) return

    try {
      await auth.logout()
      window.location.href = '/'
    } catch (err) {
      setError('Error al cerrar sesión')
      console.error(err)
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
              aria-label="Toggle dark mode"
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
          <select
            value={idiomaActual}
            onChange={(e) => cambiarIdioma(e.target.value)}
            className="input-field"
          >
            {Object.entries(idiomasDisponibles).map(([codigo, info]) => (
              <option key={codigo} value={codigo}>
                {info.nombre}
              </option>
            ))}
          </select>
          <p className="text-sm text-muted-foreground">
            Se guarda tu preferencia; los textos de esta nueva interfaz siguen en español por ahora.
          </p>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="card space-y-4 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30">
        <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">Zona de Riesgo</h2>

        <div className="border-t border-red-200 dark:border-red-900 pt-4">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors min-h-[44px]"
          >
            <LogOut className="w-5 h-5" />
            Cerrar Sesión
          </button>

          <p className="text-sm text-red-600 dark:text-red-400 mt-3 text-center">
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
