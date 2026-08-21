'use client'

import { useEffect, useState } from 'react'
import { TrendingDown, TrendingUp } from 'lucide-react'
import { Modal } from '@/components/dashboard/Modal'
import { productos } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

interface EntradaPrecio {
  precio: number
  fecha: string
}

interface HistorialPreciosModalProps {
  productoId: number
  nombreProducto: string
  onCerrar: () => void
}

// Evolucion de precio de un producto (P-04), a partir de los tickets
// confirmados con precio detectado por OCR. Sin libreria de graficos: una
// barra proporcional al maximo del historial es suficiente para ver la
// tendencia sin anadir dependencias nuevas.
export function HistorialPreciosModal({ productoId, nombreProducto, onCerrar }: HistorialPreciosModalProps) {
  const { t, idioma } = useTranslation()
  const [entradas, setEntradas] = useState<EntradaPrecio[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    productos
      .historialPrecios(productoId)
      .then((datos: any) => setEntradas(datos || []))
      .catch(() => setError(t('err_cargar_historial_precios')))
      .finally(() => setCargando(false))
  }, [productoId, t])

  const maximo = entradas.reduce((max, e) => Math.max(max, e.precio), 0)
  const ultimo = entradas[entradas.length - 1]
  const anterior = entradas[entradas.length - 2]
  const tendenciaSubida = ultimo && anterior ? ultimo.precio > anterior.precio : null

  return (
    <Modal onCerrar={onCerrar}>
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">{t('historial_precios')}</h2>
        <p className="text-sm text-muted-foreground">{nombreProducto}</p>

        {cargando ? (
          <p className="text-sm text-muted-foreground">{t('cargando')}</p>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : entradas.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('sin_historial_precios')}</p>
        ) : (
          <>
            {tendenciaSubida !== null && (
              <div className={`flex items-center gap-1.5 text-sm font-medium ${tendenciaSubida ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                {tendenciaSubida ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                {tendenciaSubida ? t('precio_ha_subido') : t('precio_ha_bajado')}
              </div>
            )}
            <ul className="space-y-1.5 max-h-80 overflow-y-auto">
              {[...entradas].reverse().map((entrada, i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-20 shrink-0">
                    {/* Con el idioma de la app, no el del navegador (mismo
                        criterio que las fechas de gastos). */}
                    {new Intl.DateTimeFormat(idioma, { dateStyle: 'short' })
                      .format(new Date(entrada.fecha))}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${maximo > 0 ? (entrada.precio / maximo) * 100 : 0}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium tabular-nums w-16 text-right">
                    {entrada.precio.toFixed(2)} €
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        <button type="button" onClick={onCerrar} className="btn-secondary w-full">
          {t('cancelar')}
        </button>
      </div>
    </Modal>
  )
}
