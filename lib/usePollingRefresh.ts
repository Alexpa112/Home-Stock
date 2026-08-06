'use client'

import { useEffect, useRef } from 'react'
import { hogares } from '@/lib/api'

const INTERVALO_MS = 60000

/**
 * Refresco periodico silencioso compartido por stock y lista de la compra:
 * cada INTERVALO_MS pregunta /api/hogares/version (barato, sin traer filas)
 * y solo llama a onCambios() si la version difiere de la ultima vista. Se
 * salta el ciclo si la pestaña esta oculta o si suspendido() devuelve true
 * (p.ej. hay un modal de edicion abierto o una mutacion en curso), para no
 * pisar algo que el usuario esta editando en ese instante.
 */
export function usePollingRefresh(onCambios: () => void, suspendido: () => boolean): void {
  const ultimaVersionRef = useRef<string | null>(null)
  const onCambiosRef = useRef(onCambios)
  const suspendidoRef = useRef(suspendido)
  onCambiosRef.current = onCambios
  suspendidoRef.current = suspendido

  useEffect(() => {
    const intervalo = setInterval(async () => {
      if (document.visibilityState !== 'visible') return
      if (suspendidoRef.current()) return
      try {
        const data: any = await hogares.version()
        const version = data?.version ?? null
        if (ultimaVersionRef.current === null) {
          ultimaVersionRef.current = version
          return
        }
        if (version !== ultimaVersionRef.current) {
          ultimaVersionRef.current = version
          onCambiosRef.current()
        }
      } catch {
        // Sin conexion puntual: se reintenta en el siguiente ciclo, sin romper la UI.
      }
    }, INTERVALO_MS)
    return () => clearInterval(intervalo)
  }, [])
}
