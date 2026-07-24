'use client'

import { Globe, LogOut, Moon, Sun } from 'lucide-react'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useSettingsPage } from '@/hooks/useSettingsPage'

export default function SettingsPage() {
  const {
    cambiarIdioma,
    darkMode,
    error,
    handleLogout,
    idiomaActual,
    idiomasDisponibles,
    toggleDarkMode,
    user,
    userLoading,
  } = useSettingsPage()

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">Ajustes</h1>
        <p className="text-muted-foreground mt-1">Personaliza tu experiencia</p>
      </div>

      {error && <StatusMessage title="Error" message={error} />}

      <div className="card space-y-4">
        <h2 className="text-lg font-semibold">Cuenta</h2>
        <div className="space-y-3 border-t border-border pt-4">
          <div>
            <label className="text-sm text-muted-foreground">Usuario</label>
            <p className="text-foreground font-medium mt-1">{userLoading ? 'Cargando...' : user?.usuario || 'Sin sesión'}</p>
          </div>
          {user?.email && (
            <div>
              <label className="text-sm text-muted-foreground">Correo Electrónico</label>
              <p className="text-foreground font-medium mt-1">{user.email}</p>
            </div>
          )}
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="text-lg font-semibold">Apariencia</h2>
        <div className="border-t border-border pt-4">
          <div className="flex items-center justify-between mb-4 min-h-[44px]">
            <div className="flex items-center gap-3">
              {darkMode ? <Moon className="w-5 h-5 text-accent" /> : <Sun className="w-5 h-5 text-accent" />}
              <div>
                <p className="font-medium">Modo Oscuro</p>
                <p className="text-sm text-muted-foreground">{darkMode ? 'Activado' : 'Desactivado'}</p>
              </div>
            </div>

            <button
              onClick={toggleDarkMode}
              className={`relative inline-flex items-center h-8 w-14 rounded-full transition-colors min-h-[44px] min-w-[44px] justify-center ${darkMode ? 'bg-accent' : 'bg-muted'}`}
              aria-label="Toggle dark mode"
            >
              <div className={`absolute left-1 w-6 h-6 bg-white rounded-full transition-transform ${darkMode ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          <p className="text-sm text-muted-foreground">El cambio de tema se aplica inmediatamente en toda la aplicación</p>
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Globe className="w-5 h-5 text-accent" /> Idioma
        </h2>
        <div className="border-t border-border pt-4 space-y-2">
          <select value={idiomaActual} onChange={(e) => cambiarIdioma(e.target.value)} className="input-field">
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

      <div className="card space-y-4 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30">
        <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">Zona de Riesgo</h2>
        <div className="border-t border-red-200 dark:border-red-900 pt-4">
          <button
            onClick={() => confirm('¿Cerrar sesión?') && handleLogout()}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors min-h-[44px]"
          >
            <LogOut className="w-5 h-5" />
            Cerrar Sesión
          </button>
          <p className="text-sm text-red-600 dark:text-red-400 mt-3 text-center">Se cerrará tu sesión en este dispositivo</p>
        </div>
      </div>

      <div className="text-center py-6 text-sm text-muted-foreground border-t border-border">
        <p>Dreame! v2.0 • Inventario del Hogar</p>
        <p className="text-xs mt-1">© 2024 Todos los derechos reservados</p>
      </div>
    </div>
  )
}
