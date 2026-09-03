'use client'

import { useState, useEffect, useRef } from 'react'
import { Plus, Trash2, AlertCircle, Package, TrendingUp, Pencil, X, Tags, ShoppingCart, Grid3x3, List, LineChart, Download, Upload } from 'lucide-react'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { MenuAcciones } from '@/components/dashboard/MenuAcciones'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { IconPicker } from '@/components/dashboard/IconPicker'
import { Modal } from '@/components/dashboard/Modal'
import { HistorialPreciosModal } from '@/components/dashboard/HistorialPreciosModal'
import { productos as productosApi, categorias as categoriasApi, articulosLista } from '@/lib/api'
import { buscarCatalogo } from '@/lib/catalogo'
import { useListPreferences } from '@/contexts/ListPreferencesContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { getCached, setCached, prefetch } from '@/lib/dataCache'
import { usePollingRefresh } from '@/lib/usePollingRefresh'
import { SkeletonCards } from '@/components/dashboard/SkeletonCards'

const CACHE_KEY_PRODUCTOS = 'stock:productos'
const CACHE_KEY_CATEGORIAS = 'stock:categorias'

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

interface ArticuloCatalogo {
  nombre: string
  icono: string | null
  categoria: string | null
  unidad: string | null
  origen: 'estandar' | 'personalizado'
}

interface FormularioProducto {
  nombre: string
  categoria: string
  cantidad: number | ''
  stock_minimo: number | ''
  unidad: string
  dias_aviso: number | ''
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

// Fusiona lo recibido del backend con lo pintado, conservando tal cual los
// items que el usuario tiene abiertos en edicion (preservarIds): si un
// refresco en segundo plano llegase entre que abre el modal y lo guarda,
// no debe pisarle lo que esta viendo/editando.
function fusionarProductos(previos: Producto[], recibidos: Producto[], preservarIds: Set<number>): Producto[] {
  if (preservarIds.size === 0) return recibidos
  const previosPorId = new Map(previos.map((p) => [p.id, p]))
  return recibidos.map((item) => (preservarIds.has(item.id) ? previosPorId.get(item.id) ?? item : item))
}

export default function StockPage() {
  const { preferences } = useListPreferences()
  const { t } = useTranslation()
  const [items, setItems] = useState<Producto[]>(() => getCached<Producto[]>(CACHE_KEY_PRODUCTOS) || [])
  const [categorias, setCategorias] = useState<Categoria[]>(() => getCached<Categoria[]>(CACHE_KEY_CATEGORIAS) || [])
  const [loading, setLoading] = useState(() => getCached<Producto[]>(CACHE_KEY_PRODUCTOS) === undefined)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState<FormularioProducto>(FORM_VACIO)
  const [gestionandoCategorias, setGestionandoCategorias] = useState(false)
  const [nuevaCategoria, setNuevaCategoria] = useState('')
  const [nuevaCategoriaIcono, setNuevaCategoriaIcono] = useState<string | undefined>(undefined)
  const [mostrarIconPickerCategoria, setMostrarIconPickerCategoria] = useState(false)
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)
  const [filtro, setFiltro] = useState<'todos' | 'bajo_minimo' | 'por_revisar'>('todos')
  const [añadiendoIds, setAñadiendoIds] = useState<Set<number>>(new Set())
  const [añadidoIds, setAñadidoIds] = useState<Set<number>>(new Set())
  const [confirmandoEliminarCatId, setConfirmandoEliminarCatId] = useState<number | null>(null)
  const [modoVista, setModoVista] = useState<'lista' | 'grid'>('grid')
  const [formIcono, setFormIcono] = useState<string | undefined>(undefined)
  const [catalogo, setCatalogo] = useState<ArticuloCatalogo[]>([])
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false)
  const [mostrarIconPicker, setMostrarIconPicker] = useState(false)
  const [mostrarHistorialPreciosId, setMostrarHistorialPreciosId] = useState<number | null>(null)
  const inputImportarRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Cargar preferencias guardadas
    const modoGuardado = localStorage.getItem('stock-modo-vista') as 'lista' | 'grid' | null
    if (modoGuardado) setModoVista(modoGuardado)

    bootstrap()
  }, [])

  // Refresco periodico silencioso: otros operarios pueden modificar el stock
  // desde otro dispositivo. Antes de recargar, comprueba una version barata
  // del hogar (ver usePollingRefresh) y se salta el ciclo si hay un modal de
  // edicion/alta abierto, para no pisar lo que el usuario esta escribiendo.
  usePollingRefresh(
    () => bootstrap(),
    () => showForm || gestionandoCategorias
  )

  // La caché es lo que se pinta al montar la pantalla, así que cualquier
  // cambio local (ajuste de cantidad, borrado, alta, edición) tiene que
  // quedar reflejado o al volver aquí se vería un instante el dato antiguo.
  useEffect(() => {
    if (!loading) setCached(CACHE_KEY_PRODUCTOS, items)
  }, [items, loading])

  // Guardar preferencias cuando cambien
  useEffect(() => {
    localStorage.setItem('stock-modo-vista', modoVista)
  }, [modoVista])

  // Busca en el catálogo (backend) cada vez que el usuario escribe el nombre,
  // en lugar de cargar una vez los 30 primeros por orden alfabético y filtrar
  // solo esos en cliente (por lo que "leche", "pan", "huevos"... nunca salían).
  useEffect(() => {
    if (!showForm) return
    const q = formData.nombre.trim()
    const timer = setTimeout(() => {
      buscarCatalogo(q || undefined).then((data: any) => {
        setCatalogo(Array.isArray(data) ? data : [])
      }).catch(() => {})
    }, 250)
    return () => clearTimeout(timer)
  }, [showForm, formData.nombre])

  const bootstrap = async () => {
    try {
      setError('')

      // La seleccion de hogar/lista activa ahora es obligatoria antes de
      // llegar aqui (ver components/shared/SelectorHogarPantallaCompleta.tsx),
      // asi que ya no hace falta crear una lista de emergencia en este punto. Ambas
      // peticiones van en paralelo desde el primer instante, sin esperas
      // en cascada.
      const [productosData, categoriasData] = await Promise.all([
        productosApi.listar(),
        categoriasApi.listar(),
      ])

      const productosArr = Array.isArray(productosData) ? productosData : []
      const categoriasArr = Array.isArray(categoriasData) ? categoriasData : []
      const preservarIds = editandoId !== null ? new Set([editandoId]) : new Set<number>()
      setItems((prev) => fusionarProductos(prev, productosArr, preservarIds))
      setCategorias(categoriasArr)
      setCached(CACHE_KEY_CATEGORIAS, categoriasArr)

      // Precargar la lista de la compra en segundo plano para que, si el
      // usuario navega ahi despues, ya este disponible al instante.
      prefetch('shopping:articulos', () => articulosLista.listar())
    } catch (err) {
      const message = err instanceof Error ? err.message : t('error_conexion_titulo')
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const abrirNuevo = () => {
    setEditandoId(null)
    setFormData({ ...FORM_VACIO, categoria: categorias[0]?.nombre || 'Otros' })
    setFormIcono(undefined)
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
    setFormIcono(item.icono || undefined)
    setShowForm(true)
  }

  const seleccionarSugerencia = (item: ArticuloCatalogo) => {
    setFormData({
      ...formData,
      nombre: item.nombre,
      categoria: item.categoria || formData.categoria,
      unidad: item.unidad || formData.unidad,
    })
    setFormIcono(item.icono || undefined)
    setMostrarSugerencias(false)
  }

  const sugerenciasNombre = formData.nombre.trim() ? catalogo.slice(0, 6) : []

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
      const diasAvisoFinal = formData.dias_aviso === '' ? 7 : Number(formData.dias_aviso)

      if (editandoId) {
        const actualizado: any = await productosApi.actualizar(editandoId, {
          nombre: formData.nombre,
          categoria: formData.categoria,
          cantidad: cantidadFinal,
          stock_minimo: stockMinimoFinal,
          unidad: formData.unidad,
          dias_aviso: diasAvisoFinal,
          icono: formIcono,
        })
        setItems(prev => prev.map(item => item.id === editandoId ? { ...item, ...actualizado } : item))
      } else {
        const creado: any = await productosApi.crear({
          nombre: formData.nombre,
          categoria: formData.categoria,
          cantidad: cantidadFinal,
          stock_minimo: stockMinimoFinal,
          unidad: formData.unidad,
          dias_aviso: diasAvisoFinal,
          icono: formIcono,
        })
        setItems(prev => [...prev, creado])
      }
      setShowForm(false)
      setEditandoId(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : t('err_guardar_cambios')
      setError(message)
    }
  }

  const handleDeleteItem = async (id: number) => {
    if (confirmandoId !== id) {
      setConfirmandoId(id)
      return
    }
    setConfirmandoId(null)

    // Quitar el producto al instante y revertir si el backend falla: antes se
    // esperaba al DELETE y encima se recargaba todo con bootstrap(), o sea dos
    // viajes de red en serie antes de que la fila desapareciera de la pantalla.
    const itemsPrevios = items
    setItems(prev => prev.filter((item) => item.id !== id))
    setError('')

    try {
      await productosApi.eliminar(id)
    } catch (err) {
      setItems(itemsPrevios)
      const message = err instanceof Error ? err.message : t('err_eliminar_producto')
      setError(message)
    }
  }

  const handleAjustarCantidad = async (id: number, delta: number) => {
    const itemIndex = items.findIndex(i => i.id === id)
    if (itemIndex === -1) return

    const itemAnterior = items[itemIndex]
    const cantidadNueva = Math.max(0, itemAnterior.cantidad + delta)

    const aplicarCantidad = (cantidad: number) =>
      setItems(prev => prev.map((item) => (item.id === id ? { ...item, cantidad } : item)))

    aplicarCantidad(cantidadNueva)
    setError('')

    try {
      await productosApi.actualizar(id, { delta })
    } catch (err) {
      aplicarCantidad(itemAnterior.cantidad)
      const message = err instanceof Error ? err.message : t('err_actualizar_cantidad')
      setError(message)
    }
  }

  const handleCrearCategoria = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nuevaCategoria.trim()) return
    try {
      setError('')
      await categoriasApi.crear(nuevaCategoria.trim(), nuevaCategoriaIcono)
      setNuevaCategoria('')
      setNuevaCategoriaIcono(undefined)
      const categoriasData: any = await categoriasApi.listar()
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_crear_categoria'))
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
      setError(err instanceof Error ? err.message : t('err_eliminar_categoria_uso'))
    }
  }

  const handleAñadirACompra = async (item: Producto) => {
    setAñadiendoIds(prev => new Set(prev).add(item.id))
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
      setAñadiendoIds(prev => {
        const siguiente = new Set(prev)
        siguiente.delete(item.id)
        return siguiente
      })
    }
  }

  // Un solo toque en "añadir todos" hacía una petición por producto y
  // esperaba a cada una antes de lanzar la siguiente (N viajes de red en
  // serie). Van en paralelo, así que tarda lo que la más lenta.
  const handleAñadirTodosACompra = async () => {
    const bajos = items.filter(i => i.cantidad <= i.stock_minimo && !añadidoIds.has(i.id))
    await Promise.all(bajos.map(handleAñadirACompra))
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

  // Vista "Grid": recuadro compacto al estilo Bring! — icono, nombre y la
  // cantidad solo si es distinta de 1 (si es 1, sobra: es el caso normal).
  // Tocar el recuadro abre la edición completa (incluye eliminar);
  // el ajuste +/- rápido y "añadir a la compra" quedan como acciones
  // secundarias discretas, sin competir visualmente con icono+nombre+cantidad.
  // Vista "Grid" — ficha compacta: icono y nombre en fila (no apilados, sin
  // insignias solapando el icono), stepper +/- siempre visible en su propia
  // fila. El aviso de stock bajo es un borde izquierdo de color en vez de un
  // punto sobre el icono, para no competir visualmente con él.
  const renderProductoGrid = (item: Producto) => {
    const icono = getCategoryIcon(item.categoria)
    const bajoMinimo = item.cantidad <= item.stock_minimo
    return (
      <div
        key={item.id}
        className={`card !p-2.5 flex flex-col gap-2 relative ${bajoMinimo ? 'border-l-4 !border-l-red-500' : ''}`}
      >
        <button
          onClick={() => abrirEdicion(item)}
          className="absolute inset-0 rounded-2xl"
          aria-label={`${t('editar')} ${item.nombre}`}
        />

        <div className="flex items-center gap-2 pointer-events-none">
          <div className="relative shrink-0">
            <div className="w-9 h-9 rounded-xl bg-muted flex items-center justify-center">
              {icono ? (
                <IconRenderer name={icono} className="w-[1.15rem] h-[1.15rem] text-muted-foreground" />
              ) : (
                <Package className="w-[1.15rem] h-[1.15rem] text-muted-foreground" />
              )}
            </div>
            {item.revisar_caducidad && (
              <span
                className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-yellow-500 border-2 border-card"
                title={t('revisar_caducidad')}
              />
            )}
          </div>
          <p className="font-medium text-foreground text-xs leading-tight line-clamp-2 min-w-0">{item.nombre}</p>
        </div>

        {/* Stepper: por encima del botón de edición a pantalla completa */}
        <div className="relative flex items-center gap-1">
          <button
            onClick={() => handleAjustarCantidad(item.id, -1)}
            className="w-7 h-7 flex items-center justify-center rounded-lg border border-border bg-card hover:bg-muted active:scale-95 transition-all text-sm font-medium"
            aria-label={t('aria_restar_uno')}
            disabled={item.cantidad <= 0}
          >
            −
          </button>
          <span className={`flex-1 text-center text-sm font-bold tabular-nums ${bajoMinimo ? 'text-red-500' : 'text-foreground'}`}>
            {item.cantidad}
          </span>
          <button
            onClick={() => handleAjustarCantidad(item.id, 1)}
            className="w-7 h-7 flex items-center justify-center rounded-lg border border-border bg-card hover:bg-muted active:scale-95 transition-all text-sm font-medium"
            aria-label={t('aria_sumar_uno')}
          >
            +
          </button>
          {confirmandoId === item.id ? (
            <>
              <button
                onClick={() => handleDeleteItem(item.id)}
                className="px-1.5 h-7 flex items-center text-xs font-semibold text-white bg-red-500 rounded-lg transition-colors"
                aria-label={t('aria_confirmar_eliminacion')}
              >
                {t('si')}
              </button>
              <button
                onClick={() => setConfirmandoId(null)}
                className="px-1.5 h-7 flex items-center text-xs font-semibold text-foreground bg-muted rounded-lg transition-colors"
                aria-label={t('cancelar')}
              >
                {t('no')}
              </button>
            </>
          ) : (
            <button
              onClick={() => handleDeleteItem(item.id)}
              className="w-7 h-7 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors"
              aria-label={t('eliminar')}
            >
              <Trash2 className="w-3.5 h-3.5 text-red-500" />
            </button>
          )}
        </div>

        {bajoMinimo && (
          <button
            onClick={() => handleAñadirACompra(item)}
            disabled={añadiendoIds.has(item.id)}
            className={`relative w-full flex items-center justify-center gap-1 py-1 rounded-lg text-[0.65rem] font-semibold transition-all active:scale-95 ${
              añadidoIds.has(item.id)
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                : 'bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-950/40 dark:hover:bg-red-950/70 dark:text-red-300'
            }`}
          >
            {añadidoIds.has(item.id) ? (
              <>✓ {t('añadido_a_la_compra')}</>
            ) : añadiendoIds.has(item.id) ? (
              <>{t('añadiendo')}</>
            ) : (
              <><ShoppingCart className="w-3 h-3" /> {t('añadir_a_la_compra')}</>
            )}
          </button>
        )}
      </div>
    )
  }

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
            {bajoMinimo && <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" title={t('bajo_minimo')} />}
            {item.revisar_caducidad && <span className="w-2 h-2 rounded-full bg-yellow-500 shrink-0" title={t('revisar_caducidad')} />}
          </div>
          <p className="text-xs text-muted-foreground truncate">{item.categoria} · {item.unidad}</p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => handleAjustarCantidad(item.id, -1)}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-border bg-card hover:bg-muted active:scale-95 transition-all text-base font-medium"
            aria-label={t('aria_restar_uno')}
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
            aria-label={t('aria_sumar_uno')}
          >
            +
          </button>
        </div>

        {bajoMinimo && (
          <button
            onClick={() => handleAñadirACompra(item)}
            disabled={añadiendoIds.has(item.id)}
            className={`w-9 h-9 flex items-center justify-center rounded-lg shrink-0 transition-all active:scale-95 ${
              añadidoIds.has(item.id)
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                : 'bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-950/40 dark:hover:bg-red-950/70 dark:text-red-300'
            }`}
            aria-label={t('añadir_a_la_compra')}
            title={t('añadir_a_la_compra')}
          >
            <ShoppingCart className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={() => abrirEdicion(item)}
          className="w-9 h-9 flex items-center justify-center hover:bg-muted rounded-lg transition-colors shrink-0"
          aria-label={t('editar')}
        >
          <Pencil className="w-4 h-4 text-muted-foreground" />
        </button>

        {confirmandoId === item.id ? (
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => handleDeleteItem(item.id)}
              className="px-2 h-9 flex items-center text-xs font-semibold text-white bg-red-500 rounded-lg transition-colors"
              aria-label={t('aria_confirmar_eliminacion')}
            >
              {t('si')}
            </button>
            <button
              onClick={() => setConfirmandoId(null)}
              className="px-2 h-9 flex items-center text-xs font-semibold text-foreground bg-muted rounded-lg transition-colors"
              aria-label={t('cancelar')}
            >
              {t('no')}
            </button>
          </div>
        ) : (
          <button
            onClick={() => handleDeleteItem(item.id)}
            className="w-9 h-9 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors shrink-0"
            aria-label={t('eliminar')}
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </button>
        )}
      </div>
    )
  }

  const renderProducto = (item: Producto) => (modoVista === 'lista' ? renderProductoLista(item) : renderProductoGrid(item))

  const handleExportarCsv = async () => {
    try {
      setError('')
      await productosApi.exportarCsv()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_conexion_titulo'))
    }
  }

  const handleImportarCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fichero = e.target.files?.[0]
    e.target.value = ''
    if (!fichero) return
    try {
      setError('')
      await productosApi.importarCsv(fichero)
      bootstrap()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_importar_csv'))
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">{t('mi_stock')}</h1>
          <p className="text-muted-foreground mt-1">{t('subtitulo_stock')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => (showForm ? setShowForm(false) : abrirNuevo())}
            className="btn-primary flex items-center gap-2 min-h-[44px]"
          >
            <Plus className="w-5 h-5" />
            <span className="hidden sm:inline">{t('añadir_producto')}</span>
            <span className="sm:hidden">{t('añadir')}</span>
          </button>
          <MenuAcciones
            label={t('mas_acciones')}
            acciones={[
              { icono: <Download className="w-4 h-4" />, etiqueta: t('exportar_csv'), onClick: handleExportarCsv },
              { icono: <Upload className="w-4 h-4" />, etiqueta: t('importar_csv'), onClick: () => inputImportarRef.current?.click() },
            ]}
          />
          <input ref={inputImportarRef} type="file" accept=".csv" className="hidden" onChange={handleImportarCsv} />
        </div>
      </div>

      {/* Filtros compactos — opciones de filtrado rápido */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setFiltro('todos')}
          aria-label={t('aria_ver_todos_articulos')}
          aria-pressed={filtro === 'todos'}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            filtro === 'todos'
              ? 'bg-accent text-accent-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          📦 {stats.totalItems} {t('articulos')}
        </button>
        <button
          onClick={() => setFiltro(filtro === 'bajo_minimo' ? 'todos' : 'bajo_minimo')}
          aria-label={filtro === 'bajo_minimo' ? t('aria_quitar_filtro_bajo_stock') : t('aria_filtrar_bajo_stock')}
          aria-pressed={filtro === 'bajo_minimo'}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            filtro === 'bajo_minimo'
              ? 'bg-red-500 text-white'
              : stats.bajoMinimo > 0
              ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-950/60'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          🛒 {stats.bajoMinimo} {t('bajo_stock')}
        </button>
        <button
          onClick={() => setFiltro(filtro === 'por_revisar' ? 'todos' : 'por_revisar')}
          aria-label={filtro === 'por_revisar' ? t('aria_quitar_filtro_caducidad') : t('aria_filtrar_revisar_caducidad')}
          aria-pressed={filtro === 'por_revisar'}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            filtro === 'por_revisar'
              ? 'bg-yellow-500 text-white'
              : stats.porRevisar > 0
              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-950/60'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          ⏱️ {stats.porRevisar} {t('caducados')}
        </button>
      </div>

      {/* Acción masiva cuando filtramos por bajo mínimo */}
      {filtro === 'bajo_minimo' && stats.bajoMinimo > 0 && (
        <div className="flex items-center justify-between gap-3 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-xl">
          <p className="text-sm text-red-700 dark:text-red-300 font-medium">
            {stats.bajoMinimo} {stats.bajoMinimo === 1 ? t('producto_bajo_stock_minimo_uno') : t('producto_bajo_stock_minimo_varios')}
          </p>
          <button
            onClick={handleAñadirTodosACompra}
            className="shrink-0 flex items-center gap-2 px-3 py-2 bg-red-500 hover:bg-red-600 text-white text-sm font-semibold rounded-xl transition-colors active:scale-95"
          >
            <ShoppingCart className="w-4 h-4" />
            {t('añadir_todos')}
          </button>
        </div>
      )}

      {/* Add / Edit Form */}
      {showForm && (
        <Modal onCerrar={() => { setShowForm(false); setEditandoId(null) }}>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{editandoId ? t('editar_producto') : t('nuevo_producto')}</h2>
            <div className="flex items-center gap-3">
              {editandoId && (
                <button
                  type="button"
                  onClick={() => setMostrarHistorialPreciosId(editandoId)}
                  className="text-sm text-accent hover:underline flex items-center gap-1"
                  title={t('ver_historial_precios')}
                >
                  <LineChart className="w-4 h-4" />
                </button>
              )}
              <button
                type="button"
                onClick={() => setGestionandoCategorias(!gestionandoCategorias)}
                className="text-sm text-accent hover:underline flex items-center gap-1"
              >
                <Tags className="w-4 h-4" /> {t('categorias')}
              </button>
            </div>
          </div>

          {gestionandoCategorias && (
            <div className="p-3 bg-muted rounded-lg space-y-2">
              <div className="flex flex-wrap gap-2">
                {categorias.map((cat) => (
                  confirmandoEliminarCatId === cat.id ? (
                    <span key={cat.id} className="flex items-center gap-1 px-2 py-1 bg-card rounded-full text-xs border border-red-300 dark:border-red-700">
                      <span className="text-red-600 dark:text-red-400 mr-0.5">{t('eliminar_pregunta')}</span>
                      <button type="button" onClick={() => handleEliminarCategoria(cat.id)} className="px-1.5 py-0.5 text-white bg-red-500 rounded-md font-medium">{t('si')}</button>
                      <button type="button" onClick={() => setConfirmandoEliminarCatId(null)} className="px-1.5 py-0.5 bg-muted rounded-md font-medium">{t('no')}</button>
                    </span>
                  ) : (
                    <span key={cat.id} className="flex items-center gap-1 px-2 py-1 bg-card rounded-full text-xs border border-border">
                      {cat.nombre}
                      <button type="button" onClick={() => handleEliminarCategoria(cat.id)} aria-label={`${t('eliminar')} ${cat.nombre}`}>
                        <X className="w-3 h-3 text-red-500" />
                      </button>
                    </span>
                  )
                ))}
              </div>
              <form onSubmit={handleCrearCategoria} className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setMostrarIconPickerCategoria(true)}
                  className="w-9 h-9 shrink-0 rounded-lg bg-card border border-border flex items-center justify-center"
                  aria-label={t('cambiar_icono')}
                >
                  {nuevaCategoriaIcono ? (
                    <IconRenderer name={nuevaCategoriaIcono} className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <Tags className="w-4 h-4 text-muted-foreground" />
                  )}
                </button>
                <input
                  type="text"
                  value={nuevaCategoria}
                  onChange={(e) => setNuevaCategoria(e.target.value)}
                  placeholder={t('nueva_categoria')}
                  className="input-field !py-1.5 flex-1"
                />
                <button type="submit" className="btn-secondary !py-1.5">{t('añadir')}</button>
              </form>
            </div>
          )}

          <form onSubmit={handleGuardar} className="space-y-4">
            <div className="relative">
              <label htmlFor="prod-nombre" className="block text-sm font-medium mb-2">{t('nombre')}</label>
              <input
                id="prod-nombre"
                type="text"
                value={formData.nombre}
                onChange={(e) => {
                  setFormData({ ...formData, nombre: e.target.value })
                  setFormIcono(undefined)
                  setMostrarSugerencias(true)
                }}
                onFocus={() => setMostrarSugerencias(true)}
                onBlur={() => setTimeout(() => setMostrarSugerencias(false), 150)}
                placeholder={t('placeholder_ej_producto')}
                className="input-field"
                required
                inputMode="text"
                autoComplete="off"
              />
              {mostrarSugerencias && sugerenciasNombre.length > 0 && (
                <ul className="absolute z-10 left-0 right-0 mt-1 bg-card border border-border rounded-xl shadow-lg overflow-hidden">
                  {sugerenciasNombre.map((item) => (
                    <li key={`${item.origen}-${item.nombre}`}>
                      <button
                        type="button"
                        onMouseDown={() => seleccionarSugerencia(item)}
                        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-muted transition-colors"
                      >
                        {item.icono && <IconRenderer name={item.icono} className="w-4 h-4 text-muted-foreground" />}
                        <span className="text-sm">{item.nombre}</span>
                        {item.categoria && <span className="text-xs text-muted-foreground ml-auto">{item.categoria}</span>}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-muted flex items-center justify-center shrink-0">
                {(formIcono || getCategoryIcon(formData.categoria)) ? (
                  <IconRenderer name={formIcono || getCategoryIcon(formData.categoria)} className="w-5 h-5 text-muted-foreground" />
                ) : (
                  <Package className="w-5 h-5 text-muted-foreground" />
                )}
              </div>
              <button
                type="button"
                onClick={() => setMostrarIconPicker(true)}
                className="btn-secondary btn-sm"
              >
                {t('cambiar_icono')}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="prod-categoria" className="block text-sm font-medium mb-2">{t('categoria')}</label>
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
                <label htmlFor="prod-unidad" className="block text-sm font-medium mb-2">{t('unidad')}</label>
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
                <label htmlFor="prod-cantidad" className="block text-sm font-medium mb-1.5">{t('cantidad')}</label>
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
                <label htmlFor="prod-minimo" className="block text-sm font-medium mb-1.5">{t('stock_minimo')}</label>
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
                  {t('dias_sin_actualizar_para_avisar')}
                </label>
                <input
                  id="prod-dias"
                  type="number"
                  value={formData.dias_aviso}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      dias_aviso: parseNumeroInput(e.target.value, 7),
                    })
                  }
                  min="1"
                  max="365"
                  className="input-field"
                  inputMode="numeric"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">
                {editandoId ? t('guardar_cambios') : t('guardar')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false)
                  setEditandoId(null)
                }}
                className="btn-secondary flex-1"
              >
                {t('cancelar')}
              </button>
            </div>
          </form>
        </div>
        </Modal>
      )}

      {mostrarHistorialPreciosId !== null && (
        <HistorialPreciosModal
          productoId={mostrarHistorialPreciosId}
          nombreProducto={formData.nombre}
          onCerrar={() => setMostrarHistorialPreciosId(null)}
        />
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

      {/* Search Bar */}
      {items.length > 0 && !loading && (
        <div className="space-y-3">
          <SearchBar
            placeholder={t('placeholder_buscar_nombre_categoria')}
            value={searchQuery}
            onChange={setSearchQuery}
          />
        </div>
      )}

      {/* Vista selector y opciones */}
      {items.length > 0 && !loading && (
        <div className="flex items-center justify-between gap-2">
          <div className="flex gap-2">
            <button
              onClick={() => setModoVista('lista')}
              className={`px-3 py-2 rounded-lg font-medium text-sm transition-colors ${modoVista === 'lista' ? 'bg-accent text-accent-foreground' : 'bg-muted text-muted-foreground hover:bg-muted-darker'}`}
              title={t('titulo_vista_lista')}
            >
              📋 {t('vista_lista')}
            </button>
            <button
              onClick={() => setModoVista('grid')}
              className={`px-3 py-2 rounded-lg font-medium text-sm transition-colors ${modoVista === 'grid' ? 'bg-accent text-accent-foreground' : 'bg-muted text-muted-foreground hover:bg-muted-darker'}`}
              title={t('titulo_vista_grid')}
            >
              ⊞ {t('grid')}
            </button>
          </div>
        </div>
      )}

      {/* Stock List */}
      {loading ? (
        <SkeletonCards />
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">{t('no_hay_productos_inventario')}</p>
          <button
            onClick={abrirNuevo}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            {t('añadir_primer_producto')}
          </button>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-12 space-y-2">
          {searchQuery ? (
            <>
              <p className="text-muted-foreground">{t('sin_resultados_para')} <strong>«{searchQuery}»</strong></p>
              <button onClick={() => setSearchQuery('')} className="text-sm text-accent hover:underline">{t('limpiar_busqueda')}</button>
            </>
          ) : filtro === 'bajo_minimo' ? (
            <p className="text-muted-foreground">{t('todo_en_orden_sin_bajo_minimo')}</p>
          ) : filtro === 'por_revisar' ? (
            <p className="text-muted-foreground">{t('no_hay_productos_pendientes_revision')}</p>
          ) : (
            <p className="text-muted-foreground">{t('no_se_encontraron_productos')}</p>
          )}
        </div>
      ) : preferences.agrupar_categorias === 'on' ? (
        // Vista agrupada por categoría
        <div className="space-y-6">
          {categorias.map((cat) => {
            const productosCat = filteredItems.filter(item => item.categoria === cat.nombre)
            if (productosCat.length === 0) return null
            return (
              <div key={cat.id}>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <IconRenderer name={cat.icono} className="w-6 h-6" />
                  {cat.nombre}
                  <span className="text-xs text-muted-foreground ml-auto">{productosCat.length} {productosCat.length !== 1 ? t('producto_plural') : t('producto_singular')}</span>
                </h2>
                <div className={modoVista === 'lista' ? 'space-y-2 lista-larga' : 'grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3 lista-larga-grid'}>
                  {productosCat.map(renderProducto)}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        // Vista sin agrupar
        <div className={modoVista === 'lista' ? 'space-y-2 lista-larga' : 'grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3 lista-larga-grid'}>
          {filteredItems.map(renderProducto)}
        </div>
      )}

      {mostrarIconPicker && (
        <IconPicker
          valorActual={formIcono || getCategoryIcon(formData.categoria)}
          onSeleccionar={(icono) => {
            setFormIcono(icono)
            setMostrarIconPicker(false)
          }}
          onCerrar={() => setMostrarIconPicker(false)}
        />
      )}

      {mostrarIconPickerCategoria && (
        <IconPicker
          valorActual={nuevaCategoriaIcono}
          onSeleccionar={(icono) => {
            setNuevaCategoriaIcono(icono)
            setMostrarIconPickerCategoria(false)
          }}
          onCerrar={() => setMostrarIconPickerCategoria(false)}
        />
      )}
    </div>
  )
}

