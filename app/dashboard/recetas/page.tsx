'use client'

import { useEffect, useState } from 'react'
import { Plus, ChefHat, X, AlertCircle, ShoppingCart, Pencil, Trash2 } from 'lucide-react'
import { Modal } from '@/components/dashboard/Modal'
import { recetas as recetasApi } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'
import { getCached, setCached } from '@/lib/dataCache'

const CACHE_KEY_RECETAS = 'recetas:lista'

interface Ingrediente {
  id?: number
  nombre: string
  cantidad: number
  unidad: string
}

interface Receta {
  id: number
  nombre: string
  icono: string | null
  ingredientes: Ingrediente[]
}

const INGREDIENTE_VACIO = (): Ingrediente => ({ nombre: '', cantidad: 1, unidad: 'ud' })

export default function RecetasPage() {
  const { t } = useTranslation()
  const [recetas, setRecetas] = useState<Receta[]>(() => getCached<Receta[]>(CACHE_KEY_RECETAS) || [])
  const [loading, setLoading] = useState(recetas.length === 0)
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [nombre, setNombre] = useState('')
  const [ingredientes, setIngredientes] = useState<Ingrediente[]>([INGREDIENTE_VACIO()])
  const [confirmandoEliminarId, setConfirmandoEliminarId] = useState<number | null>(null)

  const cargar = () => {
    recetasApi.listar().then((data: any) => {
      const arr = Array.isArray(data) ? data : []
      setRecetas(arr)
      setCached(CACHE_KEY_RECETAS, arr)
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => {
    cargar()
  }, [])

  const abrirNuevo = () => {
    setEditandoId(null)
    setNombre('')
    setIngredientes([INGREDIENTE_VACIO()])
    setShowForm(true)
  }

  const abrirEditar = (receta: Receta) => {
    setEditandoId(receta.id)
    setNombre(receta.nombre)
    setIngredientes(receta.ingredientes.length > 0 ? receta.ingredientes.map((i) => ({ ...i })) : [INGREDIENTE_VACIO()])
    setShowForm(true)
  }

  const handleGuardar = async (e: React.FormEvent) => {
    e.preventDefault()
    const ingredientesValidos = ingredientes.filter((i) => i.nombre.trim())
    if (!nombre.trim() || ingredientesValidos.length === 0) return

    const datos = {
      nombre: nombre.trim(),
      ingredientes: ingredientesValidos.map((i) => ({ nombre: i.nombre.trim(), cantidad: i.cantidad || 1, unidad: i.unidad || 'ud' })),
    }
    try {
      setError('')
      if (editandoId !== null) {
        await recetasApi.actualizar(editandoId, datos)
      } else {
        await recetasApi.crear(datos)
      }
      setShowForm(false)
      cargar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_guardar_receta'))
    }
  }

  const handleEliminar = async (id: number) => {
    if (confirmandoEliminarId !== id) {
      setConfirmandoEliminarId(id)
      return
    }
    setConfirmandoEliminarId(null)
    try {
      setError('')
      await recetasApi.eliminar(id)
      cargar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_receta'))
    }
  }

  const handleAnadirALista = async (id: number) => {
    try {
      setError('')
      setMensaje('')
      await recetasApi.anadirALista(id)
      setMensaje(t('ingredientes_anadidos_a_la_lista'))
      setTimeout(() => setMensaje(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_anadir_articulo'))
    }
  }

  const actualizarIngrediente = (idx: number, campo: keyof Ingrediente, valor: string | number) => {
    setIngredientes((prev) => prev.map((ing, i) => (i === idx ? { ...ing, [campo]: valor } : ing)))
  }

  return (
    <div className="max-w-lg mx-auto p-4 lg:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <ChefHat className="w-5 h-5" /> {t('nav_recetas')}
        </h1>
        <button onClick={abrirNuevo} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> {t('nueva_receta')}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}
      {mensaje && (
        <div className="p-3 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-200 rounded-lg text-sm">
          {mensaje}
        </div>
      )}

      {loading ? null : recetas.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-6">{t('sin_recetas_aun')}</p>
      ) : (
        <div className="space-y-3">
          {recetas.map((receta) => (
            <div key={receta.id} className="card space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">{receta.nombre}</h2>
                <div className="flex items-center gap-1">
                  <button onClick={() => abrirEditar(receta)} aria-label={t('editar_receta')} className="p-1.5 hover:bg-muted rounded-lg">
                    <Pencil className="w-4 h-4 text-muted-foreground" />
                  </button>
                  {confirmandoEliminarId === receta.id ? (
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleEliminar(receta.id)} className="px-2 py-1 text-xs text-white bg-red-500 rounded-md font-medium">{t('si')}</button>
                      <button onClick={() => setConfirmandoEliminarId(null)} className="px-2 py-1 text-xs bg-muted rounded-md font-medium">{t('no')}</button>
                    </div>
                  ) : (
                    <button onClick={() => handleEliminar(receta.id)} aria-label={t('eliminar')} className="p-1.5 hover:bg-muted rounded-lg">
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  )}
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                {receta.ingredientes.map((i) => i.nombre).join(', ')}
              </p>
              <button onClick={() => handleAnadirALista(receta.id)} className="btn-secondary w-full flex items-center justify-center gap-2">
                <ShoppingCart className="w-4 h-4" /> {t('anadir_a_la_lista')}
              </button>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <Modal onCerrar={() => setShowForm(false)}>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{editandoId !== null ? t('editar_receta') : t('nueva_receta')}</h2>
            <form onSubmit={handleGuardar} className="space-y-4">
              <input
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder={t('nombre_receta')}
                className="input-field"
                required
              />

              <div className="space-y-2">
                <label className="block text-sm font-medium">{t('ingredientes')}</label>
                {ingredientes.map((ing, idx) => (
                  <div key={idx} className="flex gap-2">
                    <input
                      type="text"
                      value={ing.nombre}
                      onChange={(e) => actualizarIngrediente(idx, 'nombre', e.target.value)}
                      placeholder={t('nombre_ingrediente')}
                      className="input-field flex-1"
                    />
                    <input
                      type="number"
                      value={ing.cantidad}
                      onChange={(e) => actualizarIngrediente(idx, 'cantidad', parseInt(e.target.value) || 1)}
                      className="input-field w-16"
                      min={1}
                    />
                    <button
                      type="button"
                      onClick={() => setIngredientes((prev) => prev.filter((_, i) => i !== idx))}
                      aria-label={t('eliminar')}
                      className="w-9 h-9 shrink-0 flex items-center justify-center"
                    >
                      <X className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setIngredientes((prev) => [...prev, INGREDIENTE_VACIO()])}
                  className="text-sm text-accent hover:underline flex items-center gap-1"
                >
                  <Plus className="w-4 h-4" /> {t('anadir_ingrediente')}
                </button>
              </div>

              <div className="flex gap-2">
                <button type="submit" className="btn-primary flex-1">{t('guardar')}</button>
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary flex-1">{t('cancelar')}</button>
              </div>
            </form>
          </div>
        </Modal>
      )}
    </div>
  )
}
