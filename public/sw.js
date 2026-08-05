// Service worker minimo, con el UNICO objetivo de soportar notificaciones
// push (P-01). No implementa cache offline de la app (eso es un cambio de
// alcance mayor, ver P-02 en el roadmap) - a proposito no intercepta
// "fetch", para no arriesgar a servir contenido obsoleto sin querer.

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
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
