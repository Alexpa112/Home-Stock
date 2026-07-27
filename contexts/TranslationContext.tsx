'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

interface TranslationContextType {
  idioma: string
  traducciones: Record<string, string>
  cargando: boolean
  t: (clave: string) => string
  cambiarIdioma: (idioma: string) => void
}

const TranslationContext = createContext<TranslationContextType | undefined>(undefined)

export function TranslationProvider({ children }: { children: React.ReactNode }) {
  const [idioma, setIdioma] = useState('es')
  const [traducciones, setTraducciones] = useState<Record<string, string>>({})
  const [cargando, setCargando] = useState(true)

  // Cargar idioma guardado y traducciones
  useEffect(() => {
    const cargarTraducciones = async () => {
      try {
        // Obtener idioma actual desde el backend
        const respuestaIdioma = await fetch('/api/idiomas/obtener', { credentials: 'include' })
        const datosIdioma = await respuestaIdioma.json()
        const idiomaActual = datosIdioma.idioma || 'es'
        setIdioma(idiomaActual)

        // Cargar todas las traducciones para ese idioma
        const respuestaTraducciones = await fetch(`/api/idiomas/todos/${idiomaActual}`, { credentials: 'include' })
        const datosTraducciones = await respuestaTraducciones.json()
        setTraducciones(datosTraducciones.traducciones || {})
      } catch (err) {
        console.error('Error cargando traducciones:', err)
      } finally {
        setCargando(false)
      }
    }

    cargarTraducciones()
  }, [])

  const t = (clave: string): string => {
    return traducciones[clave] || clave
  }

  const cambiarIdioma = (nuevoIdioma: string) => {
    setIdioma(nuevoIdioma)
    localStorage.setItem('idioma_preferido', nuevoIdioma)
    // Recargar para aplicar las nuevas traducciones
    window.location.reload()
  }

  return (
    <TranslationContext.Provider value={{ idioma, traducciones, cargando, t, cambiarIdioma }}>
      {children}
    </TranslationContext.Provider>
  )
}

export function useTranslation() {
  const context = useContext(TranslationContext)
  if (!context) {
    throw new Error('useTranslation debe usarse dentro de TranslationProvider')
  }
  return context
}
