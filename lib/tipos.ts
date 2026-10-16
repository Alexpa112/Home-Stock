// Tipos de datos que comparten varias pantallas (forma de las respuestas de la API).

/** Categoria de producto (GET /api/categorias). */
export interface Categoria {
  id: number
  nombre: string
  icono: string
}

/** Entrada del catalogo de autocompletado (GET /api/historial/catalogo). */
export interface ArticuloCatalogo {
  nombre: string
  icono: string | null
  categoria: string | null
  unidad: string | null
  origen: 'estandar' | 'personalizado'
}
