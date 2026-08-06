'use client'

import { ReactNode, useEffect } from 'react'
import { X } from 'lucide-react'
import { suspenderPorEdicion, reanudarPorEdicion } from '@/lib/editSuspension'

interface HojaCompletaProps {
  titulo: string
  onCerrar: () => void
  cabeceraDerecha?: ReactNode
  children: ReactNode
}

// Opción 7A del rediseño de gastos (docs/REDISENO_GASTOS.md): hoja a
// pantalla completa para el alta/edición, en vez de un Modal con scroll
// anidado. Mismo patrón de suspensión de refrescos que Modal.tsx y mismas
// variables de zona segura (--mobile-toolbar-h) para no quedar tapada por
// la barra inferior en móvil.
export function HojaCompleta({ titulo, onCerrar, cabeceraDerecha, children }: HojaCompletaProps) {
  useEffect(() => {
    suspenderPorEdicion()
    return () => reanudarPorEdicion()
  }, [])

  return (
    <div className="fixed inset-0 z-[60] bg-background flex flex-col pb-[var(--mobile-toolbar-h)] lg:pb-0">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border flex-shrink-0">
        <button
          onClick={onCerrar}
          className="w-9 h-9 flex items-center justify-center hover:bg-muted rounded-lg transition-colors"
          aria-label={titulo}
        >
          <X className="w-5 h-5" />
        </button>
        <h2 className="flex-1 text-center font-semibold truncate">{titulo}</h2>
        <div className="w-9 flex justify-end">{cabeceraDerecha}</div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-lg mx-auto p-4 sm:p-6">{children}</div>
      </div>
    </div>
  )
}
