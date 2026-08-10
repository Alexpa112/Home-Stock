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
import { clearAllCache } from './dataCache'

interface FetchOptions extends RequestInit {
  headers?: Record<string, string>
}

let csrfTokenCache: string | null = null
let csrfTokenPromesa: Promise<string> | null = null

async function obtenerCsrfToken(forzarRefresco = false): Promise<string> {
  // Si hay una petición en vuelo, esperamos a ella (evita race conditions)
  if (!forzarRefresco && csrfTokenPromesa) {
    return csrfTokenPromesa
  }

  if (csrfTokenCache && !forzarRefresco) return csrfTokenCache

  // Cachear la promesa para evitar múltiples peticiones simultáneas
  csrfTokenPromesa = (async () => {
    const res = await fetch('/api/csrf-token', { credentials: 'include' })
    const datos = await res.json()
    csrfTokenCache = datos.csrf_token
    csrfTokenPromesa = null
    return csrfTokenCache as string
  })()

  return csrfTokenPromesa
}

function resetearCsrfToken() {
  csrfTokenCache = null
  csrfTokenPromesa = null
}

function establecerCsrfToken(token: string | null) {
  if (token) {
    csrfTokenCache = token
    csrfTokenPromesa = null
  }
}

const METODOS_MUTABLES = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

// Como apiCall pero para multipart/form-data (subida de imagen de ticket):
// no se fija Content-Type (el navegador pone el boundary solo) ni se
// serializa el body a JSON.
export async function apiUpload<T = any>(endpoint: string, formData: FormData, timeoutMs = 120_000): Promise<T> {
  const csrfToken = await obtenerCsrfToken()
  // AbortController con timeout: si el servidor corta la conexión sin cerrar
  // bien el socket (p.ej. worker de gunicorn matado a mitad de un OCR largo),
  // fetch se queda esperando indefinidamente y el spinner nunca termina.
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  let response: Response
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-CSRFToken': csrfToken },
      body: formData,
      signal: controller.signal,
    })
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('La operación ha tardado demasiado. Prueba con una foto más ligera o con más luz.')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
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

// Como apiCall pero para descargar un blob (CSV/exportaciones): no espera
// JSON de vuelta, dispara la descarga en el navegador vía un <a> sintético.
export async function apiDownload(endpoint: string, filenameFallback: string): Promise<void> {
  const response = await fetch(endpoint, { credentials: 'include' })

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    const datos = contentType.includes('application/json') ? await response.json().catch(() => null) : null
    if (response.status === 503 && datos?.mantenimiento) {
      marcarMantenimiento(true)
    }
    throw new Error((datos && datos.error) || `Error HTTP ${response.status}`)
  }

  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const match = /filename="?([^"]+)"?/.exec(disposition)
  const filename = match ? match[1] : filenameFallback

  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = filename
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
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

  // Sesión invalidada (S-19): p.ej. otro dispositivo cambió la contraseña o
  // pulsó "cerrar otras sesiones" (ver session_version, stockhogar/api/base.py).
  // Sin esto, un usuario que vuelve a entrar en el mismo dispositivo con OTRA
  // cuenta seguiría viendo en caché los datos de la sesión anterior.
  if (response.status === 401) {
    clearAllCache()
    resetearCsrfToken()
  }

  if (!response.ok) {
    throw new Error((datos && datos.error) || `Error HTTP ${response.status}`)
  }

  return datos as T
}

// ===== Autenticación (stockhogar/rutas/auth.py) =====
export const auth = {
  estado: () => apiCall('/api/auth/estado'),

  login: async (usuario: string, password: string) => {
    const result: any = await apiCall('/api/auth/login', { method: 'POST', body: JSON.stringify({ usuario, password }) })
    if (result?.csrf_token) {
      establecerCsrfToken(result.csrf_token)
    } else {
      resetearCsrfToken()
    }
    return result
  },

  registrar: async (usuario: string, password: string, aceptaTerminos: boolean) => {
    const result: any = await apiCall('/api/auth/registrar', {
      method: 'POST',
      body: JSON.stringify({ usuario, password, acepta_terminos: aceptaTerminos }),
    })
    if (result?.csrf_token) {
      establecerCsrfToken(result.csrf_token)
    } else {
      resetearCsrfToken()
    }
    return result
  },

  aceptarTerminos: () => apiCall('/api/auth/aceptar-terminos', { method: 'POST' }),

  verificarCodigo: async (codigo: string) => {
    const result: any = await apiCall('/api/auth/verificar-codigo', { method: 'POST', body: JSON.stringify({ codigo }) })
    if (result?.csrf_token) {
      establecerCsrfToken(result.csrf_token)
    } else {
      resetearCsrfToken()
    }
    return result
  },

  reenviarCodigo: () => apiCall('/api/auth/reenviar-codigo', { method: 'POST' }),

  cambiarDobleFactor: async (activo: boolean) => {
    const result = await apiCall('/api/auth/doble-factor', { method: 'POST', body: JSON.stringify({ activo }) })
    resetearCsrfToken()
    return result
  },

  cambiarPreferenciaOcr: (ocrLocal: boolean) =>
    apiCall('/api/auth/preferencia-ocr', { method: 'POST', body: JSON.stringify({ ocr_local: ocrLocal }) }),

  logout: async () => {
    const resultado = await apiCall('/api/auth/logout', { method: 'POST' })
    clearAllCache()
    resetearCsrfToken()
    return resultado
  },

  actualizarPerfil: (datos: { usuario?: string; nombre?: string; password?: string }) =>
    apiCall('/api/auth/perfil', { method: 'PUT', body: JSON.stringify(datos) }),

  cambiarTema: (tema: 'light' | 'dark' | 'auto') =>
    apiCall('/api/auth/tema', { method: 'POST', body: JSON.stringify({ tema }) }),

  enviarVerificacionEmail: () => apiCall('/api/auth/enviar-verificacion-email', { method: 'POST' }),

  verificarEmail: (token: string) => apiCall(`/api/auth/verificar-email/${token}`),

  solicitarResetPassword: (usuarioOEmail: string) =>
    apiCall('/api/auth/solicitar-reset-password', {
      method: 'POST',
      body: JSON.stringify({ usuario_o_email: usuarioOEmail }),
    }),

  restablecerPassword: (token: string, passwordNueva: string) =>
    apiCall('/api/auth/restablecer-password', {
      method: 'POST',
      body: JSON.stringify({ token, password_nueva: passwordNueva }),
    }),

  cerrarOtrasSesiones: async () => {
    const result = await apiCall('/api/auth/cerrar-otras-sesiones', { method: 'POST' })
    resetearCsrfToken()
    return result
  },

  misEventosSeguridad: () => apiCall('/api/auth/mis-eventos-seguridad'),

  exportarMisDatos: () => apiDownload('/api/auth/exportar-mis-datos', 'mis-datos-dreame.zip'),

  cambiarPassword: async (password_actual: string, password_nueva: string, password_confirmacion: string) => {
    const result = await apiCall('/api/auth/cambiar-password', {
      method: 'POST',
      body: JSON.stringify({ password_actual, password_nueva, password_confirmacion }),
    })
    resetearCsrfToken()
    return result
  },

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

  // Lista básica (id + nombre_usuario) accesible a cualquier miembro del
  // hogar, a diferencia de permisos.miembros (solo propietario).
  miembrosBasico: (hogarId: number) => apiCall(`/api/hogares/${hogarId}/miembros-basico`),
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

  historialPrecios: (id: number) => apiCall(`/api/productos/${id}/precios`),

  exportarCsv: () => apiDownload('/api/productos/exportar', 'inventario.csv'),

  importarCsv: (fichero: File) => {
    const formData = new FormData()
    formData.append('fichero', fichero)
    return apiUpload('/api/productos/importar', formData)
  },
}

// ===== Lista de la compra (stockhogar/rutas/articulos_compra.py) =====
export const articulosLista = {
  // Devuelve { pendientes: [...], completados: [...] }
  listar: () => apiCall('/api/articulos'),

  anadir: (nombre: string, opciones: { cantidad?: number; unidad?: string; categoria?: string; icono?: string; codigo_barras?: string } = {}) =>
    apiCall('/api/articulos', { method: 'POST', body: JSON.stringify({ nombre, ...opciones }) }),

  marcarComprado: (id: number) =>
    apiCall(`/api/articulos/${id}`, { method: 'PATCH', body: JSON.stringify({ activo: false }) }),

  restaurar: (id: number) =>
    apiCall(`/api/articulos/${id}`, { method: 'PATCH', body: JSON.stringify({ activo: true }) }),

  actualizar: (id: number, datos: Record<string, unknown>) =>
    apiCall(`/api/articulos/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),

  eliminar: (id: number) => apiCall(`/api/articulos/${id}`, { method: 'DELETE' }),

  exportarCsv: () => apiDownload('/api/articulos/exportar', 'lista_compra.csv'),

  importarCsv: (fichero: File) => {
    const formData = new FormData()
    formData.append('fichero', fichero)
    return apiUpload('/api/articulos/importar', formData)
  },
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

// ===== Categorías de gasto (stockhogar/rutas/categorias_gasto.py) =====
export const categoriasGasto = {
  listar: () => apiCall('/api/categorias-gasto'),
  crear: (nombre: string, icono?: string) =>
    apiCall('/api/categorias-gasto', { method: 'POST', body: JSON.stringify({ nombre, icono }) }),
  eliminar: (id: number) => apiCall(`/api/categorias-gasto/${id}`, { method: 'DELETE' }),
}

// ===== Hogares compartidos / permisos (stockhogar/rutas/permisos.py) =====
export const permisos = {
  buscarUsuarios: (q: string) => apiCall(`/api/hogares/buscar-usuarios?q=${encodeURIComponent(q)}`),

  // { propietario: {...}, miembros: [...] }
  miembros: (hogarId: number) => apiCall(`/api/hogares/${hogarId}/miembros`),

  // Por nombre de usuario (acceso inmediato) o por email (crea invitación).
  compartir: (hogarId: number, datos: { usuario?: string; email?: string; nivel?: 'ver' | 'comprar' | 'editar' }) =>
    apiCall(`/api/hogares/${hogarId}/compartir`, { method: 'POST', body: JSON.stringify(datos) }),

  // Generar enlace compartible público
  generarEnlace: (hogarId: number) =>
    apiCall(`/api/hogares/${hogarId}/enlace-compartible`, { method: 'POST' }),

  actualizarPermiso: (hogarId: number, usuarioId: number, nivel: 'ver' | 'comprar' | 'editar') =>
    apiCall(`/api/hogares/${hogarId}/permisos/${usuarioId}`, { method: 'PATCH', body: JSON.stringify({ nivel }) }),

  revocar: (hogarId: number, usuarioId: number) =>
    apiCall(`/api/hogares/${hogarId}/permisos/${usuarioId}`, { method: 'DELETE' }),

  aceptarInvitacion: (codigo: string) =>
    apiCall(`/api/hogares/aceptar-invitacion/${codigo}`, { method: 'POST' }),

  invitacionesPendientes: () => apiCall('/api/hogares/invitaciones-pendientes'),

  rechazarInvitacion: (codigo: string) =>
    apiCall(`/api/hogares/invitaciones-pendientes/${codigo}`, { method: 'DELETE' }),
}

// ===== Gastos compartidos del hogar (stockhogar/rutas/gastos.py) =====
export const gastos = {
  listar: () => apiCall('/api/gastos'),

  resumenMes: () => apiCall('/api/gastos/resumen-mes'),

  crear: (datos: {
    descripcion: string
    importe_total: number
    usuario_pagador_id: number
    fecha?: string
    categoria?: string | null
    participantes: Array<{ usuario_id: number; importe: number }>
  }) => apiCall('/api/gastos', { method: 'POST', body: JSON.stringify(datos) }),

  actualizar: (id: number, datos: Record<string, unknown>) =>
    apiCall(`/api/gastos/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),

  eliminar: (id: number) => apiCall(`/api/gastos/${id}`, { method: 'DELETE' }),

  // Saldo neto por miembro del hogar activo: positivo = le deben, negativo = debe.
  saldo: () => apiCall('/api/gastos/saldo'),

  // Pagos sugeridos que saldan el hogar con el mínimo número de transacciones.
  simplificar: () => apiCall('/api/gastos/simplificar'),

  registrarLiquidacion: (datos: { usuario_origen_id: number; usuario_destino_id: number; importe: number; nota?: string }) =>
    apiCall('/api/gastos/liquidaciones', { method: 'POST', body: JSON.stringify(datos) }),

  listarLiquidaciones: () => apiCall('/api/gastos/liquidaciones'),

  eliminarLiquidacion: (id: number) => apiCall(`/api/gastos/liquidaciones/${id}`, { method: 'DELETE' }),

  subirRecibo: (id: number, foto: File) => {
    const formData = new FormData()
    formData.append('foto', foto)
    return apiUpload(`/api/gastos/${id}/recibo`, formData)
  },

  // URL de la foto de recibo adjunta (para <img src>): el navegador la pide
  // con la cookie de sesión, sin pasar por apiCall.
  reciboUrl: (id: number) => `/api/gastos/${id}/recibo`,

  eliminarRecibo: (id: number) => apiCall(`/api/gastos/${id}/recibo`, { method: 'DELETE' }),

  listarRecurrentes: () => apiCall('/api/gastos/recurrentes'),

  crearRecurrente: (datos: {
    descripcion: string
    importe_total: number
    usuario_pagador_id: number
    categoria?: string | null
    frecuencia: 'semanal' | 'mensual' | 'anual'
    fecha_inicio: string
    fecha_fin?: string | null
    participantes: Array<{ usuario_id: number; importe: number }>
  }) => apiCall('/api/gastos/recurrentes', { method: 'POST', body: JSON.stringify(datos) }),

  pausarRecurrente: (id: number, activo: boolean) =>
    apiCall(`/api/gastos/recurrentes/${id}`, { method: 'PATCH', body: JSON.stringify({ activo }) }),

  eliminarRecurrente: (id: number) => apiCall(`/api/gastos/recurrentes/${id}`, { method: 'DELETE' }),

  exportarCsv: () => apiDownload('/api/gastos/exportar', 'gastos.csv'),
}

// ===== Escaneo de tickets (stockhogar/rutas/tickets.py) =====
export const tickets = {
  // Sube la foto y devuelve { items: [...], resumen: {...}, advertencias: [...] }
  analizar: (foto: File) => {
    const formData = new FormData()
    formData.append('foto', foto)
    // 270s, el escalón externo de la cadena de timeouts del escáner (llamada a
    // la API 180s < worker de gunicorn 240s < este abort, ver
    // stockhogar/servicios/ocr/claude_ocr.py). Va por encima del worker a
    // propósito: así, cuando algo se pasa de tiempo, el usuario recibe el error
    // real del servidor en vez de un abort del navegador que no dice nada.
    // Solo se amplía aquí; el resto de subidas siguen con el defecto de 120s.
    return apiUpload('/api/tickets/analizar', formData, 270_000)
  },

  confirmar: (
    items: Array<{ nombre: string; cantidad: number; unidad?: string; categoria?: string; producto_id?: number | null }>
  ) => apiCall('/api/tickets/confirmar', { method: 'POST', body: JSON.stringify({ items }) }),
}

// ===== Historial / catálogo aprendido (stockhogar/rutas/historial.py) =====
export const historial = {
  listar: () => apiCall('/api/historial'),
}

// ===== Recetas (stockhogar/rutas/recetas.py) =====
export const recetas = {
  listar: () => apiCall('/api/recetas'),

  crear: (datos: { nombre: string; icono?: string; ingredientes: Array<{ nombre: string; cantidad?: number; unidad?: string }> }) =>
    apiCall('/api/recetas', { method: 'POST', body: JSON.stringify(datos) }),

  actualizar: (id: number, datos: Record<string, unknown>) =>
    apiCall(`/api/recetas/${id}`, { method: 'PATCH', body: JSON.stringify(datos) }),

  eliminar: (id: number) => apiCall(`/api/recetas/${id}`, { method: 'DELETE' }),

  anadirALista: (id: number) => apiCall(`/api/recetas/${id}/anadir-a-lista`, { method: 'POST' }),
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

// ===== Configuración pública para páginas legales (stockhogar/rutas/legal.py) =====
export const legal = {
  configuracion: (): Promise<{ titular: string; email_contacto: string; dominio: string; version_terminos: string }> =>
    apiCall('/api/legal/config'),
}

// ===== Notificaciones push (stockhogar/rutas/push.py, P-01) =====
export const push = {
  vapidClavePublica: (): Promise<{ clave_publica: string }> => apiCall('/api/push/vapid-clave-publica'),

  suscribir: (endpoint: string, keys: { p256dh: string; auth: string }) =>
    apiCall('/api/push/suscribir', { method: 'POST', body: JSON.stringify({ endpoint, keys }) }),

  desuscribir: (endpoint: string) =>
    apiCall('/api/push/desuscribir', { method: 'POST', body: JSON.stringify({ endpoint }) }),
}
