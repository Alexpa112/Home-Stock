'use client'

import { useState } from 'react'
import { Undo2 } from 'lucide-react'
import { formatImporte } from '@/lib/format'

interface Liquidacion {
  id: number
  usuario_origen_id: number
  origen_nombre: string
  usuario_destino_id: number
  destino_nombre: string
  importe: number
  fecha: string
  nota: string | null
}

interface HistorialLiquidacionesProps {
  liquidaciones: Liquidacion[]
  simboloMoneda: string
  idioma: string
  onDeshacer: (id: number) => void
  t: (clave: string) => string
}

// Fase 7 del rediseño de gastos (docs/REDISENO_GASTOS.md): antes las
// liquidaciones se guardaban pero no había forma de verlas ni de deshacer
// una registrada por error. Vive debajo de BalancesPanel.tsx (9A) en la
// pestaña Balances.
export function HistorialLiquidaciones({ liquidaciones, simboloMoneda, idioma, onDeshacer, t }: HistorialLiquidacionesProps) {
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)

  if (liquidaciones.length === 0) return null

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('historial_pagos')}</p>
      <div className="space-y-2">
        {liquidaciones.map((l) => {
          const fecha = new Date(l.fecha)
          const fechaTexto = Number.isNaN(fecha.getTime())
            ? null
            : new Intl.DateTimeFormat(idioma, { day: 'numeric', month: 'short' }).format(fecha)

          return (
            <div key={l.id} className="card-compact flex items-center gap-3">
              <div className="flex-1 min-w-0 text-sm">
                <span className="font-medium">{l.origen_nombre}</span>{' '}
                <span className="text-muted-foreground">{t('paga_a')}</span>{' '}
                <span className="font-medium">{l.destino_nombre}</span>
                {fechaTexto && <span className="text-muted-foreground"> · {fechaTexto}</span>}
                {l.nota && <span className="text-muted-foreground"> ({l.nota})</span>}
              </div>
              <span className="font-semibold tabular-nums flex-shrink-0">{formatImporte(l.importe, simboloMoneda)}</span>
              {confirmandoId === l.id ? (
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button onClick={() => { onDeshacer(l.id); setConfirmandoId(null) }} className="px-2 h-8 text-xs font-semibold text-white bg-red-500 rounded-lg">{t('si')}</button>
                  <button onClick={() => setConfirmandoId(null)} className="px-2 h-8 text-xs font-semibold text-foreground bg-muted rounded-lg">{t('no')}</button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmandoId(l.id)}
                  aria-label={t('deshacer')}
                  className="w-8 h-8 flex items-center justify-center hover:bg-muted rounded-lg transition-colors flex-shrink-0"
                >
                  <Undo2 className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
