import { useEffect } from 'react';

const CACHE_VERSION_KEY = 'stockhogar_cache_version';
const CHECK_INTERVAL = 30000; // Chequear cada 30s

export function useCacheBuster() {
  useEffect(() => {
    const checkVersion = async () => {
      try {
        const res = await fetch('/api/cache-version', { cache: 'no-store' });
        const data = await res.json();
        const newVersion = data.version;
        const savedVersion = localStorage.getItem(CACHE_VERSION_KEY);

        if (savedVersion && savedVersion !== String(newVersion)) {
          // Versión cambió, hay actualización
          await clearCacheAndReload();
        } else if (!savedVersion) {
          // Primera vez
          localStorage.setItem(CACHE_VERSION_KEY, String(newVersion));
        }
      } catch (err) {
        console.error('Cache buster error:', err);
      }
    };

    // Chequear inmediatamente
    checkVersion();

    // Y luego cada 30s
    const interval = setInterval(checkVersion, CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, []);
}

async function clearCacheAndReload() {
  try {
    // Desregistrar service workers
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (const reg of registrations) {
        await reg.unregister();
      }
    }

    // Limpiar cachés
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
    }

    // Actualizar versión guardada
    const res = await fetch('/api/cache-version', { cache: 'no-store' });
    const data = await res.json();
    localStorage.setItem(CACHE_VERSION_KEY, String(data.version));

    // Recargar con fuerza
    window.location.reload();
  } catch (err) {
    console.error('Error clearing cache:', err);
    // Recargar de todas formas
    window.location.reload();
  }
}
