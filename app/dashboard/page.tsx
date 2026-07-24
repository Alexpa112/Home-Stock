'use client'

import Link from 'next/link'
import { Clock3, Package, Pencil, Plus, ShoppingCart, Tags, Trash2, TrendingUp, TriangleAlert, X } from 'lucide-react'
import { CategoryBadge } from '@/components/dashboard/CategoryBadge'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useStockPage } from '@/hooks/useStockPage'

export default function StockPage() {
  const {
    categorias,
    cerrarFormulario,
    eliminarCategoria,
    eliminarProducto,
    error,
    filtroActivo,
    filtros,
    filteredItems,
    formData,
    getCantidadClass,
    getEstadoCardClass,
    gestionandoCategorias,
    isLowStock,
    items,
    loading,
    nuevaCategoria,
    abrirEdicion,
    abrirNuevo,
    ajustarCantidad,
    editandoId,
    searchQuery,
    setFiltroActivo,
    setFormData,
    setGestionandoCategorias,
    setNuevaCategoria,
    setSearchQuery,
    showForm,
    stats,
    setShowForm,
    submitCategoryForm,
    submitForm,
    updateCantidad,
    updateDiasAviso,
    updateStockMinimo,
  } = useStockPage()

  return (
    <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-6">
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

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatsCard title="Artículos" value={stats.totalItems} icon={Package} color="blue" description="Productos en stock" />
        <StatsCard title="Cantidad Total" value={stats.totalQuantity} icon={TrendingUp} color="green" description="Unidades disponibles" />
        <StatsCard title="Bajo Stock" value={stats.bajoStock} icon={ShoppingCart} color="red" description="Cantidad igual o inferior al mínimo" />
        <StatsCard title="Por Revisar" value={stats.porRevisar} icon={Clock3} color="yellow" description="Revisión por caducidad o tiempo" />
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
                    <button
                      type="button"
                      onClick={() => confirm('¿Eliminar esta categoría?') && eliminarCategoria(cat.id)}
                      aria-label={`Eliminar ${cat.nombre}`}
                    >
                      <X className="w-3 h-3 text-red-500" />
                    </button>
                  </span>
                ))}
              </div>
              <form onSubmit={submitCategoryForm} className="flex gap-2">
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

          <form onSubmit={submitForm} className="space-y-4">
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
                  onChange={(e) => setFormData({ ...formData, cantidad: updateCantidad(e.target.value) })}
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
                  onChange={(e) => setFormData({ ...formData, stock_minimo: updateStockMinimo(e.target.value) })}
                  min="0"
                  className="input-field"
                  inputMode="numeric"
                />
                <p className="mt-2 text-xs text-muted-foreground">Cuando la cantidad llegue a este valor o baje más, quedará marcado para reponer. Usa 0 si solo quieres avisar cuando se agote.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Aviso de revisión (días)</label>
                <input
                  type="number"
                  value={formData.dias_aviso}
                  onChange={(e) => setFormData({ ...formData, dias_aviso: updateDiasAviso(e.target.value) })}
                  min="1"
                  className="input-field"
                  inputMode="numeric"
                />
                <p className="mt-2 text-xs text-muted-foreground">Si pasan estos días sin actualizar el producto, se marcará para revisar caducidad.</p>
              </div>
              <div className="panel-info flex flex-col justify-center">
                <p className="font-semibold">¿Qué significa cada estado?</p>
                <p className="text-sm leading-6">
                  <strong>Bajo stock</strong> significa reponer. <strong>Revisar caducidad</strong> significa comprobar estado/fecha del producto.
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">
                {editandoId ? 'Guardar cambios' : 'Guardar'}
              </button>
              <button type="button" onClick={cerrarFormulario} className="btn-secondary flex-1">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {error && <StatusMessage title="Error" message={error} className="panel-danger" />}

      {items.length > 0 && !loading && (
        <div className="space-y-3">
          <SearchBar placeholder="Buscar por nombre o categoría..." value={searchQuery} onChange={setSearchQuery} />
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

      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Cargando inventario...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No hay productos en el inventario</p>
          <button onClick={abrirNuevo} className="btn-primary inline-flex items-center gap-2">
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
            <div key={item.id} className={`card flex flex-col justify-between ${getEstadoCardClass(item)}`}>
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
                      onClick={() => confirm('¿Eliminar este artículo?') && eliminarProducto(item.id)}
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
                      onClick={() => ajustarCantidad(item.id, -1)}
                      className="w-11 h-11 flex items-center justify-center rounded-xl border border-border hover:bg-muted"
                      aria-label="Restar"
                    >
                      -
                    </button>
                    <span className={`text-lg font-bold w-10 text-center ${getCantidadClass(item)}`}>{item.cantidad}</span>
                    <button
                      onClick={() => ajustarCantidad(item.id, 1)}
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
