'use client'

import { useEffect, useState } from 'react'
import { TrendingDown, BookOpen } from 'lucide-react'
import { consumo as consumoApi, historial as historialApi } from '@/lib/api'

interface ProductoConsumo {
  nombre: string
  icono: string | null
  consumo: number
}

interface ArticuloCatalogo {
  nombre: string
  icono: string | null
  categoria: string | null
  unidad: string
  cantidad_defecto: number | null
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
    cargarConsumo(dias)
    historialApi
      .listar()
      .then((data: any) => setCatalogo(Array.isArray(data) ? data : []))
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cargarConsumo = async (d: number) => {
    try {
      setLoading(true)
      setError('')
      const data: any = await consumoApi.resumen(d)
      setPorProducto(data.por_producto || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de conexión')
    } finally {
      setLoading(false)
    }
  }

  const cambiarRango = (d: number) => {
    setDias(d)
    cargarConsumo(d)
  }

  const maxConsumo = Math.max(1, ...porProducto.map((p) => p.consumo))

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">Historial</h1>
        <p className="text-muted-foreground mt-1">Consumo de tu lista activa y catálogo de artículos aprendidos</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg text-sm">{error}</div>
      )}

      <div className="card space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-accent" /> Más consumido
          </h2>
          <div className="flex gap-1">
            {RANGOS.map((r) => (
              <button
                key={r.dias}
                onClick={() => cambiarRango(r.dias)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  dias === r.dias ? 'bg-accent text-accent-foreground' : 'bg-muted text-foreground hover:bg-border'
                }`}
              >
                {r.label}
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
            {porProducto.map((p, i) => (
              <div key={i} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{p.nombre}</span>
                  <span className="text-muted-foreground">{p.consumo} ud.</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full"
                    style={{ width: `${Math.max(4, (p.consumo / maxConsumo) * 100)}%` }}
                  />
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
            {catalogo.map((a, i) => (
              <div key={i} className="p-2 rounded-lg bg-muted text-sm truncate" title={a.nombre}>
                {a.nombre}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
