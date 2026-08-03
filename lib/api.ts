/**
 * Cliente API contra el backend real de Dreame! (Flask, ver stockhogar/rutas/*.py).
 *
 * Usa rutas relativas ('/api/...'): next.config.mjs reescribe /api/:path* hacia
 * NEXT_PUBLIC_API_URL (Flask) en el propio servidor de Next, así que el navegador
 * solo habla con el origen de Next (mismo dominio) y evitamos CORS y problemas de
 * cookies de sesión entre dominios distintos.
 *
 * Todas las rutas mutables (POST/PUT/PATCH/DELETE) requieren cabecera
 * X-CSRFToken (Flask-WTF CSRFProtect, ver stockhogar/__init__.py): el token se
 * obtiene de /api/csrf-token y se cachea en memoria, con reintento único si el
 * backend lo rechaza por caducado.
 */

import { marcarMantenimiento } from './mantenimiento'

interface FetchOptions extends RequestInit {
  headers?: Record<string, string>
}

let csrfTokenCache: string | null = null

async function obtenerCsrfToken(forzarRefresco = false): Promise<string> {
  if (csrfTokenCache && !forzarRefresco) return csrfTokenCache
  const res = await fetch('/api/csrf-token', { credentials: 'include' })
  const datos = await res.json()
  csrfTokenCache = datos.csrf_token
  return csrfTokenCache as string
}

const METODOS_MUTABLES = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

// Como apiCall pero para multipart/form-data (subida de imagen de ticket):
// no se fija Content-Type (el navegador pone el boundary solo) ni se
// serializa el body a JSON.
export async function apiUpload<T = any>(endpoint: string, formData: FormData): Promise<T> {
  const csrfToken = await obtenerCsrfToken()
  const response = await fetch(endpoint, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': csrfToken },
    body: formData,
  })
  const contentType = response.headers.get('content-type') || ''
  const datos = contentType.includes('application/json') ? await response.json().catch(() => null) : null
  if (response.status === 503 && datos?.mantenimiento) {
    marcarMantenimiento(true)
  }
  if (!response.ok) {
    throw new Error((datos && datos.error) || `Error HTTP ${response.status}`)
  }
  return datos as T
}

export async function apiCall<T = any>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const metodo = (options.method || 'GET').toUpperCase()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (METODOS_MUTABLES.has(metodo)) {
    headers['X-CSRFToken'] = await obtenerCsrfToken()
  }

  const hacerPeticion = () =>
    fetch(endpoint, {
      credentials: 'include',
      ...options,
      headers,
    })

  let response = await hacerPeticion()

  // Token CSRF caducado/invalido: refrescar una vez y reintentar.
  if (response.status === 400 && METODOS_MUTABLES.has(metodo)) {
    const cuerpo = await response.clone().json().catch(() => ({}))
    if (typeof cuerpo.error === 'string' && cuerpo.error.toLowerCase().includes('csrf')) {
      headers['X-CSRFToken'] = await obtenerCsrfToken(true)
      response = await hacerPeticion()
    }
  }

  if (response.status === 204) return undefined as T

  const contentType = response.headers.get('content-type') || ''
  const datos = contentType.includes('application/json') ? await response.json().catch(() => null) : null

  // Red de seguridad si el stream SSE de mantenimiento (RootLayoutClient) se
  // hubiera perdido: cualquier petición real detecta el 503 igualmente.
  if (response.status === 503 && datos?.mantenimiento) {
    marcarMantenimiento(true)
  }

  if (!response.ok) {
    throw new Error((datos && datos.error) || `Error HTTP ${response.status}`)
  }

  return datos as T
}

// ===== Autenticación (stockhogar/rutas/auth.py) =====
export const auth = {
  estado: () => apiCall('/api/auth/estado'),

  login: (usuario: string, password: string) =>
    apiCall('/api/auth/login', { method: 'POST', body: JSON.stringify({ usuario, password }) }),

  registrar: (usuario: string, password: string) =>
    apiCall('/api/auth/registrar', { method: 'POST', body: JSON.stringify({ usuario, password }) }),

  verificarCodigo: (codigo: string) =>
    apiCall('/api/auth/verificar-codigo', { method: 'POST', body: JSON.stringify({ codigo }) }),

  reenviarCodigo: () => apiCall('/api/auth/reenviar-codigo', { method: 'POST' }),

  cambiarDobleFactor: (activo: boolean) =>
    apiCall('/api/auth/doble-factor', { method: 'POST', body: JSON.stringify({ activo }) }),

  logout: () => apiCall('/api/auth/logout', { method: 'POST' }),

  actualizarPerfil: (datos: { nombre?: string; password?: string }) =>
    apiCall('/api/auth/perfil', { method: 'PUT', body: JSON.stringify(datos) }),

  cambiarTema: (tema: 'light' | 'dark' | 'auto') =>
    apiCall('/api/auth/tema', { method: 'POST', body: JSON.stringify({ tema }) }),

  cambiarPassword: (password_actual: string, password_nueva: string, password_confirmacion: string) =>
    apiCall('/api/auth/cambiar-password', {
      method: 'POST',
      body: JSON.stringify({ password_actual, password_nueva, password_confirmacion }),
    }),

  actualizarPreferenciasListas: (datos: { vista_lista_compra?: 'lista' | 'recuadros'; agrupar_categorias?: 'on' | 'off' }) =>
    apiCall('/api/auth/preferencias-listas', { method: 'POST', body: JSON.stringify(datos) }),

  eliminarCuenta: (usuarioId: number) =>
    apiCall(`/api/usuarios/${usuarioId}`, { method: 'DELETE' }),
}

// ===== Hogares (stockhogar/rutas/hogares.py) =====
export const hogares = {
  listar: () => apiCall('/api/hogares'),

  crear: (nombre: string, opciones: { descripcion?: string; icono?: string; color?: string; privada?: boolean } = {}) =>
    apiCall('/api/hogares', { method: 'POST', body: JSON.stringify({ nombre, ...opciones }) }),

  actualizar: (id: number, datos: Record<string, unknown>) =>
    apiCall(`/api/hogares/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),

  eliminar: (id: number) => apiCall(`/api/hogares/${id}`, { method: 'DELETE' }),

  seleccionar: (id: number) => apiCall(`/api/hogares/${id}/seleccionar`, { method: 'POST' }),

  // Abandonar un hogar compartido contigo (no aplica a hogares propios).
  salir: (id: number) => apiCall(`/api/hogares/${id}/salir`, { method: 'POST' }),

  // Marca de versión barata del hogar activo, para polling silencioso (ver
  // lib/usePollingRefresh.ts): se pide antes de recargar datos completos.
  version: () => apiCall('/api/hogares/version'),
}

// ===== Productos / stock (stockhogar/rutas/productos.py) =====
export const productos = {
  listar: () => apiCall('/api/productos'),

  crear: (datos: {
    nombre: string
    categoria?: string
    cantidad?: number
    stock_minimo?: number
    unidad?: string
    icono?: string
    dias_aviso?: number
  }) => apiCall('/api/productos', { method: 'POST', body: JSON.stringify(datos) }),

  // delta: +1/-1 para los botones de cantidad; o pasar campos completos para editar.
  actualizar: (id: number, datos: { delta: number } | Record<string, unknown>) =>
    apiCall(`/api/productos/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),

  eliminar: (id: number) => apiCall(`/api/productos/${id}`, { method: 'DELETE' }),
}

// ===== Lista de la compra (stockhogar/rutas/articulos_compra.py) =====
export const articulosLista = {
  // Devuelve { pendientes: [...], completados: [...] }
  listar: () => apiCall('/api/articulos'),

  anadir: (nombre: string, opciones: { cantidad?: number; unidad?: string; categoria?: string; icono?: string } = {}) =>
    apiCall('/api/articulos', { method: 'POST', body: JSON.stringify({ nombre, ...opciones }) }),

  marcarComprado: (id: number) =>
    apiCall(`/api/articulos/${id}`, { method: 'PATCH', body: JSON.stringify({ activo: false }) }),

  restaurar: (id: number) =>
    apiCall(`/api/articulos/${id}`, { method: 'PATCH', body: JSON.stringify({ activo: true }) }),

  actualizar: (id: number, datos: Record<string, unknown>) =>
    apiCall(`/api/articulos/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),

  eliminar: (id: number) => apiCall(`/api/articulos/${id}`, { method: 'DELETE' }),
}

// ===== Artículos personalizados del hogar (catálogo propio) =====
export const articulosPersonalizados = {
  listar: () => apiCall('/api/articulos/personalizados'),
  actualizar: (id: number, datos: Record<string, unknown>) =>
    apiCall(`/api/articulos/personalizados/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),
  eliminar: (id: number) => apiCall(`/api/articulos/personalizados/${id}`, { method: 'DELETE' }),
}

// ===== Categorías (stockhogar/rutas/categorias.py) =====
export const categorias = {
  listar: () => apiCall('/api/categorias'),
  crear: (nombre: string, icono?: string) =>
    apiCall('/api/categorias', { method: 'POST', body: JSON.stringify({ nombre, icono }) }),
  eliminar: (id: number) => apiCall(`/api/categorias/${id}`, { method: 'DELETE' }),
}

// ===== Hogares compartidos / permisos (stockhogar/rutas/permisos.py) =====
export const permisos = {
  buscarUsuarios: (q: string) => apiCall(`/api/hogares/buscar-usuarios?q=${encodeURIComponent(q)}`),

  // { propietario: {...}, miembros: [...] }
  miembros: (hogarId: number) => apiCall(`/api/hogares/${hogarId}/miembros`),

  // Por nombre de usuario (acceso inmediato) o por email (crea invitación).
  compartir: (hogarId: number, datos: { usuario?: string; email?: string; nivel?: 'ver' | 'editar' }) =>
    apiCall(`/api/hogares/${hogarId}/compartir`, { method: 'POST', body: JSON.stringify(datos) }),

  // Generar enlace compartible público
  generarEnlace: (hogarId: number) =>
    apiCall(`/api/hogares/${hogarId}/enlace-compartible`, { method: 'POST' }),

  actualizarPermiso: (hogarId: number, usuarioId: number, nivel: 'ver' | 'editar') =>
    apiCall(`/api/hogares/${hogarId}/permisos/${usuarioId}`, { method: 'PATCH', body: JSON.stringify({ nivel }) }),

  revocar: (hogarId: number, usuarioId: number) =>
    apiCall(`/api/hogares/${hogarId}/permisos/${usuarioId}`, { method: 'DELETE' }),

  aceptarInvitacion: (codigo: string) =>
    apiCall(`/api/hogares/aceptar-invitacion/${codigo}`, { method: 'POST' }),
}

// ===== Escaneo de tickets (stockhogar/rutas/tickets.py) =====
export const tickets = {
  // Sube la foto y devuelve { items: [...], resumen: {...}, advertencias: [...] }
  analizar: (foto: File) => {
    const formData = new FormData()
    formData.append('foto', foto)
    return apiUpload('/api/tickets/analizar', formData)
  },

  confirmar: (
    items: Array<{ nombre: string; cantidad: number; unidad?: string; categoria?: string; producto_id?: number | null }>
  ) => apiCall('/api/tickets/confirmar', { method: 'POST', body: JSON.stringify({ items }) }),
}

// ===== Historial / catálogo aprendido (stockhogar/rutas/historial.py) =====
export const historial = {
  listar: () => apiCall('/api/historial'),
}

// ===== Consumo / auditoría de stock (stockhogar/rutas/consumo.py) =====
export const consumo = {
  movimientosProducto: (productoId: number) => apiCall(`/api/consumo/producto/${productoId}`),
  resumen: (dias = 30) => apiCall(`/api/consumo/resumen?dias=${dias}`),
}

// ===== Idiomas (stockhogar/rutas/idiomas.py) =====
export const idiomas = {
  disponibles: () => apiCall('/api/idiomas/disponibles'),
  cambiar: (idioma: string) => apiCall('/api/idiomas/cambiar', { method: 'POST', body: JSON.stringify({ idioma }) }),
  todos: (idioma: string) => apiCall(`/api/idiomas/todos/${idioma}`),
}
