'use client'

import { DatoBarra } from '@/lib/gastosStats'

interface GraficoColumnasProps {
  datos: DatoBarra[]
  formatearValor?: (v: number) => string
}

/** Columnas verticales en SVG puro, pensadas para una serie temporal
 * (evolución mensual de gastos). El <title> por columna da un tooltip
 * nativo del navegador sin JS adicional. */
export function GraficoColumnas({ datos, formatearValor = (v) => v.toFixed(0) }: GraficoColumnasProps) {
  if (datos.length === 0) return null
  const max = Math.max(...datos.map((d) => d.valor), 0.01)
  const anchoCol = 100 / datos.length

  return (
    <div className="w-full">
      <svg viewBox="0 0 100 50" preserveAspectRatio="none" className="w-full h-32 sm:h-40">
        {datos.map((d, i) => {
          const altura = (d.valor / max) * 46
          return (
            <rect
              key={d.etiqueta}
              x={i * anchoCol + anchoCol * 0.15}
              y={48 - altura}
              width={anchoCol * 0.7}
              height={Math.max(altura, 0.5)}
              rx="1"
              className="fill-accent"
            >
              <title>{`${d.etiqueta}: ${formatearValor(d.valor)}`}</title>
            </rect>
          )
        })}
      </svg>
      <div className="flex text-[10px] text-muted-foreground mt-1">
        {datos.map((d) => (
          <span key={d.etiqueta} style={{ width: `${anchoCol}%` }} className="text-center truncate">
            {d.etiqueta}
          </span>
        ))}
      </div>
    </div>
  )
}
