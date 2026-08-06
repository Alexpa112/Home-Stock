/**
 * Estado global de modo mantenimiento en el cliente.
 *
 * Se activa por dos vías (la que llegue primero gana):
 * 1. SSE en tiempo real (`useMantenimientoStream`, ver RootLayoutClient) contra
 *    /api/mantenimiento/stream (stockhogar/rutas/paginas.py): el backend
 *    empuja el cambio en cuanto detecta el flag, sin esperar a que el usuario
 *    haga nada.
 * 2. Cualquier llamada a la API (lib/api.ts) que reciba un 503 con
 *    `mantenimiento: true` (stockhogar/__init__.py, comprobar_mantenimiento):
 *    red de seguridad por si la conexión SSE se hubiera perdido.
 *
 * Un módulo aparte (en vez de vivir solo en el Context) permite que api.ts
 * marque el estado sin depender de React ni de que el componente que hizo la
 * llamada esté dentro del árbol de providers.
 */

type Listener = (activo: boolean) => void

let activo = false
const listeners = new Set<Listener>()

export function marcarMantenimiento(nuevoEstado: boolean) {
  if (nuevoEstado === activo) return
  activo = nuevoEstado
  listeners.forEach((listener) => listener(activo))
}

export function mantenimientoActivo() {
  return activo
}

export function suscribirMantenimiento(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
