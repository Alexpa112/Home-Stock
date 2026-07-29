import { apiCall } from './api'

// Catálogo (historial estándar + personalizados del hogar) para autocompletar
// y el grid de "tocar para añadir" al dar de alta un artículo en una lista.
export function buscarCatalogo(q?: string) {
  return apiCall(`/api/historial/catalogo${q ? `?q=${encodeURIComponent(q)}` : ''}`)
}
