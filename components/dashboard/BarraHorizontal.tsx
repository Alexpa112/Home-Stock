'use client'

import { DatoBarra } from '@/lib/gastosStats'

interface BarraHorizontalProps {
  datos: DatoBarra[]
  diverging?: boolean
  formatearValor?: (v: number) => string
}

/** Lista de barras horizontales en SVG puro (sin librería de gráficos).
 * Con `diverging` las barras se dibujan a ambos lados de un eje central
 * (verde a la derecha si el valor es positivo, roja a la izquierda si es
 * negativo) — pensado para el balance por persona. */
export function BarraHorizontal({ datos, diverging = false, formatearValor = (v) => v.toFixed(2) }: BarraHorizontalProps) {
  if (datos.length === 0) return null
  const maxAbs = Math.max(...datos.map((d) => Math.abs(d.valor)), 0.01)

  return (
    <div className="space-y-1.5">
      {datos.map((d) => {
        const pct = (Math.abs(d.valor) / maxAbs) * 100
        const negativo = d.valor < 0
        return (
          <div key={d.etiqueta} className="flex items-center gap-2 text-sm">
            <span className="w-24 sm:w-28 truncate text-muted-foreground shrink-0" title={d.etiqueta}>
              {d.etiqueta}
            </span>
            <svg viewBox="0 0 100 20" preserveAspectRatio="none" className="flex-1 h-5 overflow-visible">
              {diverging && <line x1="50" y1="0" x2="50" y2="20" className="stroke-border" strokeWidth="1" />}
              <rect
                x={diverging ? (negativo ? 50 - pct / 2 : 50) : 0}
                y="2"
                width={diverging ? pct / 2 : pct}
                height="16"
                rx="3"
                className={negativo ? 'fill-red-500' : 'fill-emerald-500'}
              >
                <title>{`${d.etiqueta}: ${formatearValor(d.valor)}`}</title>
              </rect>
            </svg>
            <span className="w-16 sm:w-20 text-right shrink-0 tabular-nums text-xs">{formatearValor(d.valor)}</span>
          </div>
        )
      })}
    </div>
  )
}
