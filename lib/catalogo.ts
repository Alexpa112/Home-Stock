import { apiCall } from './api'

// Catálogo (historial estándar + personalizados del hogar) para autocompletar
// y el grid de "tocar para añadir" al dar de alta un artículo en una lista.
export function buscarCatalogo(q?: string) {
  return apiCall(`/api/historial/catalogo${q ? `?q=${encodeURIComponent(q)}` : ''}`)
}

// Busca un artículo del catálogo por código de barras/EAN escaneado (P-03).
export function buscarPorCodigoBarras(codigo: string) {
  return apiCall(`/api/historial/codigo/${encodeURIComponent(codigo)}`)
}
