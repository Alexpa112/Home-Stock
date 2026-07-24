'use client'

import Link from 'next/link'
import { useState, useEffect } from 'react'
import { Plus, Trash2, AlertCircle, Package, TrendingUp, Pencil, X, Tags, ShoppingCart, Clock3, TriangleAlert } from 'lucide-react'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { CategoryBadge } from '@/components/dashboard/CategoryBadge'
import { productos as productosApi, categorias as categoriasApi, listas as listasApi } from '@/lib/api'

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

const FORM_VACIO = {
  nombre: '',
  categoria: 'Otros',
  cantidad: 1,
  stock_minimo: 1,
  dias_aviso: 30,
  unidad: 'ud',
}

type FiltroStock = 'todos' | 'bajo-stock' | 'caducidad'

export default function StockPage() {
  const [items, setItems] = useState<Producto[]>([])
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState(FORM_VACIO)
  const [gestionandoCategorias, setGestionandoCategorias] = useState(false)
  const [nuevaCategoria, setNuevaCategoria] = useState('')
  const [filtroActivo, setFiltroActivo] = useState<FiltroStock>('todos')

  useEffect(() => {
    bootstrap()
  }, [])

  const bootstrap = async () => {
    try {
      setLoading(true)
      setError('')

      // Una cuenta recien creada no tiene ninguna lista todavia; sin una
      // lista activa en sesion, el backend rechaza crear productos (403).
      // Si no hay ninguna lista propia ni compartida, se crea una por
      // defecto (crear() la deja seleccionada automaticamente en sesion).
      const listasData: any = await listasApi.listar()
      if ((listasData.propias?.length || 0) === 0 && (listasData.compartidas?.length || 0) === 0) {
        await listasApi.crear('Mi lista')
      }

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
      dias_aviso: item.dias_aviso,
      unidad: item.unidad,
    })
    setShowForm(true)
  }

  const handleGuardar = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError('')
      if (editandoId) {
        await productosApi.actualizar(editandoId, {
          nombre: formData.nombre,
          categoria: formData.categoria,
          cantidad: formData.cantidad,
          stock_minimo: formData.stock_minimo,
          dias_aviso: formData.dias_aviso,
          unidad: formData.unidad,
        })
      } else {
        await productosApi.crear({
          nombre: formData.nombre,
          categoria: formData.categoria,
          cantidad: formData.cantidad,
          stock_minimo: formData.stock_minimo,
          dias_aviso: formData.dias_aviso,
          unidad: formData.unidad,
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
    if (!confirm('¿Eliminar este artículo?')) return

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
    try {
      setError('')
      await productosApi.actualizar(id, { delta })
      await bootstrap()
    } catch (err) {
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
    if (!confirm('¿Eliminar esta categoría?')) return
    try {
      setError('')
      await categoriasApi.eliminar(id)
      const categoriasData: any = await categoriasApi.listar()
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar la categoría (puede estar en uso)')
    }
  }

  const isLowStock = (item: Producto) => item.cantidad <= item.stock_minimo

  const getEstadoCardClass = (item: Producto) => {
    if (isLowStock(item) && item.revisar_caducidad) {
      return 'border-red-200 ring-2 ring-amber-200 dark:border-red-900 dark:ring-amber-900/70'
    }
    if (isLowStock(item)) return 'border-red-200 dark:border-red-900'
    if (item.revisar_caducidad) return 'border-amber-200 dark:border-amber-900'
    return ''
  }

  const getCantidadClass = (item: Producto) => (isLowStock(item) ? 'text-stock-critical' : 'text-accent')

  // Filtrar items por búsqueda
  const filteredItems = items.filter((item) => {
    const matchesQuery =
      item.nombre.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.categoria.toLowerCase().includes(searchQuery.toLowerCase())

    if (!matchesQuery) return false
    if (filtroActivo === 'bajo-stock') return isLowStock(item)
    if (filtroActivo === 'caducidad') return item.revisar_caducidad
    return true
  })

  // Calcular estadísticas
  const stats = {
    totalItems: items.length,
    totalQuantity: items.reduce((sum, item) => sum + item.cantidad, 0),
    bajoStock: items.filter((item) => isLowStock(item)).length,
    porRevisar: items.filter((item) => item.revisar_caducidad).length,
  }

  const filtros: Array<{ key: FiltroStock; label: string; count: number }> = [
    { key: 'todos', label: 'Todos', count: items.length },
    { key: 'bajo-stock', label: 'Bajo stock', count: stats.bajoStock },
    { key: 'caducidad', label: 'Revisar caducidad', count: stats.porRevisar },
  ]

  return (
    <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">Mi Stock</h1>
          <p className="text-muted-foreground mt-1">Gestiona tu inventario y detecta rápido mínimos y productos a revisar</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/dashboard/shopping" className="btn-secondary flex items-center gap-2">
            <ShoppingCart className="w-5 h-5" />
            <span>Ver compra</span>
          </Link>
          <button
            onClick={() => (showForm ? setShowForm(false) : abrirNuevo())}
            className="btn-primary flex items-center gap-2 min-h-[44px]"
          >
            <Plus className="w-5 h-5" />
            <span className="hidden sm:inline">Añadir Producto</span>
            <span className="sm:hidden">Añadir</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatsCard
          title="Artículos"
          value={stats.totalItems}
          icon={Package}
          color="blue"
          description="Productos en stock"
        />
        <StatsCard
          title="Cantidad Total"
          value={stats.totalQuantity}
          icon={TrendingUp}
          color="green"
          description="Unidades disponibles"
        />
        <StatsCard
          title="Bajo Stock"
          value={stats.bajoStock}
          icon={ShoppingCart}
          color="red"
          description="Cantidad igual o inferior al mínimo"
        />
        <StatsCard
          title="Por Revisar"
          value={stats.porRevisar}
          icon={Clock3}
          color="yellow"
          description="Revisión por caducidad o tiempo"
        />
      </div>

      {(stats.bajoStock > 0 || stats.porRevisar > 0) && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {stats.bajoStock > 0 && (
            <div className="panel-danger flex items-start justify-between gap-4">
              <div className="space-y-1">
                <p className="font-semibold">Reposición pendiente</p>
                <p className="text-sm leading-6">
                  {stats.bajoStock} producto(s) están en mínimo o por debajo. Cuando la cantidad es igual o menor que el stock mínimo,
                  el backend los considera para reponer.
                </p>
              </div>
              <Link href="/dashboard/shopping" className="btn-secondary shrink-0">
                Abrir compra
              </Link>
            </div>
          )}
          {stats.porRevisar > 0 && (
            <div className="panel-warning space-y-1">
              <p className="font-semibold">Revisión de caducidad</p>
              <p className="text-sm leading-6">
                {stats.porRevisar} producto(s) llevan tiempo sin actualizarse. Revísalos aunque no estén bajo stock.
              </p>
            </div>
          )}
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
                  <span key={cat.id} className="flex items-center gap-1 px-2 py-1 bg-card rounded-full text-xs border border-border">
                    {cat.nombre}
                    <button type="button" onClick={() => handleEliminarCategoria(cat.id)} aria-label={`Eliminar ${cat.nombre}`}>
                      <X className="w-3 h-3 text-red-500" />
                    </button>
                  </span>
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
              <label className="block text-sm font-medium mb-2">Nombre</label>
              <input
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
                <label className="block text-sm font-medium mb-2">Categoría</label>
                <select
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
                <label className="block text-sm font-medium mb-2">Unidad</label>
                <input
                  type="text"
                  value={formData.unidad}
                  onChange={(e) => setFormData({ ...formData, unidad: e.target.value })}
                  className="input-field"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Cantidad</label>
                <input
                  type="number"
                  value={formData.cantidad}
                  onChange={(e) => setFormData({ ...formData, cantidad: parseInt(e.target.value) || 0 })}
                  min="0"
                  className="input-field"
                  inputMode="numeric"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Stock mínimo</label>
                <input
                  type="number"
                  value={formData.stock_minimo}
                  onChange={(e) => {
                    const nextValue = parseInt(e.target.value, 10)
                    setFormData({ ...formData, stock_minimo: Number.isNaN(nextValue) ? 0 : Math.max(0, nextValue) })
                  }}
                  min="0"
                  className="input-field"
                  inputMode="numeric"
                />
                <p className="mt-2 text-xs text-muted-foreground">Cuando la cantidad llegue a este valor o baje más, quedará marcado para reponer. Usa 0 si solo quieres avisar al agotarse.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Aviso de revisión (días)</label>
                <input
                  type="number"
                  value={formData.dias_aviso}
                  onChange={(e) => {
                    const nextValue = parseInt(e.target.value, 10)
                    setFormData({ ...formData, dias_aviso: Number.isNaN(nextValue) ? 1 : Math.max(1, nextValue) })
                  }}
                  min="1"
                  className="input-field"
                  inputMode="numeric"
                />
                <p className="mt-2 text-xs text-muted-foreground">Si pasan estos días sin actualizar el producto, se marcará para revisar caducidad.</p>
              </div>
              <div className="panel-info flex flex-col justify-center">
                <p className="font-semibold">Diferencia clave</p>
                <p className="text-sm leading-6">
                  <strong>Bajo stock</strong> significa reponer. <strong>Revisar caducidad</strong> significa comprobar estado/fecha del producto.
                </p>
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
        <div className="panel-danger flex items-start gap-3">
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
          <div className="flex flex-wrap gap-2">
            {filtros.map((filtro) => (
              <button
                key={filtro.key}
                type="button"
                onClick={() => setFiltroActivo(filtro.key)}
                className={filtroActivo === filtro.key ? 'btn-primary' : 'btn-secondary'}
              >
                {filtro.label} ({filtro.count})
              </button>
            ))}
          </div>
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
        <div className="text-center py-12">
          <p className="text-muted-foreground">No se encontraron productos</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredItems.map((item) => (
          <div
            key={item.id}
            className={`card flex flex-col justify-between ${getEstadoCardClass(item)}`}
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-foreground line-clamp-2 mb-1">{item.nombre}</h3>
                  <div className="flex flex-wrap gap-2">
                    <CategoryBadge category={item.categoria} />
                    {isLowStock(item) && (
                      <span className="status-badge status-badge-danger">
                        <TriangleAlert className="w-3.5 h-3.5" />
                        Bajo stock
                      </span>
                    )}
                    {item.revisar_caducidad && (
                      <span className="status-badge status-badge-warning">
                        <Clock3 className="w-3.5 h-3.5" />
                        Revisar caducidad
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => abrirEdicion(item)}
                      className="p-2 hover:bg-muted rounded-lg transition-colors min-h-[44px] flex items-center justify-center"
                      aria-label="Editar"
                    >
                      <Pencil className="w-4 h-4 text-muted-foreground" />
                    </button>
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="p-2 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors min-h-[44px] flex items-center justify-center"
                      aria-label="Eliminar"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                </div>

                <div className="space-y-2 text-sm mt-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Stock mínimo</span>
                    <span className={`font-semibold ${isLowStock(item) ? 'text-stock-critical' : 'text-foreground'}`}>
                      {item.stock_minimo} {item.unidad}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Aviso revisión</span>
                    <span className="font-semibold text-foreground">{item.dias_aviso} días</span>
                  </div>
                </div>

                {isLowStock(item) && (
                  <div className="panel-danger mt-4 p-3">
                    <p className="text-sm font-semibold">Reponer pronto</p>
                    <p className="mt-1 text-sm">
                      Tiene {item.cantidad} {item.unidad} y su mínimo es {item.stock_minimo}.
                    </p>
                  </div>
                )}

                {item.revisar_caducidad && (
                  <div className="panel-warning mt-4 p-3">
                    <p className="text-sm font-semibold">Revisión recomendada</p>
                    <p className="mt-1 text-sm">
                      Lleva tiempo sin actualizarse. Comprueba su estado aunque siga habiendo stock.
                    </p>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-border mt-auto space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Cantidad ({item.unidad})</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleAjustarCantidad(item.id, -1)}
                      className="w-11 h-11 flex items-center justify-center rounded-xl border border-border hover:bg-muted"
                      aria-label="Restar"
                    >
                      -
                    </button>
                    <span className={`text-lg font-bold w-10 text-center ${getCantidadClass(item)}`}>
                      {item.cantidad}
                    </span>
                    <button
                      onClick={() => handleAjustarCantidad(item.id, 1)}
                      className="w-11 h-11 flex items-center justify-center rounded-xl border border-border hover:bg-muted"
                      aria-label="Sumar"
                    >
                      +
                    </button>
                  </div>
                </div>

                {isLowStock(item) && (
                  <Link href="/dashboard/shopping" className="btn-secondary w-full">
                    Ver lista de compra
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
