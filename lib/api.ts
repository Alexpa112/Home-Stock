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

  logout: () => apiCall('/api/auth/logout', { method: 'POST' }),

  actualizarPerfil: (datos: { nombre?: string; password?: string }) =>
    apiCall('/api/auth/perfil', { method: 'PUT', body: JSON.stringify(datos) }),

  cambiarTema: (tema: 'light' | 'dark' | 'auto') =>
    apiCall('/api/auth/tema', { method: 'POST', body: JSON.stringify({ tema }) }),
}

// ===== Listas (stockhogar/rutas/listas.py) =====
export const listas = {
  listar: () => apiCall('/api/listas'),

  crear: (nombre: string, opciones: { descripcion?: string; icono?: string; color?: string; privada?: boolean } = {}) =>
    apiCall('/api/listas', { method: 'POST', body: JSON.stringify({ nombre, ...opciones }) }),

  actualizar: (id: number, datos: Record<string, unknown>) =>
    apiCall(`/api/listas/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),

  eliminar: (id: number) => apiCall(`/api/listas/${id}`, { method: 'DELETE' }),

  seleccionar: (id: number) => apiCall(`/api/listas/${id}/seleccionar`, { method: 'POST' }),

  // Abandonar una lista compartida contigo (no aplica a listas propias).
  salir: (id: number) => apiCall(`/api/listas/${id}/salir`, { method: 'POST' }),
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

// ===== Lista de la compra (stockhogar/rutas/articulos_lista.py) =====
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

// ===== Categorías (stockhogar/rutas/categorias.py) =====
export const categorias = {
  listar: () => apiCall('/api/categorias'),
  crear: (nombre: string, icono?: string) =>
    apiCall('/api/categorias', { method: 'POST', body: JSON.stringify({ nombre, icono }) }),
  eliminar: (id: number) => apiCall(`/api/categorias/${id}`, { method: 'DELETE' }),
}

// ===== Listas compartidas / permisos (stockhogar/rutas/permisos.py) =====
export const permisos = {
  buscarUsuarios: (q: string) => apiCall(`/api/listas/buscar-usuarios?q=${encodeURIComponent(q)}`),

  // { propietario: {...}, miembros: [...] }
  miembros: (listaId: number) => apiCall(`/api/listas/${listaId}/miembros`),

  // Por nombre de usuario (acceso inmediato) o por email (crea invitación).
  compartir: (listaId: number, datos: { usuario?: string; email?: string; nivel?: 'ver' | 'editar' }) =>
    apiCall(`/api/listas/${listaId}/compartir`, { method: 'POST', body: JSON.stringify(datos) }),

  actualizarPermiso: (listaId: number, usuarioId: number, nivel: 'ver' | 'editar') =>
    apiCall(`/api/listas/${listaId}/permisos/${usuarioId}`, { method: 'PATCH', body: JSON.stringify({ nivel }) }),

  revocar: (listaId: number, usuarioId: number) =>
    apiCall(`/api/listas/${listaId}/permisos/${usuarioId}`, { method: 'DELETE' }),

  aceptarInvitacion: (codigo: string) =>
    apiCall(`/api/listas/aceptar-invitacion/${codigo}`, { method: 'POST' }),
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
