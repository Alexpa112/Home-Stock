'use client'

import { useCallback, useEffect, useState } from 'react'
import { push } from './api'

// Uint8Array<ArrayBuffer> (no ArrayBufferLike): desde TS 5.7, lib.dom tipa
// PushSubscriptionOptionsInit.applicationServerKey como BufferSource, que
// exige el buffer concreto ArrayBuffer y ya no acepta el ArrayBufferLike
// generico que devuelve Uint8Array.from(); construir a mano deja siempre un
// ArrayBuffer real detras.
function base64UrlADataUint8Array(base64Url: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64Url.length % 4)) % 4)
  const base64 = (base64Url + padding).replace(/-/g, '+').replace(/_/g, '/')
  const bruto = window.atob(base64)
  const bytes = new Uint8Array(bruto.length)
  for (let i = 0; i < bruto.length; i++) bytes[i] = bruto.charCodeAt(i)
  return bytes
}

/**
 * Suscripcion a notificaciones push del navegador (P-01). El registro del
 * SW ya lo hace RootLayoutClient.tsx de forma global (tambien lo necesita
 * el modo offline, P-02); el register() de aqui es idempotente (el
 * navegador reutiliza el registro existente si la URL/scope coincide), se
 * mantiene para que este hook siga funcionando de forma autonoma si algun
 * dia se usa fuera de ese layout.
 */
export function usePushNotifications() {
  const [soportado, setSoportado] = useState(false)
  const [suscrito, setSuscrito] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const disponible = typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window
    setSoportado(disponible)
    if (!disponible) return

    navigator.serviceWorker.register('/sw.js').then(async (registro) => {
      const suscripcionActual = await registro.pushManager.getSubscription()
      setSuscrito(!!suscripcionActual)
    }).catch(() => {})
  }, [])

  const activar = useCallback(async () => {
    setCargando(true)
    setError('')
    try {
      if (Notification.permission === 'denied') {
        throw new Error('permiso_notificaciones_denegado')
      }
      const permiso = Notification.permission === 'granted' ? 'granted' : await Notification.requestPermission()
      if (permiso !== 'granted') {
        throw new Error('permiso_notificaciones_denegado')
      }

      const registro = await navigator.serviceWorker.ready
      const { clave_publica } = await push.vapidClavePublica()
      const suscripcion = await registro.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: base64UrlADataUint8Array(clave_publica),
      })

      const claves = suscripcion.toJSON().keys as { p256dh: string; auth: string }
      await push.suscribir(suscripcion.endpoint, claves)
      setSuscrito(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'err_conexion_servidor')
    } finally {
      setCargando(false)
    }
  }, [])

  const desactivar = useCallback(async () => {
    setCargando(true)
    setError('')
    try {
      const registro = await navigator.serviceWorker.ready
      const suscripcion = await registro.pushManager.getSubscription()
      if (suscripcion) {
        await push.desuscribir(suscripcion.endpoint)
        await suscripcion.unsubscribe()
      }
      setSuscrito(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'err_conexion_servidor')
    } finally {
      setCargando(false)
    }
  }, [])

  return { soportado, suscrito, cargando, error, activar, desactivar }
}
