'use client'

import { useState } from 'react'
import { Pencil, Trash2, Paperclip } from 'lucide-react'
import { Modal } from '@/components/dashboard/Modal'
import { CategoriaIcono } from './CategoriaIcono'
import { formatImporte } from '@/lib/format'
import { colorAvatar, inicialesAvatar } from '@/lib/avatarColor'

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

interface GastoDetalleProps {
  gasto: Gasto
  icono: string | null
  simboloMoneda: string
  idioma: string
  reciboUrl: string
  onCerrar: () => void
  onEditar: (gasto: Gasto) => void
  onEliminar: (id: number) => void
  t: (clave: string) => string
}

// Opción 5A del rediseño de gastos (docs/REDISENO_GASTOS.md): pulsar la
// tarjeta abre este detalle con el reparto real por participante; Editar y
// Eliminar viven aquí (con confirmación explícita), no como botones fijos
// en cada tarjeta de la lista.
export function GastoDetalle({ gasto, icono, simboloMoneda, idioma, reciboUrl, onCerrar, onEditar, onEliminar, t }: GastoDetalleProps) {
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false)

  const fecha = new Date(gasto.fecha)
  const fechaTexto = Number.isNaN(fecha.getTime())
    ? null
    : new Intl.DateTimeFormat(idioma, { day: 'numeric', month: 'long', year: 'numeric' }).format(fecha)

  return (
    <Modal onCerrar={onCerrar}>
      <div className="space-y-5">
        <div className="flex items-start gap-3">
          <CategoriaIcono categoria={gasto.categoria} icono={icono} className="w-11 h-11" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-foreground">{gasto.descripcion}</p>
            {fechaTexto && <p className="text-sm text-muted-foreground">{fechaTexto}</p>}
          </div>
          <span className="font-bold text-foreground tabular-nums text-lg flex-shrink-0">
            {formatImporte(gasto.importe_total, simboloMoneda)}
          </span>
        </div>

        <div className="space-y-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('participantes')}
          </p>
          {gasto.participantes.map((p) => (
            <div key={p.usuario_id} className="flex items-center gap-3">
              <span
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                style={{ backgroundColor: colorAvatar(p.nombre_usuario) }}
              >
                {inicialesAvatar(p.nombre_usuario)}
              </span>
              <span className="flex-1 text-sm truncate">
                {p.nombre_usuario}
                {p.usuario_id === gasto.usuario_pagador_id && (
                  <span className="text-xs text-muted-foreground"> · {t('pagado_por')}</span>
                )}
              </span>
              <span className="text-sm font-medium tabular-nums">{formatImporte(p.importe, simboloMoneda)}</span>
            </div>
          ))}
        </div>

        {gasto.tiene_recibo && (
          <a
            href={reciboUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-accent hover:underline"
          >
            <Paperclip className="w-4 h-4" /> {t('ver_recibo')}
          </a>
        )}

        <div className="flex gap-2">
          <button
            onClick={() => onEditar(gasto)}
            className="btn-secondary flex-1 flex items-center justify-center gap-2"
          >
            <Pencil className="w-4 h-4" /> {t('editar')}
          </button>
          {confirmandoEliminar ? (
            <div className="flex-1 flex items-center gap-2">
              <button
                onClick={() => onEliminar(gasto.id)}
                className="flex-1 h-12 text-sm font-semibold text-white bg-red-500 rounded-xl"
              >
                {t('si')}
              </button>
              <button
                onClick={() => setConfirmandoEliminar(false)}
                className="flex-1 h-12 text-sm font-semibold text-foreground bg-muted rounded-xl"
              >
                {t('no')}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmandoEliminar(true)}
              className="flex-1 flex items-center justify-center gap-2 h-12 rounded-xl border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 font-semibold transition-colors hover:bg-red-50 dark:hover:bg-red-950"
            >
              <Trash2 className="w-4 h-4" /> {t('eliminar')}
            </button>
          )}
        </div>
      </div>
    </Modal>
  )
}
