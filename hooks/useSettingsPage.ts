'use client'

import { useEffect, useState } from 'react'
import { auth, idiomas as idiomasApi } from '@/lib/api'
import { getErrorMessage } from '@/lib/error-utils'
import { useAuth } from '@/hooks/useAuth'
import { logoutAndRedirect } from '@/lib/session'

interface IdiomasResponse {
  idiomas?: Record<string, { nombre: string; nativo: string }>
  actual?: string
}

export function useSettingsPage() {
  const { user, loading: userLoading } = useAuth()
  const [darkMode, setDarkMode] = useState(false)
  const [error, setError] = useState('')
  const [idiomasDisponibles, setIdiomasDisponibles] = useState<Record<string, { nombre: string; nativo: string }>>({})
  const [idiomaActual, setIdiomaActual] = useState('es')

  useEffect(() => {
    setDarkMode(document.documentElement.classList.contains('dark'))

    void idiomasApi
      .disponibles()
      .then((data) => {
        const idiomas = data as IdiomasResponse
        setIdiomasDisponibles(idiomas.idiomas || {})
        setIdiomaActual(idiomas.actual || 'es')
      })
      .catch((err) => setError(getErrorMessage(err, 'Error al cargar idiomas')))
  }, [])

  useEffect(() => {
    if (!user) return

    const pref = user.tema_preferido || 'auto'
    const aplicarOscuro = pref === 'dark' || (pref === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    setDarkMode(aplicarOscuro)
    document.documentElement.classList.toggle('dark', aplicarOscuro)
    setIdiomaActual(user.idioma_preferido || 'es')
  }, [user])

  const cambiarIdioma = async (codigo: string) => {
    const previo = idiomaActual
    setIdiomaActual(codigo)

    try {
      await idiomasApi.cambiar(codigo)
    } catch (err) {
      setIdiomaActual(previo)
      setError(getErrorMessage(err, 'Error al cambiar el idioma'))
    }
  }

  const toggleDarkMode = async () => {
    const nextDarkMode = !darkMode
    setDarkMode(nextDarkMode)
    document.documentElement.classList.toggle('dark', nextDarkMode)
    window.localStorage.setItem('theme', nextDarkMode ? 'dark' : 'light')

    try {
      await auth.cambiarTema(nextDarkMode ? 'dark' : 'light')
    } catch (err) {
      setError(getErrorMessage(err, 'Error al guardar el tema'))
    }
  }

  const handleLogout = async () => {
    try {
      await logoutAndRedirect()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al cerrar sesión'))
    }
  }

  return {
    cambiarIdioma,
    darkMode,
    error,
    handleLogout,
    idiomaActual,
    idiomasDisponibles,
    toggleDarkMode,
    user,
    userLoading,
  }
}
