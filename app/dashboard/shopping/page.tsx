'use client'

import { useState, useEffect, useRef } from 'react'
import { Plus, Trash2, CheckCircle2, Circle, AlertCircle, Pencil, Check, AlertTriangle, Grid3x3, List, X, ScanBarcode, Download, Upload } from 'lucide-react'
import { SearchBar } from '@/components/dashboard/SearchBar'
import { CategoryBadge, getCategoryTileGradient } from '@/components/dashboard/CategoryBadge'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { Modal } from '@/components/dashboard/Modal'
import { MenuAcciones } from '@/components/dashboard/MenuAcciones'
import { BarcodeScanner } from '@/components/shared/BarcodeScanner'
import { articulosLista, categorias as categoriasApi, productos as productosApi } from '@/lib/api'
import { buscarCatalogo, buscarPorCodigoBarras } from '@/lib/catalogo'
import { useListPreferences } from '@/contexts/ListPreferencesContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { getCached, setCached, prefetch } from '@/lib/dataCache'
import { usePollingRefresh } from '@/lib/usePollingRefresh'
import { SkeletonCards } from '@/components/dashboard/SkeletonCards'

const CACHE_KEY_ARTICULOS = 'shopping:articulos'
const CACHE_KEY_CATEGORIAS = 'stock:categorias'

// Espejo de LIMITE_COMPLETADOS en stockhogar/rutas/articulos_lista.py: al
// actualizar la lista en local (sin volver a pedirla al backend) hay que
// recortar los completados igual que lo hace el servidor.
const LIMITE_COMPLETADOS = 12

// Fusiona lo recibido del backend con lo pintado, conservando tal cual el
// item que el usuario tiene abierto en el modal de edicion completa: si un
// refresco en segundo plano llegase mientras edita, no debe pisarle lo que
// esta viendo/escribiendo.
function fusionarConservando(previos: ArticuloLista[], recibidos: ArticuloLista[], preservarId: number | null): ArticuloLista[] {
  if (preservarId === null) return recibidos
  const previo = previos.find((i) => i.id === preservarId)
  if (!previo) return recibidos
  return recibidos.map((item) => (item.id === preservarId ? previo : item))
}

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
  dias_aviso: number
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

export default function ShoppingPage() {
  const { preferences, updatePreferences } = useListPreferences()
  const { t } = useTranslation()
  const cachedArticulos = getCached<{ pendientes: ArticuloLista[]; completados: ArticuloLista[] }>(CACHE_KEY_ARTICULOS)
  const [pendientes, setPendientes] = useState<ArticuloLista[]>(cachedArticulos?.pendientes || [])
  const [completados, setCompletados] = useState<ArticuloLista[]>(cachedArticulos?.completados || [])
  const [categorias, setCategorias] = useState<Categoria[]>(() => getCached<Categoria[]>(CACHE_KEY_CATEGORIAS) || [])
  const [loading, setLoading] = useState(cachedArticulos === undefined)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState<{ nombre: string; categoria: string; cantidad: number | null }>({
    nombre: '',
    categoria: 'Otros',
    cantidad: 1,
  })
  const [formIcono, setFormIcono] = useState<string | undefined>(undefined)
  const [formUnidad, setFormUnidad] = useState<string | undefined>(undefined)
  const [formCodigoBarras, setFormCodigoBarras] = useState<string | undefined>(undefined)
  const [mostrarEscaner, setMostrarEscaner] = useState(false)
  const [errorEscaner, setErrorEscaner] = useState('')
  const inputImportarRef = useRef<HTMLInputElement>(null)
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)
  const [modalEdicionId, setModalEdicionId] = useState<number | null>(null)
  const [quickAddLoading, setQuickAddLoading] = useState(false)
  const [edicionCompleta, setEdicionCompleta] = useState<{ nombre: string; cantidad: number | null; unidad: string; categoria: string; dias_aviso: number | null }>({ nombre: '', cantidad: 1, unidad: 'ud', categoria: 'Otros', dias_aviso: 30 })
  const [catalogo, setCatalogo] = useState<ArticuloCatalogo[]>([])
  const [catalogoQuery, setCatalogoQuery] = useState('')
  const [sugerencias, setSugerencias] = useState<ArticuloCatalogo[]>([])
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false)

  useEffect(() => {
    loadItems()
    categoriasApi.listar().then((data: any) => {
      const categoriasArr = Array.isArray(data) ? data : []
      setCategorias(categoriasArr)
      setCached(CACHE_KEY_CATEGORIAS, categoriasArr)
    }).catch(() => {})

    // Precargar el stock en segundo plano para que, si el usuario navega
    // ahi despues, ya este disponible al instante.
    prefetch('stock:productos', () => productosApi.listar())
  }, [])

  // Refresco periodico silencioso: la lista de la compra es la pantalla mas
  // colaborativa (varios operarios tachando/anadiendo a la vez), pero antes
  // no se refrescaba nunca tras la carga inicial. Se salta el ciclo si hay
  // un formulario de alta o un modal de edicion abiertos.
  usePollingRefresh(
    () => loadItems(),
    () => showForm || modalEdicionId !== null
  )

  // Grid de "tocar para añadir": busca en el catálogo (backend) según lo que
  // se escriba en su propia barra de búsqueda, en vez de cargar una vez los
  // 30 primeros por orden alfabético y filtrar solo esos en cliente.
  useEffect(() => {
    if (!showForm) return
    const q = catalogoQuery.trim()
    const timer = setTimeout(() => {
      buscarCatalogo(q || undefined).then((data: any) => {
        setCatalogo(Array.isArray(data) ? data : [])
      }).catch(() => {})
    }, 250)
    return () => clearTimeout(timer)
  }, [showForm, catalogoQuery])

  // Sugerencias del campo de nombre: misma idea pero sobre lo que se escribe
  // ahí, no sobre catalogoQuery (son dos búsquedas independientes).
  useEffect(() => {
    if (!showForm) return
    const q = formData.nombre.trim()
    if (!q) {
      setSugerencias([])
      return
    }
    const timer = setTimeout(() => {
      buscarCatalogo(q).then((data: any) => {
        setSugerencias(Array.isArray(data) ? data : [])
      }).catch(() => {})
    }, 250)
    return () => clearTimeout(timer)
  }, [showForm, formData.nombre])

  const loadItems = async () => {
    try {
      setError('')
      const data: any = await articulosLista.listar()
      const pendientesArr = fusionarConservando(pendientes, data?.pendientes || [], modalEdicionId)
      const completadosArr = fusionarConservando(completados, data?.completados || [], modalEdicionId)
      setPendientes(pendientesArr)
      setCompletados(completadosArr)
      setCached(CACHE_KEY_ARTICULOS, { pendientes: pendientesArr, completados: completadosArr })
    } catch (err) {
      const message = err instanceof Error ? err.message : t('error_conexion_titulo')
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleExportarCsv = async () => {
    try {
      setError('')
      await articulosLista.exportarCsv()
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
      await articulosLista.importarCsv(fichero)
      loadItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_importar_csv'))
    }
  }

  type EstadoLista = { pendientes: ArticuloLista[]; completados: ArticuloLista[] }

  // Pinta un estado nuevo de la lista al instante y lo deja en caché. Todas
  // las acciones de un toque (marcar comprado, borrar, editar) lo usan para
  // actualizar la UI sin esperar al backend: antes cada toque encadenaba la
  // petición de la mutación + una recarga completa de la lista, así que no se
  // veía nada hasta pasados dos viajes de red (>1s en Raspberry Pi/móvil).
  const aplicarEstado = (siguiente: EstadoLista) => {
    setPendientes(siguiente.pendientes)
    setCompletados(siguiente.completados)
    setCached(CACHE_KEY_ARTICULOS, siguiente)
  }

  // Mismo orden que la consulta del backend (categoria, nombre COLLATE NOCASE)
  // para que un artículo restaurado aparezca donde le corresponde.
  const ordenarPendientes = (a: ArticuloLista, b: ArticuloLista) => {
    const catA = a.categoria || ''
    const catB = b.categoria || ''
    if (catA !== catB) return catA < catB ? -1 : 1
    return a.nombre.localeCompare(b.nombre, undefined, { sensitivity: 'base' })
  }

  // Inserta/actualiza el artículo devuelto por el backend al añadir: el POST
  // puede crear uno nuevo, sumar cantidad a uno pendiente o reactivar uno
  // completado, así que hay que cubrir los tres casos sin recargar la lista.
  const fusionarArticulo = (articulo: ArticuloLista) => {
    const restoPendientes = pendientes.filter((i) => i.id !== articulo.id)
    aplicarEstado({
      pendientes: [...restoPendientes, articulo].sort(ordenarPendientes),
      completados: completados.filter((i) => i.id !== articulo.id),
    })
  }

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault()
    const categoriaPrevia = formData.categoria
    try {
      setError('')
      const creado: any = await articulosLista.anadir(formData.nombre, {
        categoria: formData.categoria,
        cantidad: formData.cantidad ?? undefined,
        icono: formIcono,
        unidad: formUnidad,
        codigo_barras: formCodigoBarras,
      })
      setFormData({ nombre: '', categoria: categoriaPrevia, cantidad: 1 })
      setFormIcono(undefined)
      setFormUnidad(undefined)
      setFormCodigoBarras(undefined)
      setShowForm(false)
      setCatalogoQuery('')
      if (creado?.id) fusionarArticulo(creado)
    } catch (err) {
      const message = err instanceof Error ? err.message : t('err_anadir_articulo')
      setError(message)
    }
  }

  // Código escaneado (P-03): si el catálogo ya lo tiene asociado, se
  // rellena el formulario; si no, se deja el nombre en blanco para que el
  // usuario lo escriba y así se aprenda para la próxima vez (ver
  // recordar_articulo en stockhogar/rutas/historial.py).
  const handleCodigoDetectado = async (codigo: string) => {
    setMostrarEscaner(false)
    setFormCodigoBarras(codigo)
    try {
      const encontrado: any = await buscarPorCodigoBarras(codigo)
      setFormData((prev) => ({ ...prev, nombre: encontrado.nombre, categoria: encontrado.categoria || prev.categoria }))
      setFormIcono(encontrado.icono || undefined)
      setFormUnidad(encontrado.unidad || undefined)
      setErrorEscaner('')
    } catch {
      setErrorEscaner(t('codigo_no_reconocido'))
    }
  }

  // Añade directamente un artículo del catálogo (grid de "tocar para añadir").
  const handleQuickAdd = async (item: ArticuloCatalogo) => {
    if (quickAddLoading) return
    try {
      setQuickAddLoading(true)
      setError('')
      const creado: any = await articulosLista.anadir(item.nombre, {
        categoria: item.categoria || undefined,
        icono: item.icono || undefined,
        unidad: item.unidad || undefined,
      })
      if (creado?.id) fusionarArticulo(creado)
    } catch (err) {
      const message = err instanceof Error ? err.message : t('err_anadir_articulo')
      setError(message)
    } finally {
      setQuickAddLoading(false)
    }
  }

  const seleccionarSugerencia = (item: ArticuloCatalogo) => {
    setFormData({ ...formData, nombre: item.nombre, categoria: item.categoria || formData.categoria })
    setFormIcono(item.icono || undefined)
    setFormUnidad(item.unidad || undefined)
    setMostrarSugerencias(false)
  }

  const sugerenciasNombre = sugerencias.slice(0, 6)

  const catalogoFiltrado = catalogo

  const handleToggleBought = async (id: number, marcarComprado: boolean) => {
    const item = (marcarComprado ? pendientes : completados).find((i) => i.id === id)
    if (!item) return

    const previo: EstadoLista = { pendientes, completados }
    const movido = { ...item, completado: marcarComprado }
    aplicarEstado(
      marcarComprado
        ? {
            pendientes: pendientes.filter((i) => i.id !== id),
            completados: [movido, ...completados].slice(0, LIMITE_COMPLETADOS),
          }
        : {
            pendientes: [...pendientes, movido].sort(ordenarPendientes),
            completados: completados.filter((i) => i.id !== id),
          }
    )
    setError('')

    try {
      if (marcarComprado) {
        await articulosLista.marcarComprado(id)
      } else {
        await articulosLista.restaurar(id)
      }
    } catch (err) {
      aplicarEstado(previo)
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

    const previo: EstadoLista = { pendientes, completados }
    aplicarEstado({
      pendientes: pendientes.filter((i) => i.id !== id),
      completados: completados.filter((i) => i.id !== id),
    })
    setError('')

    try {
      await articulosLista.eliminar(id)
    } catch (err) {
      aplicarEstado(previo)
      const message = err instanceof Error ? err.message : t('err_eliminar_articulo')
      setError(message)
    }
  }

  const abrirModalEdicion = (item: ArticuloLista) => {
    setModalEdicionId(item.id)
    setEdicionCompleta({
      nombre: item.nombre,
      cantidad: item.cantidad,
      unidad: item.unidad,
      categoria: item.categoria || 'Otros',
      dias_aviso: item.dias_aviso ?? 30,
    })
  }

  const guardarEdicionCompleta = async () => {
    if (modalEdicionId === null || !edicionCompleta.nombre.trim()) return

    const id = modalEdicionId
    const cambios = {
      nombre: edicionCompleta.nombre.trim(),
      cantidad: edicionCompleta.cantidad ?? 1,
      unidad: edicionCompleta.unidad,
      categoria: edicionCompleta.categoria,
      dias_aviso: edicionCompleta.dias_aviso ?? 30,
    }
    const previo: EstadoLista = { pendientes, completados }
    const parchear = (lista: ArticuloLista[]) =>
      lista.map((i) => (i.id === id ? { ...i, ...cambios } : i))

    setModalEdicionId(null)
    aplicarEstado({
      pendientes: parchear(pendientes).sort(ordenarPendientes),
      completados: parchear(completados),
    })
    setError('')

    try {
      await articulosLista.actualizar(id, cambios)
    } catch (err) {
      aplicarEstado(previo)
      setError(err instanceof Error ? err.message : t('err_editar_articulo'))
    }
  }

  // Gesto de mantener pulsado: dispara abrirModalEdicion tras ~550ms y evita
  // que el click posterior (mouseup/touchend) dispare la accion normal del
  // elemento (marcar comprado, etc.). onClickCapture corta la propagacion
  // hacia los botones hijos si el long-press ya se disparo.
  //
  // El estado del gesto vive en refs, no en variables de la closure: antes se
  // creaba una closure nueva en cada render, asi que si se re-renderizaba
  // entre el mousedown y el mouseup (ahora ocurre en cada toque, porque la UI
  // se actualiza al instante) el `cancelar` del nuevo render no veia el timer
  // del anterior y la modal de edicion se abria sola tras 550ms.
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const longPressDisparado = useRef(false)

  const crearLongPress = (item: ArticuloLista) => {
    const iniciar = () => {
      longPressDisparado.current = false
      if (longPressTimer.current) clearTimeout(longPressTimer.current)
      longPressTimer.current = setTimeout(() => {
        longPressTimer.current = null
        longPressDisparado.current = true
        abrirModalEdicion(item)
      }, 550)
    }
    const cancelar = () => {
      if (longPressTimer.current) clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
    return {
      onTouchStart: iniciar,
      onTouchEnd: cancelar,
      onTouchMove: cancelar,
      onMouseDown: iniciar,
      onMouseUp: cancelar,
      onMouseLeave: cancelar,
      onContextMenu: (e: React.MouseEvent) => e.preventDefault(),
      onClickCapture: (e: React.MouseEvent) => {
        if (longPressDisparado.current) {
          longPressDisparado.current = false
          e.stopPropagation()
          e.preventDefault()
        }
      },
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
      {...crearLongPress(item)}
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

      <button
        onClick={() => abrirModalEdicion(item)}
        className="w-10 h-10 flex items-center justify-center hover:bg-muted rounded-xl transition-colors flex-shrink-0"
        aria-label={t('editar')}
      >
        <Pencil className="w-4 h-4 text-muted-foreground" />
      </button>

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

  // Tile "color por categoría": el icono ocupa un bloque de color propio de
  // la categoría (mismo criterio que CategoryBadge, así que un vistazo a
  // colores agrupa igual que un vistazo a iconos), con nombre y cantidad en
  // una franja inferior con scrim. Tocar el tile marca comprado/restaurado;
  // mantener pulsado abre la modal de edición completa.
  const renderItemGridTile = (item: ArticuloLista, isCompleted: boolean = false) => {
    const icono = getCategoryIcon(item.categoria)
    const gradiente = getCategoryTileGradient(item.categoria || 'Otros')
    return (
      <div
        key={item.id}
        className={`relative rounded-2xl overflow-hidden border border-border aspect-[10/11] flex flex-col justify-end transition-all ${isCompleted ? 'grayscale opacity-60' : ''}`}
        {...crearLongPress(item)}
      >
        <button
          onClick={() => handleToggleBought(item.id, !isCompleted)}
          className="absolute inset-0"
          aria-label={isCompleted ? t('aria_restaurar_producto').replace('{nombre}', item.nombre) : t('aria_marcar_comprado_producto').replace('{nombre}', item.nombre)}
        />

        <div className={`absolute inset-0 bg-gradient-to-br ${gradiente} flex items-center justify-center pointer-events-none`}>
          {icono ? (
            <IconRenderer name={icono} className="w-8 h-8 text-white/90" />
          ) : isCompleted ? (
            <CheckCircle2 className="w-8 h-8 text-white/90" />
          ) : (
            <Circle className="w-8 h-8 text-white/90" />
          )}
        </div>

        {item.origen === 'auto' && !isCompleted && (
          <span className="absolute top-2 right-2 w-2.5 h-2.5 rounded-full bg-red-500 border-2 border-white/85 pointer-events-none" title={t('stock_bajo')} />
        )}

        <div className="relative bg-black/45 backdrop-blur-[1px] px-2 py-1.5 pointer-events-none">
          <p className={`text-white text-xs font-semibold leading-tight line-clamp-2 ${isCompleted ? 'line-through' : ''}`}>
            {item.nombre}
          </p>
          <p className="text-white/80 text-[0.65rem] mt-0.5 tabular-nums">
            ×{item.cantidad}
          </p>
        </div>
      </div>
    )
  }

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
          {preferences.agrupar_categorias === 'on' ? (
            <div className="space-y-4">
              {agruparPorCategoria(filteredPendingItems).map(([categoria, items]) => (
                <div key={categoria} className="space-y-2">
                  <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    {getCategoryIcon(categoria) && <IconRenderer name={getCategoryIcon(categoria)} className="w-4 h-4" />}
                    {categoria}
                  </h3>
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3 lista-larga-grid">
                    {items.map((item) => renderItemGridTile(item, false))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3 lista-larga-grid">
              {filteredPendingItems.map((item) => renderItemGridTile(item, false))}
            </div>
          )}
        </div>
      )}

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
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3 lista-larga-grid">
                    {items.map((item) => renderItemGridTile(item, true))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3 lista-larga-grid">
              {filteredBoughtItems.map((item) => renderItemGridTile(item, true))}
            </div>
          )}
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
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowForm(!showForm)}
            className="btn-primary flex items-center gap-2 min-h-[44px]"
          >
            <Plus className="w-5 h-5" />
            <span className="hidden sm:inline">{t('añadir_articulo')}</span>
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

      {/* Vista Controls */}
      {items.length > 0 && !loading && (
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <button
              onClick={() => updatePreferences({ vista_lista_compra: 'lista' })}
              className={`w-11 h-11 flex items-center justify-center rounded-xl transition-colors ${
                preferences.vista_lista_compra === 'lista'
                  ? 'bg-accent text-accent-foreground'
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
                  ? 'bg-accent text-accent-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
              title={t('titulo_vista_recuadros')}
              aria-label={t('titulo_vista_recuadros')}
            >
              <Grid3x3 className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <Modal onCerrar={() => { setShowForm(false); setCatalogoQuery('') }}>
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">{t('nuevo_articulo')}</h2>
          {catalogo.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">{t('elegir_del_catalogo')}</p>
              <SearchBar
                placeholder={t('buscar_en_catalogo')}
                value={catalogoQuery}
                onChange={setCatalogoQuery}
              />
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 max-h-64 overflow-y-auto">
                {catalogoFiltrado.map((item) => (
                  <button
                    key={`${item.origen}-${item.nombre}`}
                    type="button"
                    onClick={() => handleQuickAdd(item)}
                    disabled={quickAddLoading}
                    className="card !p-2 flex flex-col items-center text-center gap-1 hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center">
                      {item.icono ? (
                        <IconRenderer name={item.icono} className="w-5 h-5 text-muted-foreground" />
                      ) : (
                        <Plus className="w-5 h-5 text-muted-foreground" />
                      )}
                    </div>
                    <p className="text-xs font-medium leading-tight line-clamp-2">{item.nombre}</p>
                  </button>
                ))}
              </div>
              {catalogoFiltrado.length === 0 && (
                <p className="text-sm text-muted-foreground">{t('sin_coincidencias_catalogo')}</p>
              )}
            </div>
          )}

          <form onSubmit={handleAddItem} className="space-y-4">
            <div className="relative">
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="art-nombre" className="block text-sm font-medium">{t('articulo')}</label>
                <button
                  type="button"
                  onClick={() => { setErrorEscaner(''); setMostrarEscaner(true) }}
                  className="flex items-center gap-1 text-xs font-medium text-primary"
                >
                  <ScanBarcode className="w-4 h-4" />
                  {t('escanear_codigo_barras')}
                </button>
              </div>
              {errorEscaner && <p className="text-xs text-destructive mb-2">{errorEscaner}</p>}
              <input
                id="art-nombre"
                type="text"
                value={formData.nombre}
                onChange={(e) => {
                  setFormData({ ...formData, nombre: e.target.value })
                  setFormIcono(undefined)
                  setFormUnidad(undefined)
                  setFormCodigoBarras(undefined)
                  setMostrarSugerencias(true)
                }}
                onFocus={() => setMostrarSugerencias(true)}
                onBlur={() => setTimeout(() => setMostrarSugerencias(false), 150)}
                placeholder={t('placeholder_ej_articulo')}
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
                  value={formData.cantidad || ''}
                  onChange={(e) => setFormData({ ...formData, cantidad: e.target.value === '' ? null : parseInt(e.target.value) })}
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
                onClick={() => {
                  setShowForm(false)
                  setCatalogoQuery('')
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

      {mostrarEscaner && (
        <BarcodeScanner onDetectado={handleCodigoDetectado} onCerrar={() => setMostrarEscaner(false)} />
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
        <SkeletonCards />
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
                      <div className="space-y-2 ml-2 lista-larga">
                        {items.map((item) => renderItemRow(item, false))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2 lista-larga">
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
                      <div className="space-y-2 ml-2 lista-larga">
                        {items.map((item) => renderItemRow(item, true))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2 lista-larga">
                  {filteredBoughtItems.map((item) => renderItemRow(item, true))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Modal de edicion completa: se abre con mantener pulsado (grid y lista) */}
      {modalEdicionId !== null && (
        <Modal onCerrar={() => setModalEdicionId(null)}>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">{t('editar_articulo')}</h2>
              <button onClick={() => setModalEdicionId(null)} className="p-1 hover:bg-muted rounded" aria-label={t('aria_cancelar_edicion')}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                guardarEdicionCompleta()
              }}
              className="space-y-4"
            >
              <div>
                <label htmlFor="edit-nombre" className="block text-sm font-medium mb-2">{t('articulo')}</label>
                <input
                  id="edit-nombre"
                  type="text"
                  value={edicionCompleta.nombre}
                  onChange={(e) => setEdicionCompleta({ ...edicionCompleta, nombre: e.target.value })}
                  className="input-field"
                  autoFocus
                  required
                  inputMode="text"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="edit-categoria" className="block text-sm font-medium mb-2">{t('categoria')}</label>
                  <select
                    id="edit-categoria"
                    value={edicionCompleta.categoria}
                    onChange={(e) => setEdicionCompleta({ ...edicionCompleta, categoria: e.target.value })}
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
                  <label htmlFor="edit-unidad" className="block text-sm font-medium mb-2">{t('unidad')}</label>
                  <input
                    id="edit-unidad"
                    type="text"
                    value={edicionCompleta.unidad}
                    onChange={(e) => setEdicionCompleta({ ...edicionCompleta, unidad: e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="edit-cantidad" className="block text-sm font-medium mb-2">{t('cantidad')}</label>
                  <input
                    id="edit-cantidad"
                    type="number"
                    value={edicionCompleta.cantidad || ''}
                    onChange={(e) => setEdicionCompleta({ ...edicionCompleta, cantidad: e.target.value === '' ? null : parseInt(e.target.value) })}
                    className="input-field"
                    inputMode="numeric"
                  />
                </div>

                <div>
                  <label htmlFor="edit-dias-aviso" className="block text-sm font-medium mb-2">
                    {t('dias_sin_actualizar_para_avisar')}
                  </label>
                  <input
                    id="edit-dias-aviso"
                    type="number"
                    min={1}
                    max={365}
                    value={edicionCompleta.dias_aviso || ''}
                    onChange={(e) => setEdicionCompleta({ ...edicionCompleta, dias_aviso: e.target.value === '' ? null : parseInt(e.target.value) })}
                    className="input-field"
                    inputMode="numeric"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button type="submit" className="btn-primary flex-1 flex items-center justify-center gap-2">
                  <Check className="w-4 h-4" /> {t('guardar')}
                </button>
                <button type="button" onClick={() => setModalEdicionId(null)} className="btn-secondary flex-1">
                  {t('cancelar')}
                </button>
              </div>
            </form>
          </div>
        </Modal>
      )}
    </div>
  )
}
