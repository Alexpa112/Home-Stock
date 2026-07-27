'use client'

import { useState, useEffect } from 'react'
import { Plus, Trash2, CheckCircle2, Circle, AlertCircle, Pencil, Check, AlertTriangle, Grid3x3, List } from 'lucide-react'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { CategoryBadge } from '@/components/dashboard/CategoryBadge'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { articulosLista, categorias as categoriasApi } from '@/lib/api'
import { useListPreferences } from '@/contexts/ListPreferencesContext'
import { useTranslation } from '@/contexts/TranslationContext'

interface ArticuloLista {
  id: number
  lista_id: number
  nombre: string
  cantidad: number
  unidad: string
  categoria: string | null
  icono: string | null
  completado: boolean
  origen: 'auto' | 'manual'
}

interface Categoria {
  id: number
  nombre: string
  icono: string
}

export default function ShoppingPage() {
  const { preferences, updatePreferences } = useListPreferences()
  const { t } = useTranslation()
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
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)

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
      const message = err instanceof Error ? err.message : t('error_conexion_titulo')
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
      const message = err instanceof Error ? err.message : t('err_anadir_articulo')
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
      const message = err instanceof Error ? err.message : t('err_actualizar')
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
      await articulosLista.eliminar(id)
      await loadItems()
    } catch (err) {
      const message = err instanceof Error ? err.message : t('err_eliminar_articulo')
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
      setError(err instanceof Error ? err.message : t('err_editar_articulo'))
    }
  }

  const items = [...pendientes, ...completados]

  const filteredPendingItems = pendientes.filter((item) =>
    item.nombre.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.categoria || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredBoughtItems = completados.filter((item) =>
    item.nombre.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.categoria || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getCategoryIcon = (categoryName: string | null) => {
    if (!categoryName) return null
    const cat = categorias.find((c) => c.nombre === categoryName)
    return cat?.icono || null
  }

  const agruparPorCategoria = (itemsList: ArticuloLista[]) => {
    const grupos: Record<string, ArticuloLista[]> = {}
    itemsList.forEach((item) => {
      const cat = item.categoria || 'Otros'
      if (!grupos[cat]) grupos[cat] = []
      grupos[cat].push(item)
    })
    return Object.entries(grupos).sort(([a], [b]) => a.localeCompare(b))
  }

  const renderItemRow = (item: ArticuloLista, isCompleted: boolean = false) => (
    <div
      key={item.id}
      className={`card flex items-center justify-between gap-4 ${isCompleted ? 'opacity-60' : ''}`}
    >
      <button
        onClick={() => handleToggleBought(item.id, !isCompleted)}
        className={`w-11 h-11 flex items-center justify-center rounded-xl transition-colors flex-shrink-0 ${
          isCompleted
            ? 'hover:bg-muted'
            : 'hover:bg-green-50 dark:hover:bg-green-950'
        }`}
        aria-label={isCompleted ? t('aria_restaurar_producto').replace('{nombre}', item.nombre) : t('aria_marcar_comprado_producto').replace('{nombre}', item.nombre)}
      >
        {isCompleted ? (
          <CheckCircle2 className="w-6 h-6 text-green-500" />
        ) : (
          <Circle className="w-6 h-6 text-muted-foreground" />
        )}
      </button>

      {editandoId === item.id ? (
        <div className="flex-1 flex flex-col gap-2">
          <input
            type="text"
            value={edicion.nombre}
            onChange={(e) => setEdicion({ ...edicion, nombre: e.target.value })}
            className="input-field"
            autoFocus
            inputMode="text"
          />
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              value={edicion.cantidad}
              onChange={(e) => setEdicion({ ...edicion, cantidad: parseInt(e.target.value) || 1 })}
              className="input-field w-24"
              inputMode="numeric"
            />
            <button
              onClick={() => guardarEdicion(item.id)}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
              aria-label={t('guardar')}
            >
              <Check className="w-4 h-4" /> {t('guardar')}
            </button>
            <button
              onClick={() => setEditandoId(null)}
              className="btn-secondary px-3"
              aria-label={t('aria_cancelar_edicion')}
            >
              ✕
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <p className={`font-medium text-foreground ${isCompleted ? 'line-through' : ''}`}>
              {item.nombre}
              {item.cantidad > 1 && <span className="text-muted-foreground"> ×{item.cantidad}</span>}
            </p>
            {item.origen === 'auto' && !isCompleted && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300">
                <AlertTriangle className="w-3 h-3" />
                {t('stock_bajo')}
              </span>
            )}
          </div>
          {item.categoria && <CategoryBadge category={item.categoria} icon={getCategoryIcon(item.categoria)} />}
        </div>
      )}

      {editandoId !== item.id && (
        <button
          onClick={() => iniciarEdicion(item)}
          className="w-10 h-10 flex items-center justify-center hover:bg-muted rounded-xl transition-colors flex-shrink-0"
          aria-label={t('editar')}
        >
          <Pencil className="w-4 h-4 text-muted-foreground" />
        </button>
      )}

      {confirmandoId === item.id ? (
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => handleDeleteItem(item.id)}
            className="px-2 h-10 text-xs font-semibold text-white bg-red-500 rounded-xl"
          >
            {t('si')}
          </button>
          <button
            onClick={() => setConfirmandoId(null)}
            className="px-2 h-10 text-xs font-semibold text-foreground bg-muted rounded-xl"
          >
            {t('no')}
          </button>
        </div>
      ) : (
        <button
          onClick={() => handleDeleteItem(item.id)}
          className="w-10 h-10 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors flex-shrink-0"
          aria-label={t('eliminar')}
        >
          <Trash2 className="w-4 h-4 text-red-500" />
        </button>
      )}
    </div>
  )

  const renderVistaRecuadros = () => (
    <div className="space-y-6">
      {searchQuery && filteredPendingItems.length === 0 && filteredBoughtItems.length === 0 && (
        <div className="text-center py-8 space-y-2">
          <p className="text-muted-foreground">{t('sin_resultados_para')} <strong>«{searchQuery}»</strong></p>
          <button onClick={() => setSearchQuery('')} className="text-sm text-accent hover:underline">{t('limpiar_busqueda')}</button>
        </div>
      )}

      {filteredPendingItems.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">{t('pendientes_contador')} ({filteredPendingItems.length})</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredPendingItems.map((item) => (
              <div
                key={item.id}
                className="card p-4 flex flex-col justify-between"
              >
                <div className="flex-1">
                  <div className="flex items-start gap-2 mb-2">
                    <p className="font-medium text-foreground flex-1">
                      {item.nombre}
                      {item.cantidad > 1 && <span className="text-muted-foreground"> ×{item.cantidad}</span>}
                    </p>
                    {item.origen === 'auto' && (
                      <AlertTriangle className="w-4 h-4 text-orange-500 flex-shrink-0 mt-0.5" />
                    )}
                  </div>
                  {item.categoria && (
                    <CategoryBadge category={item.categoria} icon={getCategoryIcon(item.categoria)} />
                  )}
                </div>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => handleToggleBought(item.id, true)}
                    className="flex-1 btn-primary text-xs flex items-center justify-center gap-1"
                  >
                    <Check className="w-3 h-3" /> {t('comprado')}
                  </button>
                  <button
                    onClick={() => iniciarEdicion(item)}
                    className="w-10 h-10 flex items-center justify-center hover:bg-muted rounded-xl transition-colors"
                    aria-label={t('editar')}
                  >
                    <Pencil className="w-4 h-4 text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => handleDeleteItem(item.id)}
                    className="w-10 h-10 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors"
                    aria-label={t('eliminar')}
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {filteredBoughtItems.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-muted-foreground">{t('comprados_contador')} ({filteredBoughtItems.length})</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredBoughtItems.map((item) => (
              <div
                key={item.id}
                className="card p-4 opacity-60 flex flex-col justify-between"
              >
                <div className="flex-1">
                  <p className="font-medium text-foreground line-through mb-2">
                    {item.nombre}
                    {item.cantidad > 1 && <span className="text-muted-foreground"> ×{item.cantidad}</span>}
                  </p>
                  {item.categoria && (
                    <CategoryBadge category={item.categoria} icon={getCategoryIcon(item.categoria)} />
                  )}
                </div>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => handleToggleBought(item.id, false)}
                    className="flex-1 btn-secondary text-xs"
                  >
                    {t('restaurar')}
                  </button>
                  <button
                    onClick={() => handleDeleteItem(item.id)}
                    className="w-10 h-10 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors"
                    aria-label={t('eliminar')}
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">{t('lista_compra')}</h1>
          <p className="text-muted-foreground mt-1">
            {pendientes.length} {t('articulos_pendientes')}
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2 min-h-[44px]"
        >
          <Plus className="w-5 h-5" />
          <span className="hidden sm:inline">{t('añadir_articulo')}</span>
          <span className="sm:hidden">{t('añadir')}</span>
        </button>
      </div>

      {/* Vista Controls */}
      {items.length > 0 && !loading && (
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <button
              onClick={() => updatePreferences({ vista_lista_compra: 'lista' })}
              className={`w-11 h-11 flex items-center justify-center rounded-xl transition-colors ${
                preferences.vista_lista_compra === 'lista'
                  ? 'bg-accent text-white'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
              title={t('titulo_vista_lista')}
              aria-label={t('titulo_vista_lista')}
            >
              <List className="w-5 h-5" />
            </button>
            <button
              onClick={() => updatePreferences({ vista_lista_compra: 'recuadros' })}
              className={`w-11 h-11 flex items-center justify-center rounded-xl transition-colors ${
                preferences.vista_lista_compra === 'recuadros'
                  ? 'bg-accent text-white'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
              title={t('titulo_vista_recuadros')}
              aria-label={t('titulo_vista_recuadros')}
            >
              <Grid3x3 className="w-5 h-5" />
            </button>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.agrupar_categorias === 'on'}
              onChange={(e) => updatePreferences({ agrupar_categorias: e.target.checked ? 'on' : 'off' })}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm font-medium">{t('agrupar_por_categoria')}</span>
          </label>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">{t('nuevo_articulo')}</h2>
          <form onSubmit={handleAddItem} className="space-y-4">
            <div>
              <label htmlFor="art-nombre" className="block text-sm font-medium mb-2">{t('articulo')}</label>
              <input
                id="art-nombre"
                type="text"
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder={t('placeholder_ej_articulo')}
                className="input-field"
                required
                inputMode="text"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="art-categoria" className="block text-sm font-medium mb-2">{t('categoria')}</label>
                <select
                  id="art-categoria"
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
                <label htmlFor="art-cantidad" className="block text-sm font-medium mb-2">{t('cantidad')}</label>
                <input
                  id="art-cantidad"
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
                {t('guardar')}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary flex-1"
              >
                {t('cancelar')}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Search Bar */}
      {items.length > 0 && !loading && (
        <div>
          <SearchBar
            placeholder={t('placeholder_buscar_nombre_categoria')}
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
            <p className="font-medium">{t('error')}</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">{t('cargando_lista_compra')}</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">{t('lista_vacia')}</p>
          <button
            onClick={() => setShowForm(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            {t('crear_primera_compra')}
          </button>
        </div>
      ) : preferences.vista_lista_compra === 'recuadros' ? (
        renderVistaRecuadros()
      ) : (
        <div className="space-y-6">
          {/* Pending Items */}
          {filteredPendingItems.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">{t('pendientes_contador')} ({filteredPendingItems.length})</h2>
              {preferences.agrupar_categorias === 'on' ? (
                <div className="space-y-4">
                  {agruparPorCategoria(filteredPendingItems).map(([categoria, items]) => (
                    <div key={categoria} className="space-y-2">
                      <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        {getCategoryIcon(categoria) && <IconRenderer name={getCategoryIcon(categoria)} className="w-4 h-4" />}
                        {categoria}
                      </h3>
                      <div className="space-y-2 ml-2">
                        {items.map((item) => renderItemRow(item, false))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredPendingItems.map((item) => renderItemRow(item, false))}
                </div>
              )}
            </div>
          )}

          {/* Sin resultados de búsqueda */}
          {searchQuery && filteredPendingItems.length === 0 && filteredBoughtItems.length === 0 && (
            <div className="text-center py-8 space-y-2">
              <p className="text-muted-foreground">{t('sin_resultados_para')} <strong>«{searchQuery}»</strong></p>
              <button onClick={() => setSearchQuery('')} className="text-sm text-accent hover:underline">{t('limpiar_busqueda')}</button>
            </div>
          )}

          {/* Bought Items */}
          {filteredBoughtItems.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-muted-foreground">{t('comprados_contador')} ({filteredBoughtItems.length})</h2>
              {preferences.agrupar_categorias === 'on' ? (
                <div className="space-y-4">
                  {agruparPorCategoria(filteredBoughtItems).map(([categoria, items]) => (
                    <div key={categoria} className="space-y-2">
                      <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        {getCategoryIcon(categoria) && <IconRenderer name={getCategoryIcon(categoria)} className="w-4 h-4" />}
                        {categoria}
                      </h3>
                      <div className="space-y-2 ml-2">
                        {items.map((item) => renderItemRow(item, true))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredBoughtItems.map((item) => renderItemRow(item, true))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
