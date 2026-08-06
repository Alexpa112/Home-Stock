import { useEffect } from 'react'
import { marcarMantenimiento } from './mantenimiento'

// Antes era un SSE persistente (/api/mantenimiento/stream). Cada pestaña
// abierta retenia un hilo de gunicorn en el backend a la espera del cambio
// (S-02): con --workers 2 --threads 4 (8 hilos totales, ver
// Dockerfile.raspbian), unas pocas pestañas ya saturaban el servidor. Ahora
// se hace polling ligero, mismo patron que lib/usePollingRefresh.ts, pero
// mas frecuente (15s en vez de 60s) porque el mantenimiento es mas urgente
// de detectar: el usuario deberia ver el aviso casi al instante.
const INTERVALO_MS = 15000

export function useMantenimientoStream() {
  useEffect(() => {
    let cancelado = false

    const comprobar = async () => {
      if (document.visibilityState !== 'visible') return
      try {
        const resp = await fetch('/api/mantenimiento/estado')
        if (!resp.ok) return
        const data = await resp.json()
        if (!cancelado) marcarMantenimiento(Boolean(data?.activo))
      } catch {
        // Sin conexion puntual: se reintenta en el siguiente ciclo.
      }
    }

    comprobar()
    const intervalo = setInterval(comprobar, INTERVALO_MS)

    return () => {
      cancelado = true
      clearInterval(intervalo)
    }
  }, [])
}
