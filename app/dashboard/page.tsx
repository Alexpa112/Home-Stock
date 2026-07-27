'use client'

import { useState, useEffect } from 'react'
import { Plus, Trash2, AlertCircle, Package, TrendingUp, Pencil, X, Tags, ShoppingCart, Clock, Grid3x3, List } from 'lucide-react'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { CategoryBadge } from '@/components/dashboard/CategoryBadge'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { productos as productosApi, categorias as categoriasApi, articulosLista } from '@/lib/api'
import { useListPreferences } from '@/contexts/ListPreferencesContext'

// Shape real: ver stockhogar/utils/converters.py DataConverter.producto_to_dict.
// No hay fecha de caducidad absoluta; 'revisar_caducidad' es un booleano que el
// backend calcula segun cuanto tiempo ha pasado desde la ultima actualizacion
// frente a 'dias_aviso'.
interface Producto {
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

interface Categoria {
  id: number
  nombre: string
  icono: string
}

interface FormularioProducto {
  nombre: string
  categoria: string
  cantidad: number | ''
  stock_minimo: number | ''
  unidad: string
}

const FORM_VACIO: FormularioProducto = {
  nombre: '',
  categoria: 'Otros',
  cantidad: 1,
  stock_minimo: 1,
  unidad: 'ud',
  dias_aviso: 7,
}

function parseNumeroInput(value: string, fallback: number): number | '' {
  if (value === '') return ''
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export default function StockPage() {
  const { preferences, updatePreferences } = useListPreferences()
  const [items, setItems] = useState<Producto[]>([])
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState<FormularioProducto>(FORM_VACIO)
  const [gestionandoCategorias, setGestionandoCategorias] = useState(false)
  const [nuevaCategoria, setNuevaCategoria] = useState('')
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)
  const [filtro, setFiltro] = useState<'todos' | 'bajo_minimo' | 'por_revisar'>('todos')
  const [añadiendoId, setAñadiendoId] = useState<number | null>(null)
  const [añadidoIds, setAñadidoIds] = useState<Set<number>>(new Set())
  const [confirmandoEliminarCatId, setConfirmandoEliminarCatId] = useState<number | null>(null)
  const [modoVista, setModoVista] = useState<'lista' | 'grid'>('grid')
  const [agruparPorCategoria, setAgruparPorCategoria] = useState(true)

  useEffect(() => {
    // Cargar preferencias guardadas
    const modoGuardado = localStorage.getItem('stock-modo-vista') as 'lista' | 'grid' | null
    const agruparGuardado = localStorage.getItem('stock-agrupar-categoria')
    if (modoGuardado) setModoVista(modoGuardado)
    if (agruparGuardado !== null) setAgruparPorCategoria(agruparGuardado === 'true')

    bootstrap()
  }, [])

  // Guardar preferencias cuando cambien
  useEffect(() => {
    localStorage.setItem('stock-modo-vista', modoVista)
  }, [modoVista])

  useEffect(() => {
    localStorage.setItem('stock-agrupar-categoria', String(agruparPorCategoria))
  }, [agruparPorCategoria])

  const bootstrap = async () => {
    try {
      setLoading(true)
      setError('')

      // La seleccion de hogar/lista activa ahora es obligatoria antes de
      // llegar aqui (ver components/shared/SeleccionHogar.tsx), asi que ya
      // no hace falta crear una lista de emergencia en este punto.
      const [productosData, categoriasData] = await Promise.all([
        productosApi.listar(),
        categoriasApi.listar(),
      ])
      setItems(Array.isArray(productosData) ? productosData : [])
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error de conexión'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const abrirNuevo = () => {
    setEditandoId(null)
    setFormData({ ...FORM_VACIO, categoria: categorias[0]?.nombre || 'Otros' })
    setShowForm(true)
  }

  const abrirEdicion = (item: Producto) => {
    setEditandoId(item.id)
    setFormData({
      nombre: item.nombre,
      categoria: item.categoria,
      cantidad: item.cantidad,
      stock_minimo: item.stock_minimo,
      unidad: item.unidad,
      dias_aviso: item.dias_aviso,
    })
    setShowForm(true)
  }

  const getCategoryIcon = (categoryName: string | null) => {
    if (!categoryName) return null
    const cat = categorias.find((c) => c.nombre === categoryName)
    return cat?.icono || null
  }

  const handleGuardar = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError('')
      const cantidadFinal = formData.cantidad === '' ? 0 : Number(formData.cantidad)
      const stockMinimoFinal = formData.stock_minimo === '' ? 1 : Number(formData.stock_minimo)

      if (editandoId) {
        await productosApi.actualizar(editandoId, {
          nombre: formData.nombre,
          categoria: formData.categoria,
          cantidad: cantidadFinal,
          stock_minimo: stockMinimoFinal,
          unidad: formData.unidad,
          dias_aviso: formData.dias_aviso,
        })
      } else {
        await productosApi.crear({
          nombre: formData.nombre,
          categoria: formData.categoria,
          cantidad: cantidadFinal,
          stock_minimo: stockMinimoFinal,
          unidad: formData.unidad,
          dias_aviso: formData.dias_aviso,
        })
      }
      setShowForm(false)
      setEditandoId(null)
      await bootstrap()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al guardar el producto'
      setError(message)
    }
  }

  const handleDeleteItem = async (id: number) => {
    if (confirmandoId !== id) {
      setConfirmandoId(id)
      return
    }
    setConfirmandoId(null)
    try {
      setError('')
      await productosApi.eliminar(id)
      await bootstrap()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al eliminar producto'
      setError(message)
    }
  }

  const handleAjustarCantidad = async (id: number, delta: number) => {
    const itemIndex = items.findIndex(i => i.id === id)
    if (itemIndex === -1) return

    const itemAnterior = items[itemIndex]
    const cantidadNueva = Math.max(0, itemAnterior.cantidad + delta)

    setItems(prev => prev.map((item, i) =>
      i === itemIndex ? { ...item, cantidad: cantidadNueva } : item
    ))
    setError('')

    try {
      await productosApi.actualizar(id, { delta })
    } catch (err) {
      setItems(prev => prev.map((item, i) =>
        i === itemIndex ? itemAnterior : item
      ))
      const message = err instanceof Error ? err.message : 'Error al actualizar cantidad'
      setError(message)
    }
  }

  const handleCrearCategoria = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nuevaCategoria.trim()) return
    try {
      setError('')
      await categoriasApi.crear(nuevaCategoria.trim())
      setNuevaCategoria('')
      const categoriasData: any = await categoriasApi.listar()
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear la categoría')
    }
  }

  const handleEliminarCategoria = async (id: number) => {
    if (confirmandoEliminarCatId !== id) { setConfirmandoEliminarCatId(id); return }
    setConfirmandoEliminarCatId(null)
    try {
      setError('')
      await categoriasApi.eliminar(id)
      const categoriasData: any = await categoriasApi.listar()
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar la categoría (puede estar en uso)')
    }
  }

  const handleAñadirACompra = async (item: Producto) => {
    setAñadiendoId(item.id)
    try {
      await articulosLista.anadir(item.nombre, {
        cantidad: Math.max(1, item.stock_minimo - item.cantidad),
        unidad: item.unidad,
        categoria: item.categoria,
      })
      setAñadidoIds(prev => new Set(prev).add(item.id))
    } catch {
      // silencioso — el usuario puede ir a la lista de compra a verificar
    } finally {
      setAñadiendoId(null)
    }
  }

  const handleAñadirTodosACompra = async () => {
    const bajos = items.filter(i => i.cantidad <= i.stock_minimo && !añadidoIds.has(i.id))
    for (const item of bajos) {
      await handleAñadirACompra(item)
    }
  }

  // Filtrar items por búsqueda y filtro activo
  const itemsFiltrados = items.filter((item) => {
    if (filtro === 'bajo_minimo') return item.cantidad <= item.stock_minimo
    if (filtro === 'por_revisar') return item.revisar_caducidad
    return true
  })

  const filteredItems = itemsFiltrados.filter((item) =>
    item.nombre.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.categoria.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Calcular estadísticas
  const stats = {
    totalItems: items.length,
    totalQuantity: items.reduce((sum, item) => sum + item.cantidad, 0),
    porRevisar: items.filter((item) => item.revisar_caducidad).length,
    bajoMinimo: items.filter((item) => item.cantidad <= item.stock_minimo).length,
  }

  // Vista "Grid": tarjeta con toda la info a la vista, pensada para pantallas
  // anchas o para explorar el inventario con calma.
  const renderProductoGrid = (item: Producto) => (
    <div key={item.id} className="card flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground line-clamp-2 mb-1">{item.nombre}</h3>
            <CategoryBadge category={item.categoria} icon={getCategoryIcon(item.categoria)} />
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={() => abrirEdicion(item)}
              className="w-10 h-10 flex items-center justify-center hover:bg-muted rounded-xl transition-colors"
              aria-label="Editar"
            >
              <Pencil className="w-4 h-4 text-muted-foreground" />
            </button>
            {confirmandoId === item.id ? (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleDeleteItem(item.id)}
                  className="px-2 h-10 flex items-center text-xs font-semibold text-white bg-red-500 rounded-xl transition-colors"
                  aria-label="Confirmar eliminación"
                >
                  Sí
                </button>
                <button
                  onClick={() => setConfirmandoId(null)}
                  className="px-2 h-10 flex items-center text-xs font-semibold text-foreground bg-muted rounded-xl transition-colors"
                  aria-label="Cancelar"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                onClick={() => handleDeleteItem(item.id)}
                className="w-10 h-10 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors"
                aria-label="Eliminar"
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            )}
          </div>
        </div>

        {(item.cantidad <= item.stock_minimo || item.revisar_caducidad) && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {item.cantidad <= item.stock_minimo && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300">
                <ShoppingCart className="w-3 h-3" />
                Bajo mínimo
              </span>
            )}
            {item.revisar_caducidad && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300">
                <Clock className="w-3 h-3" />
                Revisar
              </span>
            )}
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-border mt-auto space-y-2">
        {/* Cantidad +/- */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{item.unidad}</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => handleAjustarCantidad(item.id, -1)}
              className="w-11 h-11 flex items-center justify-center rounded-xl border border-border bg-card hover:bg-muted active:scale-95 transition-all text-lg font-medium"
              aria-label="Restar uno"
              disabled={item.cantidad <= 0}
            >
              −
            </button>
            <span className={`text-xl font-bold w-10 text-center tabular-nums ${item.cantidad <= item.stock_minimo ? 'text-red-500 dark:text-red-400' : 'text-accent'}`}>
              {item.cantidad}
            </span>
            <button
              onClick={() => handleAjustarCantidad(item.id, 1)}
              className="w-11 h-11 flex items-center justify-center rounded-xl border border-border bg-card hover:bg-muted active:scale-95 transition-all text-lg font-medium"
              aria-label="Sumar uno"
            >
              +
            </button>
          </div>
        </div>

        {/* Acción rápida: añadir a compra si está bajo mínimo */}
        {item.cantidad <= item.stock_minimo && (
          <button
            onClick={() => handleAñadirACompra(item)}
            disabled={añadiendoId === item.id || añadidoIds.has(item.id)}
            className={`w-full flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-semibold transition-all active:scale-95 ${
              añadidoIds.has(item.id)
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                : 'bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-950/40 dark:hover:bg-red-950/70 dark:text-red-300'
            }`}
          >
            {añadidoIds.has(item.id) ? (
              <>✓ Añadido a la compra</>
            ) : añadiendoId === item.id ? (
              <>Añadiendo...</>
            ) : (
              <><ShoppingCart className="w-3.5 h-3.5" /> Añadir a la compra</>
            )}
          </button>
        )}
      </div>
    </div>
  )

  // Vista "Lista": fila compacta al estilo Bring! — icono, nombre y
  // cantidad en una sola línea, pensada para revisar el inventario rápido.
  const renderProductoLista = (item: Producto) => {
    const icono = getCategoryIcon(item.categoria)
    const bajoMinimo = item.cantidad <= item.stock_minimo
    return (
      <div key={item.id} className="card !p-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center shrink-0">
          {icono ? (
            <IconRenderer name={icono} className="w-5 h-5 text-muted-foreground" />
          ) : (
            <Package className="w-5 h-5 text-muted-foreground" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="font-medium text-foreground truncate">{item.nombre}</p>
            {bajoMinimo && <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" title="Bajo mínimo" />}
            {item.revisar_caducidad && <span className="w-2 h-2 rounded-full bg-yellow-500 shrink-0" title="Revisar caducidad" />}
          </div>
          <p className="text-xs text-muted-foreground truncate">{item.categoria} · {item.unidad}</p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => handleAjustarCantidad(item.id, -1)}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-border bg-card hover:bg-muted active:scale-95 transition-all text-base font-medium"
            aria-label="Restar uno"
            disabled={item.cantidad <= 0}
          >
            −
          </button>
          <span className={`text-base font-bold w-7 text-center tabular-nums ${bajoMinimo ? 'text-red-500 dark:text-red-400' : 'text-accent'}`}>
            {item.cantidad}
          </span>
          <button
            onClick={() => handleAjustarCantidad(item.id, 1)}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-border bg-card hover:bg-muted active:scale-95 transition-all text-base font-medium"
            aria-label="Sumar uno"
          >
            +
          </button>
        </div>

        {bajoMinimo && (
          <button
            onClick={() => handleAñadirACompra(item)}
            disabled={añadiendoId === item.id || añadidoIds.has(item.id)}
            className={`w-9 h-9 flex items-center justify-center rounded-lg shrink-0 transition-all active:scale-95 ${
              añadidoIds.has(item.id)
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                : 'bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-950/40 dark:hover:bg-red-950/70 dark:text-red-300'
            }`}
            aria-label="Añadir a la compra"
            title="Añadir a la compra"
          >
            <ShoppingCart className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={() => abrirEdicion(item)}
          className="w-9 h-9 flex items-center justify-center hover:bg-muted rounded-lg transition-colors shrink-0"
          aria-label="Editar"
        >
          <Pencil className="w-4 h-4 text-muted-foreground" />
        </button>

        {confirmandoId === item.id ? (
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => handleDeleteItem(item.id)}
              className="px-2 h-9 flex items-center text-xs font-semibold text-white bg-red-500 rounded-lg transition-colors"
              aria-label="Confirmar eliminación"
            >
              Sí
            </button>
            <button
              onClick={() => setConfirmandoId(null)}
              className="px-2 h-9 flex items-center text-xs font-semibold text-foreground bg-muted rounded-lg transition-colors"
              aria-label="Cancelar"
            >
              No
            </button>
          </div>
        ) : (
          <button
            onClick={() => handleDeleteItem(item.id)}
            className="w-9 h-9 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors shrink-0"
            aria-label="Eliminar"
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </button>
        )}
      </div>
    )
  }

  const renderProducto = (item: Producto) => (modoVista === 'lista' ? renderProductoLista(item) : renderProductoGrid(item))

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">Mi Stock</h1>
          <p className="text-muted-foreground mt-1">Gestiona tu inventario del hogar</p>
        </div>
        <button
          onClick={() => (showForm ? setShowForm(false) : abrirNuevo())}
          className="btn-primary flex items-center gap-2 min-h-[44px]"
        >
          <Plus className="w-5 h-5" />
          <span className="hidden sm:inline">Añadir Producto</span>
          <span className="sm:hidden">Añadir</span>
        </button>
      </div>

      {/* Filtros compactos — opciones de filtrado rápido */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setFiltro('todos')}
          aria-label="Ver todos los artículos"
          aria-pressed={filtro === 'todos'}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            filtro === 'todos'
              ? 'bg-accent text-accent-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          📦 {stats.totalItems} artículos
        </button>
        <button
          onClick={() => setFiltro(filtro === 'bajo_minimo' ? 'todos' : 'bajo_minimo')}
          aria-label={filtro === 'bajo_minimo' ? 'Quitar filtro de bajo stock' : 'Filtrar por bajo stock'}
          aria-pressed={filtro === 'bajo_minimo'}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            filtro === 'bajo_minimo'
              ? 'bg-red-500 text-white'
              : stats.bajoMinimo > 0
              ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-950/60'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          🛒 {stats.bajoMinimo} bajo stock
        </button>
        <button
          onClick={() => setFiltro(filtro === 'por_revisar' ? 'todos' : 'por_revisar')}
          aria-label={filtro === 'por_revisar' ? 'Quitar filtro de caducidad' : 'Filtrar por revisar caducidad'}
          aria-pressed={filtro === 'por_revisar'}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            filtro === 'por_revisar'
              ? 'bg-yellow-500 text-white'
              : stats.porRevisar > 0
              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-950/60'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          ⏱️ {stats.porRevisar} caducados
        </button>
      </div>

      {/* Acción masiva cuando filtramos por bajo mínimo */}
      {filtro === 'bajo_minimo' && stats.bajoMinimo > 0 && (
        <div className="flex items-center justify-between gap-3 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-xl">
          <p className="text-sm text-red-700 dark:text-red-300 font-medium">
            {stats.bajoMinimo} {stats.bajoMinimo === 1 ? 'producto bajo' : 'productos bajos'} de stock mínimo
          </p>
          <button
            onClick={handleAñadirTodosACompra}
            className="shrink-0 flex items-center gap-2 px-3 py-2 bg-red-500 hover:bg-red-600 text-white text-sm font-semibold rounded-xl transition-colors active:scale-95"
          >
            <ShoppingCart className="w-4 h-4" />
            Añadir todos
          </button>
        </div>
      )}

      {/* Add / Edit Form */}
      {showForm && (
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{editandoId ? 'Editar Producto' : 'Nuevo Producto'}</h2>
            <button
              type="button"
              onClick={() => setGestionandoCategorias(!gestionandoCategorias)}
              className="text-sm text-accent hover:underline flex items-center gap-1"
            >
              <Tags className="w-4 h-4" /> Categorías
            </button>
          </div>

          {gestionandoCategorias && (
            <div className="p-3 bg-muted rounded-lg space-y-2">
              <div className="flex flex-wrap gap-2">
                {categorias.map((cat) => (
                  confirmandoEliminarCatId === cat.id ? (
                    <span key={cat.id} className="flex items-center gap-1 px-2 py-1 bg-card rounded-full text-xs border border-red-300 dark:border-red-700">
                      <span className="text-red-600 dark:text-red-400 mr-0.5">¿Eliminar?</span>
                      <button type="button" onClick={() => handleEliminarCategoria(cat.id)} className="px-1.5 py-0.5 text-white bg-red-500 rounded-md font-medium">Sí</button>
                      <button type="button" onClick={() => setConfirmandoEliminarCatId(null)} className="px-1.5 py-0.5 bg-muted rounded-md font-medium">No</button>
                    </span>
                  ) : (
                    <span key={cat.id} className="flex items-center gap-1 px-2 py-1 bg-card rounded-full text-xs border border-border">
                      {cat.nombre}
                      <button type="button" onClick={() => handleEliminarCategoria(cat.id)} aria-label={`Eliminar ${cat.nombre}`}>
                        <X className="w-3 h-3 text-red-500" />
                      </button>
                    </span>
                  )
                ))}
              </div>
              <form onSubmit={handleCrearCategoria} className="flex gap-2">
                <input
                  type="text"
                  value={nuevaCategoria}
                  onChange={(e) => setNuevaCategoria(e.target.value)}
                  placeholder="Nueva categoría"
                  className="input-field !py-1.5 flex-1"
                />
                <button type="submit" className="btn-secondary !py-1.5">Añadir</button>
              </form>
            </div>
          )}

          <form onSubmit={handleGuardar} className="space-y-4">
            <div>
              <label htmlFor="prod-nombre" className="block text-sm font-medium mb-2">Nombre</label>
              <input
                id="prod-nombre"
                type="text"
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder="ej: Leche, Arroz, Detergente..."
                className="input-field"
                required
                inputMode="text"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="prod-categoria" className="block text-sm font-medium mb-2">Categoría</label>
                <select
                  id="prod-categoria"
                  value={formData.categoria}
                  onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
                  className="input-field"
                >
                  {categorias.map((cat) => (
                    <option key={cat.id} value={cat.nombre}>
                      {cat.nombre}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="prod-unidad" className="block text-sm font-medium mb-2">Unidad</label>
                <input
                  id="prod-unidad"
                  type="text"
                  value={formData.unidad}
                  onChange={(e) => setFormData({ ...formData, unidad: e.target.value })}
                  className="input-field"
                />
              </div>
            </div>

            {/* En móvil: 2 cols arriba + 1 col abajo; en sm+: 3 cols */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <label htmlFor="prod-cantidad" className="block text-sm font-medium mb-1.5">Cantidad</label>
                <input
                  id="prod-cantidad"
                  type="number"
                  value={formData.cantidad}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      cantidad: parseNumeroInput(e.target.value, 0),
                    })
                  }
                  min="0"
                  className="input-field"
                  inputMode="numeric"
                />
              </div>

              <div>
                <label htmlFor="prod-minimo" className="block text-sm font-medium mb-1.5">Stock mínimo</label>
                <input
                  id="prod-minimo"
                  type="number"
                  value={formData.stock_minimo}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      stock_minimo: parseNumeroInput(e.target.value, 1),
                    })
                  }
                  min="0"
                  className="input-field"
                  inputMode="numeric"
                />
              </div>

              <div className="col-span-2 sm:col-span-1">
                <label htmlFor="prod-dias" className="block text-sm font-medium mb-1.5">
                  Días sin actualizar para avisar
                </label>
                <input
                  id="prod-dias"
                  type="number"
                  value={formData.dias_aviso}
                  onChange={(e) => setFormData({ ...formData, dias_aviso: parseInt(e.target.value) || 7 })}
                  min="1"
                  max="365"
                  className="input-field"
                  inputMode="numeric"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">
                {editandoId ? 'Guardar cambios' : 'Guardar'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false)
                  setEditandoId(null)
                }}
                className="btn-secondary flex-1"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Error</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Search Bar */}
      {items.length > 0 && !loading && (
        <div className="space-y-3">
          <SearchBar
            placeholder="Buscar por nombre o categoría..."
            value={searchQuery}
            onChange={setSearchQuery}
          />
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.agrupar_categorias === 'on'}
              onChange={(e) => updatePreferences({ agrupar_categorias: e.target.checked ? 'on' : 'off' })}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm font-medium">Agrupar por categoría</span>
          </label>
        </div>
      )}

      {/* Vista selector y opciones */}
      {items.length > 0 && !loading && (
        <div className="flex items-center justify-between gap-2">
          <div className="flex gap-2">
            <button
              onClick={() => setModoVista('lista')}
              className={`px-3 py-2 rounded-lg font-medium text-sm transition-colors ${modoVista === 'lista' ? 'bg-accent text-accent-foreground' : 'bg-muted text-muted-foreground hover:bg-muted-darker'}`}
              title="Vista de lista"
            >
              📋 Lista
            </button>
            <button
              onClick={() => setModoVista('grid')}
              className={`px-3 py-2 rounded-lg font-medium text-sm transition-colors ${modoVista === 'grid' ? 'bg-accent text-accent-foreground' : 'bg-muted text-muted-foreground hover:bg-muted-darker'}`}
              title="Vista de grid"
            >
              ⊞ Grid
            </button>
          </div>
          <button
            onClick={() => setAgruparPorCategoria(!agruparPorCategoria)}
            className={`px-3 py-2 rounded-lg font-medium text-sm transition-colors ${agruparPorCategoria ? 'bg-accent text-accent-foreground' : 'bg-muted text-muted-foreground hover:bg-muted-darker'}`}
            title={agruparPorCategoria ? 'Agrupar por categoría' : 'Sin agrupar'}
          >
            {agruparPorCategoria ? '📂 Agrupado' : '📄 Sin agrupar'}
          </button>
        </div>
      )}

      {/* Stock List */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Cargando inventario...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No hay productos en el inventario</p>
          <button
            onClick={abrirNuevo}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Añadir el Primer Producto
          </button>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-12 space-y-2">
          {searchQuery ? (
            <>
              <p className="text-muted-foreground">Sin resultados para <strong>«{searchQuery}»</strong></p>
              <button onClick={() => setSearchQuery('')} className="text-sm text-accent hover:underline">Limpiar búsqueda</button>
            </>
          ) : filtro === 'bajo_minimo' ? (
            <p className="text-muted-foreground">¡Todo en orden! No hay productos bajo el mínimo.</p>
          ) : filtro === 'por_revisar' ? (
            <p className="text-muted-foreground">No hay productos pendientes de revisión.</p>
          ) : (
            <p className="text-muted-foreground">No se encontraron productos.</p>
          )}
        </div>
      ) : agruparPorCategoria ? (
        // Vista agrupada por categoría
        <div className="space-y-6">
          {categorias.map((cat) => {
            const productosCat = filteredItems.filter(item => item.categoria === cat.nombre)
            if (productosCat.length === 0) return null
            return (
              <div key={cat.id}>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <span className="text-2xl">{cat.icono}</span>
                  {cat.nombre}
                  <span className="text-xs text-muted-foreground ml-auto">{productosCat.length} producto{productosCat.length !== 1 ? 's' : ''}</span>
                </h2>
                <div className={modoVista === 'lista' ? 'space-y-2' : 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'}>
                  {productosCat.map(renderProducto)}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        // Vista sin agrupar
        <div className={modoVista === 'lista' ? 'space-y-2' : 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'}>
          {filteredItems.map(renderProducto)}
        </div>
      )}
    </div>
  )
}

