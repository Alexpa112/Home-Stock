const CACHE_NAME = 'stockhogar-v7';
const OFFLINE_URL = '/static/offline.html';

const SHELL_ASSETS = [
  '/static/style.css',
  '/static/responsive.css',
  '/static/virtual-keyboard.css',
  '/static/app.js',
  '/static/i18n.js',
  '/static/manifest.json',
  '/static/icons/favicon.svg',
  '/static/icons/catalogo-iconos.js',
  '/static/utils/iconos.js',
  '/static/modules/ui-components.js',
  '/static/modules/form-builder.js',
  '/static/modules/drawer-listas.js',
  '/static/modules/virtual-keyboard.js',
  OFFLINE_URL,
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Llamadas a la API: siempre red, sin cache (datos dinámicos)
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // Navegación (recarga de página): red primero, y si falla, shell offline
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Estáticos: cache-first con actualización en segundo plano
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((response) => {
          if (response.ok) {
            caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
