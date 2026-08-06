// Service worker con dos responsabilidades: notificaciones push (P-01) y
// un modo offline minimo (P-02) - navegar a una pagina ya visitada sigue
// funcionando sin red, mostrando la ultima version vista.
//
// No cachea peticiones a /api/* (los datos ya tienen su propia cache en
// lib/dataCache.ts, a nivel de aplicacion, con su propia logica de
// stale-while-revalidate; duplicarla aqui podria servir un JSON obsoleto
// justo cuando dataCache.ts esperaria un error de red real para caer a SU
// cache) ni a /_next/static/* (en dev, Turbopack REUSA los mismos nombres
// de chunk entre recompilaciones - ver el comentario sobre esto en
// next.config.mjs; cachear esos ficheros en el SW reproduciria ese mismo
// bug de contenido obsoleto, esta vez tambien en produccion). Solo se
// cachean documentos de navegacion (las paginas HTML en si).
//
// Sin riesgo de quedarse con cache obsoleta para siempre tras un deploy:
// lib/useCacheBuster.ts ya detecta cada nueva version del servidor y
// desregistra el SW + borra TODAS las caches (caches.keys()) como parte de
// su reload automatico, asi que cualquier cache que abra este fichero se
// limpia sola en el siguiente despliegue.

const CACHE_SHELL = 'dreame-shell-v1'
const RUTA_OFFLINE = '/offline'

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_SHELL).then((cache) => cache.addAll([RUTA_OFFLINE, '/manifest.json']))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  if (request.mode !== 'navigate') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) return

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE_SHELL)
      try {
        const respuesta = await fetch(request)
        // Solo se guarda una respuesta valida (200); errores 4xx/5xx no
        // sustituyen la ultima version buena que hubiera en cache.
        if (respuesta && respuesta.ok) cache.put(request, respuesta.clone())
        return respuesta
      } catch {
        const enCache = await cache.match(request)
        return enCache || (await cache.match(RUTA_OFFLINE))
      }
    })()
  )
})

self.addEventListener('push', (event) => {
  let datos = { titulo: 'Dreame!', cuerpo: '', url: '/dashboard' }
  try {
    if (event.data) datos = { ...datos, ...event.data.json() }
  } catch {
    // Si el payload no es JSON valido, se usa el texto tal cual como cuerpo.
    datos.cuerpo = event.data ? event.data.text() : ''
  }

  event.waitUntil(
    self.registration.showNotification(datos.titulo, {
      body: datos.cuerpo,
      icon: '/icon-192x192.png',
      badge: '/icon-192x192.png',
      data: { url: datos.url || '/dashboard' },
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/dashboard'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const cliente of clientList) {
        if (cliente.url.includes(url) && 'focus' in cliente) return cliente.focus()
      }
      if (self.clients.openWindow) return self.clients.openWindow(url)
    })
  )
})
