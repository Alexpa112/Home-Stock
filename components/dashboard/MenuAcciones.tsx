'use client'

import { useState, ReactNode } from 'react'
import { MoreVertical } from 'lucide-react'

interface AccionMenu {
  icono: ReactNode
  etiqueta: string
  onClick: () => void
  destructiva?: boolean
}

interface MenuAccionesProps {
  acciones: AccionMenu[]
  label: string
}

// Menú "⋯" compacto para acciones secundarias de una pantalla (opción 6A del
// rediseño de gastos, docs/REDISENO_GASTOS.md): igual patrón que Modal.tsx
// para cerrar al pulsar fuera, pero sin overlay oscuro ya que es un panel
// pequeño anclado al botón, no una hoja a pantalla completa.
export function MenuAcciones({ acciones, label }: MenuAccionesProps) {
  const [abierto, setAbierto] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setAbierto((v) => !v)}
        aria-label={label}
        aria-expanded={abierto}
        className="w-11 h-11 flex items-center justify-center rounded-xl border border-border bg-card hover:bg-muted transition-colors"
      >
        <MoreVertical className="w-5 h-5" />
      </button>

      {abierto && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setAbierto(false)} />
          <div className="absolute right-0 top-full mt-2 z-40 w-56 rounded-xl border border-border bg-card shadow-lg overflow-hidden">
            {acciones.map((accion, i) => (
              <button
                key={i}
                onClick={() => { setAbierto(false); accion.onClick() }}
                className={`w-full flex items-center gap-3 px-4 py-3 text-sm text-left hover:bg-muted transition-colors ${
                  accion.destructiva ? 'text-red-600 dark:text-red-400' : 'text-foreground'
                }`}
              >
                {accion.icono}
                {accion.etiqueta}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
