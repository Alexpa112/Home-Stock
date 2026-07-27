import { useEffect, useState } from 'react'
import { idiomas as idiomasApi } from '@/lib/api'

interface Translations {
  [key: string]: string
}

export function useTranslations(idioma?: string) {
  const [traducciones, setTraducciones] = useState<Translations>({})
  const [cargando, setCargando] = useState(true)
  const [idimaActual, setIdiomaActual] = useState(idioma || 'es')

  useEffect(() => {
    setCargando(true)
    // Cargar todas las traducciones para el idioma actual
    fetch(`/api/idiomas/todos/${idimaActual}`, {
      credentials: 'include',
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.traducciones) {
          setTraducciones(data.traducciones)
        }
        setCargando(false)
      })
      .catch((err) => {
        console.error('Error al cargar traducciones:', err)
        setCargando(false)
      })
  }, [idimaActual])

  const t = (clave: string): string => {
    return traducciones[clave] || clave
  }

  const cambiarIdioma = (nuevoIdioma: string) => {
    setIdiomaActual(nuevoIdioma)
    localStorage.setItem('idioma_preferido', nuevoIdioma)
  }

  return {
    t,
    traducciones,
    cargando,
    idimaActual,
    cambiarIdioma,
  }
}
