'use client'

import { useEffect, useState } from 'react'
import { BookOpen, TrendingDown } from 'lucide-react'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { consumo as consumoApi, historial as historialApi } from '@/lib/api'
import { getErrorMessage } from '@/lib/error-utils'
import type { ArticuloCatalogo, ProductoConsumo } from '@/lib/types'

interface ConsumoResponse {
  por_producto?: ProductoConsumo[]
}

const RANGOS = [
  { dias: 7, label: '7 días' },
  { dias: 30, label: '30 días' },
  { dias: 90, label: '90 días' },
]

export default function HistorialPage() {
  const [dias, setDias] = useState(30)
  const [porProducto, setPorProducto] = useState<ProductoConsumo[]>([])
  const [catalogo, setCatalogo] = useState<ArticuloCatalogo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void cargarConsumo(dias)
    void historialApi
      .listar()
      .then((data) => setCatalogo(Array.isArray(data) ? (data as ArticuloCatalogo[]) : []))
      .catch((err) => setError(getErrorMessage(err, 'Error al cargar el catálogo aprendido')))
  }, [])

  const cargarConsumo = async (rango: number) => {
    try {
      setLoading(true)
      setError('')
      const data = await consumoApi.resumen(rango) as ConsumoResponse
      setPorProducto(data.por_producto || [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const maxConsumo = Math.max(1, ...porProducto.map((producto) => producto.consumo))

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">Historial</h1>
        <p className="text-muted-foreground mt-1">Consumo de tu lista activa y catálogo de artículos aprendidos</p>
      </div>

      {error && <StatusMessage message={error} />}

      <div className="card space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-accent" /> Más consumido
          </h2>
          <div className="flex gap-1">
            {RANGOS.map((rango) => (
              <button
                key={rango.dias}
                onClick={() => {
                  setDias(rango.dias)
                  void cargarConsumo(rango.dias)
                }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${dias === rango.dias ? 'bg-accent text-accent-foreground' : 'bg-muted text-foreground hover:bg-border'}`}
              >
                {rango.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando...</p>
        ) : porProducto.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Sin consumo registrado en este periodo (baja la cantidad de algún producto en Stock para que aparezca aquí).
          </p>
        ) : (
          <div className="space-y-3">
            {porProducto.map((producto, index) => (
              <div key={index} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{producto.nombre}</span>
                  <span className="text-muted-foreground">{producto.consumo} ud.</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-accent rounded-full" style={{ width: `${Math.max(4, (producto.consumo / maxConsumo) * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card space-y-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-accent" /> Catálogo aprendido ({catalogo.length})
        </h2>
        <p className="text-sm text-muted-foreground">
          Artículos que la app recuerda (icono, categoría, unidad habitual) para sugerirlos automáticamente.
        </p>
        {catalogo.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-80 overflow-y-auto">
            {catalogo.map((articulo, index) => (
              <div key={index} className="p-2 rounded-lg bg-muted text-sm truncate" title={articulo.nombre}>
                {articulo.nombre}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
