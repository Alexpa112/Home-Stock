export interface Categoria {
  id: number
  nombre: string
  icono: string
}

export interface Producto {
  id: number
  nombre: string
  categoria: string
  icono: string | null
  cantidad: number
  unidad: string
  stock_minimo: number
  dias_aviso: number
  fecha_actualizacion: string | null
  revisar_caducidad: boolean
}

export interface ProductoFormData {
  nombre: string
  categoria: string
  cantidad: number
  stock_minimo: number
  dias_aviso: number
  unidad: string
}

export interface ArticuloLista {
  id: number
  lista_id: number
  nombre: string
  cantidad: number
  unidad: string
  categoria: string | null
  icono: string | null
  completado: boolean
}

export interface ArticuloListaFormData {
  nombre: string
  categoria: string
  cantidad: number
}

export interface Lista {
  id: number
  nombre: string
  descripcion: string | null
  icono: string
  color: string
  privada: boolean
  usuario_propietario_id: number
  mi_rol?: string
}

export interface MiembroLista {
  id: number
  nombre_usuario: string
  email: string | null
  nivel: string
  fecha_otorgado?: string
}

export interface UsuarioAutenticado {
  usuario?: string
  email?: string | null
  tema_preferido?: string
  idioma_preferido?: string
}

export interface ProductoConsumo {
  nombre: string
  icono: string | null
  consumo: number
}

export interface ArticuloCatalogo {
  nombre: string
  icono: string | null
  categoria: string | null
  unidad: string
  cantidad_defecto: number | null
}

export interface TicketWarning {
  tipo: string
  mensaje: string
}

export interface TicketItem {
  nombre: string
  cantidad: number
  unidad: string
  categoria: string
  producto_id: number | null
  confianza_match: number
  confianza_cantidad: number
  precio_valido: boolean
  incluir?: boolean
}
