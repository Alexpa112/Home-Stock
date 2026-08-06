'use client'

import { HandCoins } from 'lucide-react'
import { formatImporte } from '@/lib/format'
import { colorAvatar, inicialesAvatar } from '@/lib/avatarColor'

interface SugerenciaPago {
  usuario_origen_id: number
  usuario_origen_nombre: string
  usuario_destino_id: number
  usuario_destino_nombre: string
  importe: number
}

interface BalancesPanelProps {
  sugerencias: SugerenciaPago[]
  simboloMoneda: string
  onSaldar: (sugerencia: SugerenciaPago) => void
  t: (clave: string) => string
}

// Opción 9A del rediseño de gastos (docs/REDISENO_GASTOS.md): en vez de una
// lista de saldos netos que cada uno tiene que interpretar, se muestra
// directamente quién paga a quién y cuánto — reutilizando el algoritmo de
// simplificación ya calculado por el backend (GET /api/gastos/simplificar),
// con un botón "Saldar" que abre el pago ya prerrellenado.
export function BalancesPanel({ sugerencias, simboloMoneda, onSaldar, t }: BalancesPanelProps) {
  if (sugerencias.length === 0) {
    return (
      <div className="card text-center py-8">
        <p className="text-sm text-muted-foreground">{t('estas_en_paz')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {sugerencias.map((s, i) => (
        <div key={i} className="card flex items-center gap-3">
          <span
            className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
            style={{ backgroundColor: colorAvatar(s.usuario_origen_nombre) }}
          >
            {inicialesAvatar(s.usuario_origen_nombre)}
          </span>
          <div className="flex-1 min-w-0 text-sm">
            <span className="font-semibold">{s.usuario_origen_nombre}</span>{' '}
            <span className="text-muted-foreground">{t('paga_a')}</span>{' '}
            <span className="font-semibold">{s.usuario_destino_nombre}</span>
          </div>
          <div className="flex flex-col items-end gap-1 flex-shrink-0">
            <span className="font-bold tabular-nums">{formatImporte(s.importe, simboloMoneda)}</span>
            <button
              onClick={() => onSaldar(s)}
              className="flex items-center gap-1 text-xs font-semibold text-accent hover:underline"
            >
              <HandCoins className="w-3 h-3" /> {t('saldar')}
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
