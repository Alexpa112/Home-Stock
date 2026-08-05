'use client'

import { SegmentedControl } from '@/components/dashboard/SegmentedControl'
import { formatImporte } from '@/lib/format'
import { colorAvatar, inicialesAvatar } from '@/lib/avatarColor'

type ModoReparto = 'igual' | 'porcentaje' | 'partes' | 'personalizado'

interface Miembro {
  id: number
  nombre_usuario: string
}

interface RepartoParticipantesProps {
  miembros: Miembro[]
  seleccionados: Set<number>
  modoReparto: ModoReparto
  importesPorMiembro: Record<number, string>
  porcentajesPorMiembro: Record<number, string>
  partesPorMiembro: Record<number, string>
  simboloMoneda: string
  reparteCuadra: boolean
  onToggle: (id: number) => void
  onCambiarModo: (modo: ModoReparto) => void
  onCambiarPorcentaje: (id: number, valor: string) => void
  onCambiarPartes: (id: number, valor: string) => void
  onCambiarImporte: (id: number, valor: string) => void
  etiquetaParticipantes: string
  etiquetaIgual: string
  etiquetaPorcentaje: string
  etiquetaPartes: string
  etiquetaPersonalizado: string
  etiquetaExcluido: string
  etiquetaCuadra: string
  etiquetaNoCuadra: string
}

// Opción 8B del rediseño de gastos (docs/REDISENO_GASTOS.md): una fila por
// miembro con avatar, nombre e importe; los excluidos quedan atenuados en
// vez de desaparecer. Conserva los cuatro modos de reparto ya existentes
// (igual/porcentaje/partes/personalizado), solo cambia su presentación.
export function RepartoParticipantes({
  miembros,
  seleccionados,
  modoReparto,
  importesPorMiembro,
  porcentajesPorMiembro,
  partesPorMiembro,
  simboloMoneda,
  reparteCuadra,
  onToggle,
  onCambiarModo,
  onCambiarPorcentaje,
  onCambiarPartes,
  onCambiarImporte,
  etiquetaParticipantes,
  etiquetaIgual,
  etiquetaPorcentaje,
  etiquetaPartes,
  etiquetaPersonalizado,
  etiquetaExcluido,
  etiquetaCuadra,
  etiquetaNoCuadra,
}: RepartoParticipantesProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{etiquetaParticipantes}</span>
      </div>

      <SegmentedControl
        valor={modoReparto}
        onCambiar={onCambiarModo}
        opciones={[
          { valor: 'igual', etiqueta: etiquetaIgual },
          { valor: 'porcentaje', etiqueta: etiquetaPorcentaje },
          { valor: 'partes', etiqueta: etiquetaPartes },
          { valor: 'personalizado', etiqueta: etiquetaPersonalizado },
        ]}
      />

      <div className="space-y-1.5">
        {miembros.map((m) => {
          const incluido = seleccionados.has(m.id)
          return (
            <div
              key={m.id}
              onClick={() => onToggle(m.id)}
              className={`flex items-center gap-3 p-2 rounded-xl cursor-pointer transition-opacity ${incluido ? '' : 'opacity-45'}`}
            >
              <span
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                style={{ backgroundColor: colorAvatar(m.nombre_usuario) }}
              >
                {inicialesAvatar(m.nombre_usuario)}
              </span>
              <span className="flex-1 text-sm truncate">{m.nombre_usuario}</span>

              {!incluido ? (
                <span className="text-xs text-muted-foreground">{etiquetaExcluido}</span>
              ) : modoReparto === 'porcentaje' ? (
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={porcentajesPorMiembro[m.id] ?? ''}
                    onChange={(e) => onCambiarPorcentaje(m.id, e.target.value)}
                    className="input-field !py-1 !px-2 w-16 text-sm text-right"
                  />
                  <span className="text-xs text-muted-foreground w-16 text-right flex-shrink-0 tabular-nums">
                    {formatImporte(parseFloat(importesPorMiembro[m.id] || '0') || 0, simboloMoneda)}
                  </span>
                </div>
              ) : modoReparto === 'partes' ? (
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={partesPorMiembro[m.id] ?? '1'}
                    onChange={(e) => onCambiarPartes(m.id, e.target.value)}
                    className="input-field !py-1 !px-2 w-16 text-sm text-right"
                  />
                  <span className="text-xs text-muted-foreground w-16 text-right flex-shrink-0 tabular-nums">
                    {formatImporte(parseFloat(importesPorMiembro[m.id] || '0') || 0, simboloMoneda)}
                  </span>
                </div>
              ) : modoReparto === 'personalizado' ? (
                <div onClick={(e) => e.stopPropagation()}>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={importesPorMiembro[m.id] ?? ''}
                    onChange={(e) => onCambiarImporte(m.id, e.target.value)}
                    className="input-field !py-1 !px-2 w-24 text-sm text-right"
                  />
                </div>
              ) : (
                <span className="text-sm font-medium tabular-nums">
                  {formatImporte(parseFloat(importesPorMiembro[m.id] || '0') || 0, simboloMoneda)}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {seleccionados.size > 0 && (
        <p className={`text-xs ${reparteCuadra ? 'text-muted-foreground' : 'text-red-600 dark:text-red-400 font-medium'}`}>
          {reparteCuadra ? etiquetaCuadra : etiquetaNoCuadra}
        </p>
      )}
    </div>
  )
}
