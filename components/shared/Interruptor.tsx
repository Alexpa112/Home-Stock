'use client'

import { Check, Loader2 } from 'lucide-react'

interface InterruptorProps {
  activo: boolean
  onChange: (nuevoValor: boolean) => void
  /** Nombre accesible: lo lee el lector de pantalla junto al estado. */
  etiqueta: string
  deshabilitado?: boolean
  /** Mientras se guarda el cambio: gira un indicador y no admite otro toque. */
  cargando?: boolean
}

/**
 * Interruptor unico de la app (Ajustes y cualquier ajuste on/off). El dibujo
 * vive en .interruptor de app/globals.css; aqui solo la semantica: role=switch,
 * aria-checked y el estado de carga. Antes cada pantalla copiaba su propio
 * boton con el pulgar mal centrado (6 px arriba, 2 px abajo).
 */
export function Interruptor({ activo, onChange, etiqueta, deshabilitado = false, cargando = false }: InterruptorProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={activo}
      aria-label={etiqueta}
      aria-busy={cargando || undefined}
      disabled={deshabilitado || cargando}
      onClick={() => onChange(!activo)}
      className="interruptor"
    >
      <span aria-hidden="true" className="interruptor-pulgar">
        {cargando ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : activo ? (
          <Check className="w-3.5 h-3.5" strokeWidth={3} />
        ) : null}
      </span>
    </button>
  )
}
