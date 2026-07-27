import { useEffect } from 'react';

const CACHE_VERSION_KEY = 'stockhogar_cache_version';
const CHECK_INTERVAL = 15000; // Chequear cada 15s (más frecuente para detectar updates rápido)
const MAX_RETRIES = 3;

export function useCacheBuster() {
  useEffect(() => {
    let retryCount = 0;

    const checkVersion = async () => {
      try {
        const res = await fetch('/api/cache-version?t=' + Date.now(), {
          cache: 'no-store',
          headers: { 'pragma': 'no-cache', 'cache-control': 'no-cache' },
        });
        const data = await res.json();
        const newVersion = String(data.version);
        const savedVersion = localStorage.getItem(CACHE_VERSION_KEY);

        console.debug('[CacheBuster] Server version:', newVersion, 'Saved:', savedVersion);

        if (savedVersion && savedVersion !== newVersion) {
          // Versión cambió, hay actualización
          console.warn('[CacheBuster] Update detected! Server changed from', savedVersion, 'to', newVersion);
          await clearCacheAndReload();
        } else if (!savedVersion) {
          // Primera vez, guardar versión
          console.debug('[CacheBuster] First check, saving version:', newVersion);
          localStorage.setItem(CACHE_VERSION_KEY, newVersion);
        }
        retryCount = 0; // Reset retry count on success
      } catch (err) {
        retryCount++;
        console.error('[CacheBuster] Error checking version (attempt', retryCount + '/' + MAX_RETRIES + '):', err);
        // No hacer nada en error, reintentar en el siguiente intervalo
      }
    };

    // Chequear inmediatamente
    checkVersion();

    // Y luego cada 15s
    const interval = setInterval(checkVersion, CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, []);
}

async function clearCacheAndReload() {
  console.warn('[CacheBuster] Starting cache clear and reload...');
  try {
    // Esperar un poco para asegurar que el servidor esté listo
    await new Promise(resolve => setTimeout(resolve, 500));

    // Desregistrar service workers
    if ('serviceWorker' in navigator) {
      console.debug('[CacheBuster] Unregistering service workers...');
      const registrations = await navigator.serviceWorker.getRegistrations();
      console.debug('[CacheBuster] Found', registrations.length, 'service worker(s)');
      for (const reg of registrations) {
        try {
          await reg.unregister();
          console.debug('[CacheBuster] Unregistered:', reg.scope);
        } catch (e) {
          console.error('[CacheBuster] Error unregistering SW:', e);
        }
      }
      // Esperar a que se desregistren
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    // Limpiar todos los cachés
    if ('caches' in window) {
      console.debug('[CacheBuster] Clearing caches...');
      const cacheNames = await caches.keys();
      console.debug('[CacheBuster] Found caches:', cacheNames);
      await Promise.all(cacheNames.map(async (name) => {
        try {
          await caches.delete(name);
          console.debug('[CacheBuster] Deleted cache:', name);
        } catch (e) {
          console.error('[CacheBuster] Error deleting cache:', name, e);
        }
      }));
    }

    // Actualizar versión guardada
    console.debug('[CacheBuster] Fetching new version...');
    const res = await fetch('/api/cache-version?t=' + Date.now(), {
      cache: 'no-store',
      headers: { 'pragma': 'no-cache', 'cache-control': 'no-cache' },
    });
    const data = await res.json();
    const newVersion = String(data.version);
    localStorage.setItem(CACHE_VERSION_KEY, newVersion);
    console.debug('[CacheBuster] Updated saved version to:', newVersion);

    // Esperar un poco más antes de recargar
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Recargar con fuerza (bypassing cache)
    console.warn('[CacheBuster] Reloading page...');
    window.location.href = window.location.href.split('#')[0]; // Remove hash, then reload
  } catch (err) {
    console.error('[CacheBuster] Error during cache clear:', err);
    // Recargar de todas formas
    console.warn('[CacheBuster] Force reloading despite error...');
    window.location.reload();
  }
}
