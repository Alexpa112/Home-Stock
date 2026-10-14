'use client'

import { useEffect, useRef } from 'react'

// El selector de hogar a pantalla completa vive en el layout, pero el chip que
// lo abre está en la cabecera de cada pantalla. Mismo patrón que accionAnadir.
export const EVENTO_SELECTOR_HOGAR = 'dreame:selector-hogar'

export function abrirSelectorHogar() {
  window.dispatchEvent(new Event(EVENTO_SELECTOR_HOGAR))
}

export function useAbrirSelectorHogar(accion: () => void) {
  const ref = useRef(accion)
  useEffect(() => {
    ref.current = accion
  })
  useEffect(() => {
    const manejador = () => ref.current()
    window.addEventListener(EVENTO_SELECTOR_HOGAR, manejador)
    return () => window.removeEventListener(EVENTO_SELECTOR_HOGAR, manejador)
  }, [])
}
