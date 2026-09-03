'use client'

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import TRADUCCIONES_BASE from '@/lib/traduccionesBase'

interface TranslationContextType {
  idioma: string
  traducciones: Record<string, string>
  cargando: boolean
  t: (clave: string) => string
  cambiarIdioma: (idioma: string) => void
}

const TranslationContext = createContext<TranslationContextType | undefined>(undefined)

const CACHE_KEY_PREFIX = 'traducciones_cache_'

function leerCache(idioma: string): Record<string, string> | null {
  if (typeof window === 'undefined') return null
  try {
    const bruto = localStorage.getItem(CACHE_KEY_PREFIX + idioma)
    return bruto ? JSON.parse(bruto) : null
  } catch {
    return null
  }
}

function guardarCache(idioma: string, traducciones: Record<string, string>) {
  try {
    localStorage.setItem(CACHE_KEY_PREFIX + idioma, JSON.stringify(traducciones))
  } catch {
    // localStorage puede fallar (modo privado, cuota); no es crítico
  }
}

export function TranslationProvider({ children }: { children: React.ReactNode }) {
  // Idioma/caché previos (si los hay) para evitar el parpadeo de claves sin
  // traducir mientras se confirma el idioma real con el backend.
  const idiomaInicial = typeof window !== 'undefined' ? (localStorage.getItem('idioma_preferido') || 'es') : 'es'
  const [idioma, setIdioma] = useState(idiomaInicial)
  // TRADUCCIONES_BASE (español, empaquetado) como punto de partida: la caché
  // solo existe en visitas repetidas, así que sin él la PRIMERA carga —y todo
  // el HTML que genera el servidor, que no tiene localStorage— salía con las
  // claves en crudo hasta que respondía /api/idiomas/todos/<idioma>. Eso se
  // veía en pantalla y además rompía la hidratación de React (#418) en todas
  // las páginas, porque el texto del servidor no coincidía con el del cliente.
  const [traducciones, setTraducciones] = useState<Record<string, string>>(
    () => leerCache(idiomaInicial) || TRADUCCIONES_BASE
  )
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
        document.documentElement.lang = idiomaActual

        // Cargar todas las traducciones para ese idioma
        const respuestaTraducciones = await fetch(`/api/idiomas/todos/${idiomaActual}`, { credentials: 'include' })
        const datosTraducciones = await respuestaTraducciones.json()
        const nuevasTraducciones = datosTraducciones.traducciones || {}
        setTraducciones(nuevasTraducciones)
        guardarCache(idiomaActual, nuevasTraducciones)
      } catch (err) {
        console.error('Error cargando traducciones:', err)
      } finally {
        setCargando(false)
      }
    }

    cargarTraducciones()
  }, [])

  // t() y cambiarIdioma() van memoizados, y el value tambien: al recrearse en
  // cada render, cualquier efecto o useCallback que los llevara en sus
  // dependencias se reejecutaba sin motivo. El caso concreto que se veia:
  // HogarContext.cargar dependia de [t], asi que cada render de este provider
  // provocaba otra peticion a /api/hogares y, con ella, el spinner de pantalla
  // completa del dashboard.
  const t = useCallback(
    // Si al idioma activo le falta una clave, se cae al español antes que a la
    // clave: el usuario prefiere leer "Guardar" a leer "btn_guardar".
    (clave: string): string => traducciones[clave] || TRADUCCIONES_BASE[clave] || clave,
    [traducciones]
  )

  const cambiarIdioma = useCallback(async (nuevoIdioma: string) => {
    try {
      const cache = leerCache(nuevoIdioma)
      if (cache) setTraducciones(cache)

      const respuesta = await fetch(`/api/idiomas/todos/${nuevoIdioma}`, { credentials: 'include' })
      const datos = await respuesta.json()
      const nuevasTraducciones = datos.traducciones || {}
      setTraducciones(nuevasTraducciones)
      guardarCache(nuevoIdioma, nuevasTraducciones)
      setIdioma(nuevoIdioma)
      document.documentElement.lang = nuevoIdioma
      localStorage.setItem('idioma_preferido', nuevoIdioma)
    } catch (err) {
      console.error('Error cambiando idioma:', err)
    }
  }, [])

  const valor = useMemo(
    () => ({ idioma, traducciones, cargando, t, cambiarIdioma }),
    [idioma, traducciones, cargando, t, cambiarIdioma]
  )

  return <TranslationContext.Provider value={valor}>{children}</TranslationContext.Provider>

}

export function useTranslation() {
  const context = useContext(TranslationContext)
  if (!context) {
    throw new Error('useTranslation debe usarse dentro de TranslationProvider')
  }
  return context
}
