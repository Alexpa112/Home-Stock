'use client'

import { formatImporte } from '@/lib/format'

interface SaldoItem {
  usuario_id: number
  nombre_usuario: string
  saldo: number
}

interface SugerenciaPago {
  usuario_origen_id: number
  usuario_origen_nombre: string
  usuario_destino_id: number
  usuario_destino_nombre: string
  importe: number
}

interface BalanceHeroProps {
  saldo: SaldoItem[]
  sugerenciasPropias: SugerenciaPago[]
  usuarioId: number | null
  simboloMoneda: string
  t: (clave: string) => string
}

const TOLERANCIA = 0.01

// Opción 1A del rediseño de gastos (docs/REDISENO_GASTOS.md): "Tu balance"
// con la cifra que importa (positiva = te deben, negativa = debes) en
// grande, y el desglose frente a cada persona en chips. Reutiliza las
// sugerencias de pago que ya calcula el backend (GET /api/gastos/simplificar,
// stockhogar/rutas/gastos.py) en vez de repetir el algoritmo en el cliente,
// así BalanceHero y BalancesPanel.tsx (9A) siempre coinciden.
export function BalanceHero({ saldo, sugerenciasPropias, usuarioId, simboloMoneda, t }: BalanceHeroProps) {
  const tuSaldo = saldo.find((s) => s.usuario_id === usuarioId)?.saldo ?? 0
  const enPaz = Math.abs(tuSaldo) <= TOLERANCIA

  return (
    <div className="card space-y-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('tu_balance')}</p>
        <p className={`text-3xl font-bold tabular-nums ${enPaz ? 'text-foreground' : tuSaldo > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {enPaz ? formatImporte(0, simboloMoneda) : `${tuSaldo > 0 ? '+' : '−'} ${formatImporte(Math.abs(tuSaldo), simboloMoneda)}`}
        </p>
        <p className="text-sm text-muted-foreground">
          {enPaz ? t('estas_en_paz') : tuSaldo > 0 ? t('te_deben_total') : t('debes_total')}
        </p>
      </div>

      {sugerenciasPropias.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {sugerenciasPropias.map((s, i) => {
            const soyOrigen = s.usuario_origen_id === usuarioId
            const nombre = soyOrigen ? s.usuario_destino_nombre : s.usuario_origen_nombre
            return (
              <span key={i} className={`badge ${soyOrigen ? 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300' : 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'}`}>
                {nombre} {formatImporte(s.importe, simboloMoneda)}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
