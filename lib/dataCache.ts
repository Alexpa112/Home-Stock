/**
 * Cache cliente en memoria + localStorage para datos de pantallas (stock,
 * lista de compra, categorias). Permite pintar el ultimo dato conocido al
 * instante mientras se revalida contra el backend (stale-while-revalidate)
 * y precargar pantallas antes de que el usuario navegue a ellas.
 */

type CacheEntry = { data: unknown; timestamp: number }

const memoryCache = new Map<string, CacheEntry>()
const STORAGE_PREFIX = 'sh-cache:'

function readFromStorage(key: string): CacheEntry | undefined {
  if (typeof window === 'undefined') return undefined
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key)
    return raw ? (JSON.parse(raw) as CacheEntry) : undefined
  } catch {
    return undefined
  }
}

function writeToStorage(key: string, entry: CacheEntry) {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(entry))
  } catch {
    // localStorage lleno o inaccesible: la cache en memoria sigue funcionando
  }
}

export function getCached<T>(key: string): T | undefined {
  const hit = memoryCache.get(key) ?? readFromStorage(key)
  if (hit && !memoryCache.has(key)) memoryCache.set(key, hit)
  return hit?.data as T | undefined
}

export function setCached(key: string, data: unknown): void {
  const entry: CacheEntry = { data, timestamp: Date.now() }
  memoryCache.set(key, entry)
  writeToStorage(key, entry)
}

/**
 * Lanza fetcher() y guarda el resultado en cache sin bloquear al llamador.
 * Usado para precargar los datos de otra pantalla mientras el usuario sigue
 * en la actual, de forma que al navegar ya esten disponibles al instante.
 */
export function prefetch<T>(key: string, fetcher: () => Promise<T>): void {
  fetcher().then((data) => setCached(key, data)).catch(() => {})
}

/**
 * Borra entradas de cache (memoria + localStorage). Las claves de este
 * modulo NO estan separadas por hogar (ver 'stock:productos', etc.), asi
 * que al cambiar de hogar hay que llamar a esto antes de recargar la app:
 * si no, un stale-while-revalidate pintaria por un instante los datos del
 * hogar anterior.
 */
export function clearCache(keys: string[]): void {
  for (const key of keys) {
    memoryCache.delete(key)
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem(STORAGE_PREFIX + key)
      } catch {
        // ignorar
      }
    }
  }
}
