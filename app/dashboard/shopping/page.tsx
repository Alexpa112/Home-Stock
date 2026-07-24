'use client'

import { AlertCircle, Check, CheckCircle2, Circle, Pencil, Plus, ShoppingCart, Trash2 } from 'lucide-react'
import { CategoryBadge } from '@/components/dashboard/CategoryBadge'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useShoppingPage } from '@/hooks/useShoppingPage'

export default function ShoppingPage() {
  const {
    categorias,
    completados,
    deleteItem,
    edicion,
    editandoId,
    error,
    filteredBoughtItems,
    filteredPendingItems,
    formData,
    guardarEdicion,
    iniciarEdicion,
    items,
    loading,
    pendientes,
    searchQuery,
    setEdicion,
    setFormData,
    setSearchQuery,
    setShowForm,
    showForm,
    submitAddItem,
    toggleBought,
    updateCantidad,
  } = useShoppingPage()

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">Lista de Compra</h1>
          <p className="text-muted-foreground mt-1">{pendientes.length} artículos pendientes</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2 min-h-[44px]">
          <Plus className="w-5 h-5" />
          <span className="hidden sm:inline">Añadir Artículo</span>
          <span className="sm:hidden">Añadir</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <StatsCard title="Por Comprar" value={pendientes.length} icon={ShoppingCart} color="blue" description="Artículos pendientes" />
        <StatsCard title="Comprados" value={completados.length} icon={CheckCircle2} color="green" description="Artículos completados" />
      </div>

      {showForm && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">Nuevo Artículo</h2>
          <form onSubmit={submitAddItem} className="space-y-4">
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
                  onChange={(e) => setFormData({ ...formData, cantidad: updateCantidad(e.target.value) })}
                  min="1"
                  className="input-field"
                  inputMode="numeric"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">Guardar</button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary flex-1">Cancelar</button>
            </div>
          </form>
        </div>
      )}

      {items.length > 0 && !loading && (
        <div>
          <SearchBar placeholder="Buscar por nombre o categoría..." value={searchQuery} onChange={setSearchQuery} />
        </div>
      )}

      {error && <StatusMessage title="Error" message={error} />}

      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Cargando lista de compra...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">La lista está vacía</p>
          <button onClick={() => setShowForm(true)} className="btn-primary inline-flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Crear Mi Primera Compra
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredPendingItems.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Pendientes ({filteredPendingItems.length})</h2>
              <div className="space-y-2">
                {filteredPendingItems.map((item) => (
                  <div key={item.id} className="card flex items-center justify-between gap-4">
                    <button
                      onClick={() => toggleBought(item.id, true)}
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
                          onChange={(e) => setEdicion({ ...edicion, cantidad: updateCantidad(e.target.value) })}
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
                      onClick={() => confirm('¿Eliminar este artículo?') && deleteItem(item.id)}
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

          {filteredBoughtItems.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-muted-foreground">Comprados ({filteredBoughtItems.length})</h2>
              <div className="space-y-2">
                {filteredBoughtItems.map((item) => (
                  <div key={item.id} className="card flex items-center justify-between gap-4 opacity-60">
                    <button onClick={() => toggleBought(item.id, false)} className="p-1 flex-shrink-0" aria-label="Marcar como pendiente">
                      <CheckCircle2 className="w-6 h-6 text-green-500" />
                    </button>

                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground line-through mb-1">{item.nombre}</p>
                      {item.categoria && <CategoryBadge category={item.categoria} />}
                    </div>

                    <button
                      onClick={() => confirm('¿Eliminar este artículo?') && deleteItem(item.id)}
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
