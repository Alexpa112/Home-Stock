'use client'

import { useEffect, useState } from 'react'
import { idiomas } from '@/lib/api'

/** Traducciones de UI para un idioma, cargadas desde stockhogar/translations.json vía la API. */
export function useTexto(idioma: string) {
  const [traducciones, setTraducciones] = useState<Record<string, string>>({})

  useEffect(() => {
    idiomas
      .todos(idioma)
      .then((datos) => setTraducciones(datos.traducciones || {}))
      .catch(() => setTraducciones({}))
  }, [idioma])

  return (clave: string, textoPorDefecto: string) => traducciones[clave] || textoPorDefecto
}
