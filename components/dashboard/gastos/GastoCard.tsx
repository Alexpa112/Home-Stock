'use client'

import { User, CalendarDays, Paperclip } from 'lucide-react'
import { CategoriaIcono } from './CategoriaIcono'
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

interface GastoCardProps {
  gasto: Gasto
  icono: string | null
  simboloMoneda: string
  idioma: string
  onAbrirDetalle: (gasto: Gasto) => void
  labelDetalle: string
}

// Opción 3C del rediseño de gastos (docs/REDISENO_GASTOS.md): título e
// importe en la primera línea, categoría/pagador/fecha como chips en la
// segunda. El icono de categoría usa CategoriaIcono (opción 11A), así que
// la categoría no se repite como chip para no duplicar información. Desde
// la Fase 4 (opción 5A) la tarjeta ya no lleva botones de editar/eliminar:
// pulsarla abre GastoDetalle.tsx, que es donde viven esas acciones.
export function GastoCard({ gasto, icono, simboloMoneda, idioma, onAbrirDetalle, labelDetalle }: GastoCardProps) {
  const fecha = new Date(gasto.fecha)
  const fechaTexto = Number.isNaN(fecha.getTime())
    ? null
    : new Intl.DateTimeFormat(idioma, { day: 'numeric', month: 'short' }).format(fecha)

  return (
    <button
      onClick={() => onAbrirDetalle(gasto)}
      aria-label={labelDetalle}
      className="card w-full text-left space-y-2.5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-3">
        <CategoriaIcono categoria={gasto.categoria} icono={icono} />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-foreground truncate flex items-center gap-1.5">
            {gasto.descripcion}
            {gasto.tiene_recibo && <Paperclip className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />}
          </p>
        </div>
        <span className="font-bold text-foreground tabular-nums flex-shrink-0">
          {formatImporte(gasto.importe_total, simboloMoneda)}
        </span>
      </div>

      <div className="flex items-center gap-1.5 flex-wrap pl-[calc(2.25rem+0.75rem)]">
        <span className="badge bg-muted text-muted-foreground">
          <User className="w-3 h-3" /> {gasto.pagador_nombre}
        </span>
        {fechaTexto && (
          <span className="badge bg-muted text-muted-foreground">
            <CalendarDays className="w-3 h-3" /> {fechaTexto}
          </span>
        )}
      </div>
    </button>
  )
}
