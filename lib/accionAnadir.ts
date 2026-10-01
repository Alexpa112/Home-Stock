'use client'

import { useEffect, useRef } from 'react'

// El botón flotante vive en el layout y la pantalla activa decide qué significa
// "añadir" (Stock: alta de producto; Compra: alta de artículo). Un evento de
// ventana evita acoplar el layout a cada página.
export const EVENTO_ANADIR = 'dreame:anadir'

export function dispararAnadir() {
  window.dispatchEvent(new Event(EVENTO_ANADIR))
}

export function useAccionAnadir(accion: () => void) {
  const ref = useRef(accion)
  useEffect(() => {
    ref.current = accion
  })
  useEffect(() => {
    const manejador = () => ref.current()
    window.addEventListener(EVENTO_ANADIR, manejador)
    return () => window.removeEventListener(EVENTO_ANADIR, manejador)
  }, [])
}
