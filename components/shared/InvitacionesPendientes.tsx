'use client'

import { useEffect, useState } from 'react'
import { Mail, Check, X } from 'lucide-react'
import { permisos } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

interface Invitacion {
  id: number
  codigo_invitacion: string
  nivel: string
  nombre_hogar: string
  nombre_propietario: string
}

/**
 * Invitaciones a hogares dirigidas al usuario (S-10): las creadas al
 * compartir por nombre de usuario ya no dan acceso inmediato, asi que hace
 * falta un sitio donde aceptarlas o rechazarlas explicitamente.
 */
export function InvitacionesPendientes() {
  const { t } = useTranslation()
  const [invitaciones, setInvitaciones] = useState<Invitacion[]>([])
  const [procesando, setProcesando] = useState<string | null>(null)

  useEffect(() => {
    permisos
      .invitacionesPendientes()
      .then((data: any) => setInvitaciones(data || []))
      .catch(() => {})
  }, [])

  if (invitaciones.length === 0) return null

  const aceptar = async (codigo: string) => {
    setProcesando(codigo)
    try {
      await permisos.aceptarInvitacion(codigo)
      setInvitaciones((prev) => prev.filter((i) => i.codigo_invitacion !== codigo))
      window.location.reload()
    } catch {
      setProcesando(null)
    }
  }

  const rechazar = async (codigo: string) => {
    setProcesando(codigo)
    try {
      await permisos.rechazarInvitacion(codigo)
      setInvitaciones((prev) => prev.filter((i) => i.codigo_invitacion !== codigo))
    } finally {
      setProcesando(null)
    }
  }

  return (
    <div className="fixed top-2 inset-x-0 z-50 flex flex-col items-center gap-2 px-4 pointer-events-none">
      {invitaciones.map((inv) => (
        <div
          key={inv.codigo_invitacion}
          className="card !p-3 flex items-center gap-2.5 shadow-lg pointer-events-auto max-w-sm w-full"
        >
          <Mail className="w-4 h-4 text-accent shrink-0" />
          <span className="text-sm flex-1">
            <strong>{inv.nombre_propietario}</strong> · {inv.nombre_hogar}
          </span>
          <button
            onClick={() => aceptar(inv.codigo_invitacion)}
            disabled={procesando === inv.codigo_invitacion}
            aria-label={t('btn_aceptar')}
            className="w-7 h-7 flex items-center justify-center rounded-md bg-accent text-accent-foreground shrink-0 disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={() => rechazar(inv.codigo_invitacion)}
            disabled={procesando === inv.codigo_invitacion}
            aria-label={t('btn_rechazar')}
            className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-muted shrink-0 disabled:opacity-50"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  )
}
