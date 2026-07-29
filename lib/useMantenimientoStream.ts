import { useEffect } from 'react'
import { marcarMantenimiento } from './mantenimiento'

// Reconexión manual: EventSource ya reintenta solo, pero con backoff propio
// del navegador que puede tardar; forzamos un reintento corto y acotado para
// no dejar una pestaña abierta minutos sin saber que ya se puede volver a usar.
const REINTENTO_MS = 3000

export function useMantenimientoStream() {
  useEffect(() => {
    let es: EventSource | null = null
    let reintentoTimer: ReturnType<typeof setTimeout> | null = null
    let cancelado = false

    const conectar = () => {
      if (cancelado) return
      es = new EventSource('/api/mantenimiento/stream')

      es.addEventListener('mantenimiento', (evento) => {
        const data = (evento as MessageEvent).data
        marcarMantenimiento(data === 'activo')
      })

      es.onerror = () => {
        es?.close()
        if (!cancelado) {
          reintentoTimer = setTimeout(conectar, REINTENTO_MS)
        }
      }
    }

    conectar()

    return () => {
      cancelado = true
      es?.close()
      if (reintentoTimer) clearTimeout(reintentoTimer)
    }
  }, [])
}
