'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { push } from './api'
import { claveErrorPush } from './errorPush'

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
 *
 * iOS (Safari 16.4+, solo con la app anadida a la pantalla de inicio) exige
 * que requestPermission() y pushManager.subscribe() se llamen desde el gesto
 * del usuario. Por eso la clave VAPID y el registro del service worker se
 * obtienen al montar, no al pulsar: una peticion de red entre el toque y
 * subscribe() hacia perder el gesto y fallaba con NotAllowedError.
 */
export function usePushNotifications() {
  const [soportado, setSoportado] = useState(false)
  const [suscrito, setSuscrito] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const clavePublicaRef = useRef('')
  const registroRef = useRef<ServiceWorkerRegistration | null>(null)

  useEffect(() => {
    const soportaNavegador = typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window
    if (!soportaNavegador) {
      setSoportado(false)
      return
    }

    // El navegador puede con push, pero hace falta que el servidor tenga clave
    // VAPID (py-vapid instalado y data/vapid_private_key.pem generada). Si no
    // la tiene, se oculta el interruptor en vez de ofrecerlo y fallar al
    // pulsarlo: sin clave publica, pushManager.subscribe() lanza una
    // DOMException del navegador que no dice nada al usuario.
    push.vapidClavePublica()
      .then(({ clave_publica }) => {
        clavePublicaRef.current = clave_publica || ''
        setSoportado(!!clave_publica)
      })
      .catch(() => setSoportado(false))

    navigator.serviceWorker.register('/sw.js').then(async () => {
      // ready espera a que el worker este ACTIVO (register() puede resolver con
      // el worker aun instalandose, y subscribe() falla en ese estado).
      const registro = await navigator.serviceWorker.ready
      registroRef.current = registro
      const suscripcionActual = await registro.pushManager.getSubscription()
      setSuscrito(!!suscripcionActual)
    }).catch(() => {})
  }, [])

  const activar = useCallback(async () => {
    setCargando(true)
    setError('')
    let suscripcionNueva: PushSubscription | null = null
    try {
      if (typeof Notification === 'undefined') {
        throw new Error('err_push_no_disponible')
      }
      if (Notification.permission === 'denied') {
        throw new Error('permiso_notificaciones_denegado')
      }
      // Primera operacion asincrona: se ejecuta dentro del gesto del usuario.
      const permiso = Notification.permission === 'granted' ? 'granted' : await Notification.requestPermission()
      if (permiso !== 'granted') {
        throw new Error('permiso_notificaciones_denegado')
      }

      // Con los datos ya cargados al montar, subscribe() va justo despues del
      // permiso, sin viajes de red por medio.
      const registro = registroRef.current ?? (await navigator.serviceWorker.ready)
      const clavePublica = clavePublicaRef.current || (await push.vapidClavePublica()).clave_publica
      if (!clavePublica) {
        // Servidor sin clave VAPID: no se llama a subscribe() con una clave
        // vacia, porque el error resultante seria un mensaje del navegador en
        // su propio idioma y sin traduccion posible.
        setSoportado(false)
        throw new Error('err_push_no_disponible')
      }

      // Si ya habia una suscripcion (de un intento anterior que fallo al
      // guardarse en el servidor) se reutiliza: pedir otra con otra clave lanza
      // InvalidStateError.
      let suscripcion = await registro.pushManager.getSubscription()
      if (!suscripcion) {
        suscripcion = suscripcionNueva = await registro.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: base64UrlADataUint8Array(clavePublica),
        })
      }

      const claves = suscripcion.toJSON().keys as { p256dh: string; auth: string }
      await push.suscribir(suscripcion.endpoint, claves)
      setSuscrito(true)
    } catch (err) {
      // Si la suscripcion se creo pero el servidor no la guardo, se deshace:
      // un interruptor apagado con una suscripcion huerfana en el navegador.
      if (suscripcionNueva) await suscripcionNueva.unsubscribe().catch(() => {})
      setError(claveErrorPush(err, typeof Notification === 'undefined' ? undefined : Notification.permission))
    } finally {
      setCargando(false)
    }
  }, [])

  const desactivar = useCallback(async () => {
    setCargando(true)
    setError('')
    try {
      const registro = registroRef.current ?? (await navigator.serviceWorker.ready)
      const suscripcion = await registro.pushManager.getSubscription()
      if (suscripcion) {
        await push.desuscribir(suscripcion.endpoint)
        await suscripcion.unsubscribe()
      }
      setSuscrito(false)
    } catch (err) {
      setError(claveErrorPush(err))
    } finally {
      setCargando(false)
    }
  }, [])

  return { soportado, suscrito, cargando, error, activar, desactivar }
}
