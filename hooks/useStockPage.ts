'use client'

import type { FormEvent } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { categorias as categoriasApi, listas as listasApi, productos as productosApi } from '@/lib/api'
import { getErrorMessage, parseNonNegativeInteger, parsePositiveInteger } from '@/lib/error-utils'
import type { Categoria, Lista, Producto, ProductoFormData } from '@/lib/types'

const EMPTY_FORM: ProductoFormData = {
  nombre: '',
  categoria: 'Otros',
  cantidad: 1,
  stock_minimo: 1,
  dias_aviso: 30,
  unidad: 'ud',
}

interface ListasDashboardResponse {
  propias?: Lista[]
  compartidas?: Lista[]
}

export type FiltroStock = 'todos' | 'bajo-stock' | 'caducidad'

export function useStockPage() {
  const [items, setItems] = useState<Producto[]>([])
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState<ProductoFormData>(EMPTY_FORM)
  const [gestionandoCategorias, setGestionandoCategorias] = useState(false)
  const [nuevaCategoria, setNuevaCategoria] = useState('')
  const [filtroActivo, setFiltroActivo] = useState<FiltroStock>('todos')

  useEffect(() => {
    void bootstrap()
  }, [])

  const bootstrap = async () => {
    try {
      setLoading(true)
      setError('')

      const listasData = await listasApi.listar() as ListasDashboardResponse
      if ((listasData.propias?.length || 0) === 0 && (listasData.compartidas?.length || 0) === 0) {
        await listasApi.crear('Mi lista')
      }

      const [productosData, categoriasData] = await Promise.all([
        productosApi.listar() as Promise<Producto[]>,
        categoriasApi.listar() as Promise<Categoria[]>,
      ])

      setItems(Array.isArray(productosData) ? productosData : [])
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const abrirNuevo = () => {
    setEditandoId(null)
    setFormData({ ...EMPTY_FORM, categoria: categorias[0]?.nombre || 'Otros' })
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

  const cerrarFormulario = () => {
    setShowForm(false)
    setEditandoId(null)
    setGestionandoCategorias(false)
  }

  const guardarProducto = async () => {
    try {
      setError('')
      if (editandoId) {
        await productosApi.actualizar(editandoId, formData)
      } else {
        await productosApi.crear(formData)
      }
      cerrarFormulario()
      await bootstrap()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al guardar el producto'))
    }
  }

  const eliminarProducto = async (id: number) => {
    try {
      setError('')
      await productosApi.eliminar(id)
      await bootstrap()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al eliminar producto'))
    }
  }

  const ajustarCantidad = async (id: number, delta: number) => {
    try {
      setError('')
      await productosApi.actualizar(id, { delta })
      await bootstrap()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al actualizar cantidad'))
    }
  }

  const crearCategoria = async () => {
    if (!nuevaCategoria.trim()) return

    try {
      setError('')
      await categoriasApi.crear(nuevaCategoria.trim())
      setNuevaCategoria('')
      const categoriasData = await categoriasApi.listar() as Categoria[]
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      setError(getErrorMessage(err, 'Error al crear la categoría'))
    }
  }

  const eliminarCategoria = async (id: number) => {
    try {
      setError('')
      await categoriasApi.eliminar(id)
      const categoriasData = await categoriasApi.listar() as Categoria[]
      setCategorias(Array.isArray(categoriasData) ? categoriasData : [])
    } catch (err) {
      setError(getErrorMessage(err, 'Error al eliminar la categoría (puede estar en uso)'))
    }
  }

  const isLowStock = (item: Producto) => item.cantidad <= item.stock_minimo

  const filteredItems = useMemo(() => items.filter((item) => {
    const query = searchQuery.toLowerCase()
    const matchesQuery = item.nombre.toLowerCase().includes(query) || item.categoria.toLowerCase().includes(query)

    if (!matchesQuery) return false
    if (filtroActivo === 'bajo-stock') return isLowStock(item)
    if (filtroActivo === 'caducidad') return item.revisar_caducidad
    return true
  }), [filtroActivo, items, searchQuery])

  const stats = useMemo(() => ({
    totalItems: items.length,
    totalQuantity: items.reduce((sum, item) => sum + item.cantidad, 0),
    bajoStock: items.filter((item) => isLowStock(item)).length,
    porRevisar: items.filter((item) => item.revisar_caducidad).length,
  }), [items])

  const filtros = useMemo(() => ([
    { key: 'todos' as const, label: 'Todos', count: items.length },
    { key: 'bajo-stock' as const, label: 'Bajo stock', count: stats.bajoStock },
    { key: 'caducidad' as const, label: 'Revisar caducidad', count: stats.porRevisar },
  ]), [items.length, stats.bajoStock, stats.porRevisar])

  const getEstadoCardClass = (item: Producto) => {
    if (isLowStock(item) && item.revisar_caducidad) {
      return 'border-red-200 ring-2 ring-amber-200 dark:border-red-900 dark:ring-amber-900/70'
    }
    if (isLowStock(item)) return 'border-red-200 dark:border-red-900'
    if (item.revisar_caducidad) return 'border-amber-200 dark:border-amber-900'
    return ''
  }

  const getCantidadClass = (item: Producto) => (isLowStock(item) ? 'text-stock-critical' : 'text-accent')

  return {
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
    submitForm: async (event: FormEvent) => {
      event.preventDefault()
      await guardarProducto()
    },
    submitCategoryForm: async (event: FormEvent) => {
      event.preventDefault()
      await crearCategoria()
    },
    updateCantidad: (value: string) => parseNonNegativeInteger(value),
    updateStockMinimo: (value: string) => parseNonNegativeInteger(value),
    updateDiasAviso: (value: string) => parsePositiveInteger(value),
  }
}
