'use client'

import { useState, useEffect } from 'react'
import { Plus, Trash2, CheckCircle2, Circle, AlertCircle, ShoppingCart, Pencil, Check } from 'lucide-react'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { CategoryBadge } from '@/components/dashboard/CategoryBadge'
import { articulosLista, categorias as categoriasApi } from '@/lib/api'

// Shape real: ver stockhogar/utils/converters.py DataConverter.articulo_lista_to_dict.
interface ArticuloLista {
  id: number
  lista_id: number
  nombre: string
  cantidad: number
  unidad: string
  categoria: string | null
  icono: string | null
  completado: boolean
}

interface Categoria {
  id: number
  nombre: string
  icono: string
}

export default function ShoppingPage() {
  const [pendientes, setPendientes] = useState<ArticuloLista[]>([])
  const [completados, setCompletados] = useState<ArticuloLista[]>([])
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState({
    nombre: '',
    categoria: 'Otros',
    cantidad: 1,
  })
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [edicion, setEdicion] = useState({ nombre: '', cantidad: 1 })

  useEffect(() => {
    loadItems()
    categoriasApi.listar().then((data: any) => setCategorias(Array.isArray(data) ? data : [])).catch(() => {})
  }, [])

  const loadItems = async () => {
    try {
      setLoading(true)
      setError('')
      const data: any = await articulosLista.listar()
      setPendientes(data?.pendientes || [])
      setCompletados(data?.completados || [])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error de conexión'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError('')
      await articulosLista.anadir(formData.nombre, {
        categoria: formData.categoria,
        cantidad: formData.cantidad,
      })
      setFormData({ nombre: '', categoria: formData.categoria, cantidad: 1 })
      setShowForm(false)
      await loadItems()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al añadir artículo'
      setError(message)
    }
  }

  const handleToggleBought = async (id: number, marcarComprado: boolean) => {
    try {
      setError('')
      if (marcarComprado) {
        await articulosLista.marcarComprado(id)
      } else {
        await articulosLista.restaurar(id)
      }
      await loadItems()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al actualizar'
      setError(message)
    }
  }

  const handleDeleteItem = async (id: number) => {
    if (!confirm('¿Eliminar este artículo?')) return

    try {
      setError('')
      await articulosLista.eliminar(id)
      await loadItems()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al eliminar'
      setError(message)
    }
  }

  const iniciarEdicion = (item: ArticuloLista) => {
    setEditandoId(item.id)
    setEdicion({ nombre: item.nombre, cantidad: item.cantidad })
  }

  const guardarEdicion = async (id: number) => {
    if (!edicion.nombre.trim()) return
    try {
      setError('')
      await articulosLista.actualizar(id, { nombre: edicion.nombre.trim(), cantidad: edicion.cantidad })
      setEditandoId(null)
      await loadItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al editar el artículo')
    }
  }

  const items = [...pendientes, ...completados]

  // Filtrar por búsqueda
  const filteredPendingItems = pendientes.filter((item) =>
    item.nombre.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.categoria || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredBoughtItems = completados.filter((item) =>
    item.nombre.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.categoria || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">Lista de Compra</h1>
          <p className="text-muted-foreground mt-1">
            {pendientes.length} artículos pendientes
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2 min-h-[44px]"
        >
          <Plus className="w-5 h-5" />
          <span className="hidden sm:inline">Añadir Artículo</span>
          <span className="sm:hidden">Añadir</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <StatsCard
          title="Por Comprar"
          value={pendientes.length}
          icon={ShoppingCart}
          color="blue"
          description="Artículos pendientes"
        />
        <StatsCard
          title="Comprados"
          value={completados.length}
          icon={CheckCircle2}
          color="green"
          description="Artículos completados"
        />
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">Nuevo Artículo</h2>
          <form onSubmit={handleAddItem} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Artículo</label>
              <input
                type="text"
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder="ej: Leche, Pan, Detergente..."
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
                <label className="block text-sm font-medium mb-2">Cantidad</label>
                <input
                  type="number"
                  value={formData.cantidad}
                  onChange={(e) => setFormData({ ...formData, cantidad: parseInt(e.target.value) || 1 })}
                  min="1"
                  className="input-field"
                  inputMode="numeric"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">
                Guardar
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary flex-1"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Search Bar */}
      {items.length > 0 && !loading && (
        <div>
          <SearchBar
            placeholder="Buscar por nombre o categoría..."
            value={searchQuery}
            onChange={setSearchQuery}
          />
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

      {/* Loading */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Cargando lista de compra...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">La lista está vacía</p>
          <button
            onClick={() => setShowForm(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Crear Mi Primera Compra
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Pending Items */}
          {filteredPendingItems.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Pendientes ({filteredPendingItems.length})</h2>
              <div className="space-y-2">
                {filteredPendingItems.map((item) => (
                  <div
                    key={item.id}
                    className="card flex items-center justify-between gap-4"
                  >
                    <button
                      onClick={() => handleToggleBought(item.id, true)}
                      className="p-1 hover:bg-green-50 dark:hover:bg-green-950 rounded-lg transition-colors flex-shrink-0"
                      aria-label="Marcar como comprado"
                    >
                      <Circle className="w-6 h-6 text-muted-foreground" />
                    </button>

                    {editandoId === item.id ? (
                      <div className="flex-1 flex gap-2 items-center">
                        <input
                          type="text"
                          value={edicion.nombre}
                          onChange={(e) => setEdicion({ ...edicion, nombre: e.target.value })}
                          className="input-field !py-1 flex-1"
                          autoFocus
                        />
                        <input
                          type="number"
                          min={1}
                          value={edicion.cantidad}
                          onChange={(e) => setEdicion({ ...edicion, cantidad: parseInt(e.target.value) || 1 })}
                          className="input-field !py-1 w-16"
                        />
                        <button onClick={() => guardarEdicion(item.id)} aria-label="Guardar">
                          <Check className="w-5 h-5 text-green-500" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-foreground mb-1">
                          {item.nombre}
                          {item.cantidad > 1 && <span className="text-muted-foreground"> ×{item.cantidad}</span>}
                        </p>
                        {item.categoria && <CategoryBadge category={item.categoria} />}
                      </div>
                    )}

                    <button
                      onClick={() => iniciarEdicion(item)}
                      className="p-2 hover:bg-muted rounded-lg transition-colors flex-shrink-0"
                      aria-label="Editar"
                    >
                      <Pencil className="w-4 h-4 text-muted-foreground" />
                    </button>
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="p-2 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors flex-shrink-0"
                      aria-label="Eliminar"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bought Items */}
          {filteredBoughtItems.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-muted-foreground">Comprados ({filteredBoughtItems.length})</h2>
              <div className="space-y-2">
                {filteredBoughtItems.map((item) => (
                  <div
                    key={item.id}
                    className="card flex items-center justify-between gap-4 opacity-60"
                  >
                    <button
                      onClick={() => handleToggleBought(item.id, false)}
                      className="p-1 flex-shrink-0"
                      aria-label="Marcar como pendiente"
                    >
                      <CheckCircle2 className="w-6 h-6 text-green-500" />
                    </button>

                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground line-through mb-1">{item.nombre}</p>
                      {item.categoria && <CategoryBadge category={item.categoria} />}
                    </div>

                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="p-2 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors flex-shrink-0"
                      aria-label="Eliminar"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
