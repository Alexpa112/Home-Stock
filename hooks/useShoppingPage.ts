'use client'

import type { FormEvent } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { articulosLista, categorias as categoriasApi } from '@/lib/api'
import { getErrorMessage, parsePositiveInteger } from '@/lib/error-utils'
import type { ArticuloLista, ArticuloListaFormData, Categoria } from '@/lib/types'

interface ArticulosResponse {
  pendientes?: ArticuloLista[]
  completados?: ArticuloLista[]
}

export function useShoppingPage() {
  const [pendientes, setPendientes] = useState<ArticuloLista[]>([])
  const [completados, setCompletados] = useState<ArticuloLista[]>([])
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState<ArticuloListaFormData>({ nombre: '', categoria: 'Otros', cantidad: 1 })
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [edicion, setEdicion] = useState({ nombre: '', cantidad: 1 })

  useEffect(() => {
    void loadItems()
    void categoriasApi
      .listar()
      .then((data) => setCategorias(Array.isArray(data) ? (data as Categoria[]) : []))
      .catch((err) => setError(getErrorMessage(err, 'Error cargando categorías')))
  }, [])

  const loadItems = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await articulosLista.listar() as ArticulosResponse
      setPendientes(data?.pendientes || [])
      setCompletados(data?.completados || [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const addItem = async () => {
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
      setError(getErrorMessage(err, 'Error al añadir artículo'))
    }
  }

  const toggleBought = async (id: number, marcarComprado: boolean) => {
    try {
      setError('')
      if (marcarComprado) {
        await articulosLista.marcarComprado(id)
      } else {
        await articulosLista.restaurar(id)
      }
      await loadItems()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al actualizar'))
    }
  }

  const deleteItem = async (id: number) => {
    try {
      setError('')
      await articulosLista.eliminar(id)
      await loadItems()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al eliminar'))
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
      setError(getErrorMessage(err, 'Error al editar el artículo'))
    }
  }

  const items = useMemo(() => [...pendientes, ...completados], [completados, pendientes])
  const normalizedQuery = searchQuery.toLowerCase()

  const filteredPendingItems = useMemo(() => pendientes.filter((item) =>
    item.nombre.toLowerCase().includes(normalizedQuery) ||
    (item.categoria || '').toLowerCase().includes(normalizedQuery)
  ), [normalizedQuery, pendientes])

  const filteredBoughtItems = useMemo(() => completados.filter((item) =>
    item.nombre.toLowerCase().includes(normalizedQuery) ||
    (item.categoria || '').toLowerCase().includes(normalizedQuery)
  ), [completados, normalizedQuery])

  return {
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
    submitAddItem: async (event: FormEvent) => {
      event.preventDefault()
      await addItem()
    },
    toggleBought,
    updateCantidad: (value: string) => parsePositiveInteger(value),
  }
}
