'use client'

import { agruparPorMes } from '@/lib/gastosStats'
import { GastoCard } from './GastoCard'
import { formatImporte } from '@/lib/format'

interface Participante {
  usuario_id: number
  importe: number
  nombre_usuario: string
}

interface Gasto {
  id: number
  descripcion: string
  importe_total: number
  fecha: string
  categoria?: string | null
  usuario_pagador_id: number
  pagador_nombre: string
  tiene_recibo: boolean
  participantes: Participante[]
}

interface ListaGastosProps {
  gastos: Gasto[]
  simboloMoneda: string
  idioma: string
  getCategoriaGastoIcon: (nombre: string | null | undefined) => string | null
  onAbrirDetalle: (gasto: Gasto) => void
  labelDetalle: string
}

// Opción 4A del rediseño de gastos (docs/REDISENO_GASTOS.md): la lista se
// agrupa por mes con una cabecera "sticky" y el subtotal de ese mes, en vez
// de una lista plana. La agrupación en sí (orden, suma) vive en
// lib/gastosStats.ts (agruparPorMes) para poder testearla sin DOM.
export function ListaGastos({
  gastos,
  simboloMoneda,
  idioma,
  getCategoriaGastoIcon,
  onAbrirDetalle,
  labelDetalle,
}: ListaGastosProps) {
  const grupos = agruparPorMes(gastos)

  return (
    <div className="space-y-4">
      {grupos.map((grupo) => {
        const fechaGrupo = new Date(`${grupo.ym}-01T00:00:00`)
        const etiquetaMes = Number.isNaN(fechaGrupo.getTime())
          ? grupo.ym
          : new Intl.DateTimeFormat(idioma, { month: 'long', year: 'numeric' }).format(fechaGrupo)

        return (
          <div key={grupo.ym} className="space-y-2">
            <div className="sticky top-0 z-10 -mx-4 px-4 sm:-mx-6 sm:px-6 py-1.5 bg-background/95 backdrop-blur-sm flex items-baseline justify-between">
              <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{etiquetaMes}</span>
              <span className="text-xs font-bold tabular-nums text-muted-foreground">
                {formatImporte(grupo.total, simboloMoneda)}
              </span>
            </div>
            {/* lista-larga va en ESTE contenedor y no en el del grupo: la
                cabecera del mes es sticky y la contencion de
                content-visibility le crearia un nuevo bloque contenedor, con
                lo que dejaria de quedarse pegada arriba al desplazar. */}
            <div className="space-y-2 lista-larga">
              {grupo.gastos.map((gasto) => (
                <GastoCard
                  key={gasto.id}
                  gasto={gasto}
                  icono={getCategoriaGastoIcon(gasto.categoria)}
                  simboloMoneda={simboloMoneda}
                  idioma={idioma}
                  onAbrirDetalle={onAbrirDetalle}
                  labelDetalle={labelDetalle}
                />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
