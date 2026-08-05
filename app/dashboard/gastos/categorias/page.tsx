'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Plus, Tags, X, AlertCircle } from 'lucide-react'
import { IconPicker } from '@/components/dashboard/IconPicker'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { categoriasGasto as categoriasGastoApi } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'
import { getCached, setCached } from '@/lib/dataCache'

const CACHE_KEY_CATEGORIAS_GASTO = 'gastos:categorias'

interface CategoriaGasto {
  id: number
  nombre: string
  icono: string
}

// Gestión de categorías de gasto, antes incrustada en el formulario de alta
// de FormularioGasto.tsx (ver docs/REDISENO_GASTOS.md, Fase 3): con su
// propia página cabe el listado y el alta sin el límite de altura de una
// hoja o modal de gasto.
export default function CategoriasGastoPage() {
  const { t } = useTranslation()
  const [categorias, setCategorias] = useState<CategoriaGasto[]>(
    () => getCached<CategoriaGasto[]>(CACHE_KEY_CATEGORIAS_GASTO) || []
  )
  const [nombre, setNombre] = useState('')
  const [icono, setIcono] = useState<string | undefined>(undefined)
  const [mostrarIconPicker, setMostrarIconPicker] = useState(false)
  const [confirmandoEliminarId, setConfirmandoEliminarId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const cargar = () => {
    categoriasGastoApi.listar().then((data: any) => {
      const arr = Array.isArray(data) ? data : []
      setCategorias(arr)
      setCached(CACHE_KEY_CATEGORIAS_GASTO, arr)
    }).catch(() => {})
  }

  useEffect(() => {
    cargar()
  }, [])

  const handleCrear = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nombre.trim()) return
    try {
      setError('')
      await categoriasGastoApi.crear(nombre.trim(), icono)
      setNombre('')
      setIcono(undefined)
      cargar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_crear_categoria'))
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
      await categoriasGastoApi.eliminar(id)
      cargar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_categoria_uso'))
    }
  }

  return (
    <div className="max-w-lg mx-auto p-4 lg:p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Link href="/dashboard/gastos" className="w-9 h-9 flex items-center justify-center hover:bg-muted rounded-lg transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-bold">{t('categorias_gasto')}</h1>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleCrear} className="flex gap-2">
        <button
          type="button"
          onClick={() => setMostrarIconPicker(true)}
          className="w-12 h-12 shrink-0 rounded-xl bg-card border border-border flex items-center justify-center"
          aria-label={t('cambiar_icono')}
        >
          {icono ? (
            <IconRenderer name={icono} className="w-5 h-5 text-muted-foreground" />
          ) : (
            <Tags className="w-5 h-5 text-muted-foreground" />
          )}
        </button>
        <input
          type="text"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder={t('nueva_categoria')}
          className="input-field flex-1"
        />
        <button type="submit" className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> {t('añadir')}
        </button>
      </form>

      {categorias.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-6">{t('sin_categorias_aun')}</p>
      ) : (
        <div className="space-y-2">
          {categorias.map((cat) => (
            <div key={cat.id} className="card flex items-center gap-3">
              {cat.icono && <IconRenderer name={cat.icono} className="w-4 h-4 text-muted-foreground" />}
              <span className="flex-1 text-sm font-medium">{cat.nombre}</span>
              {confirmandoEliminarId === cat.id ? (
                <div className="flex items-center gap-1">
                  <span className="text-xs text-red-600 dark:text-red-400 mr-0.5">{t('eliminar_pregunta')}</span>
                  <button onClick={() => handleEliminar(cat.id)} className="px-2 py-1 text-xs text-white bg-red-500 rounded-md font-medium">{t('si')}</button>
                  <button onClick={() => setConfirmandoEliminarId(null)} className="px-2 py-1 text-xs bg-muted rounded-md font-medium">{t('no')}</button>
                </div>
              ) : (
                <button onClick={() => handleEliminar(cat.id)} aria-label={`${t('eliminar')} ${cat.nombre}`}>
                  <X className="w-4 h-4 text-red-500" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {mostrarIconPicker && (
        <IconPicker
          valorActual={icono}
          onSeleccionar={(valor) => {
            setIcono(valor)
            setMostrarIconPicker(false)
          }}
          onCerrar={() => setMostrarIconPicker(false)}
        />
      )}
    </div>
  )
}
