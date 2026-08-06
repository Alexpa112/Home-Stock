'use client'

import { useEffect, useState } from 'react'

/**
 * Estado online/offline del navegador (P-02). navigator.onLine es fiable
 * para detectar "sin adaptador de red" pero no "hay red local sin salida a
 * internet real"; para el uso de esta app (avisar de que se esta viendo
 * contenido en cache) es suficiente sin añadir comprobaciones activas
 * contra el backend.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(true)

  useEffect(() => {
    setOnline(navigator.onLine)
    const marcarOnline = () => setOnline(true)
    const marcarOffline = () => setOnline(false)
    window.addEventListener('online', marcarOnline)
    window.addEventListener('offline', marcarOffline)
    return () => {
      window.removeEventListener('online', marcarOnline)
      window.removeEventListener('offline', marcarOffline)
    }
  }, [])

  return online
}
