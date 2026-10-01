'use client'

import { useRef, useState, ReactNode } from 'react'
import Link from 'next/link'
import { MoreVertical } from 'lucide-react'
import { epigrafeAntesDe } from '@/lib/agruparAcciones'

export interface AccionMenu {
  icono: ReactNode
  etiqueta: string
  // Con `href` se pinta un enlace (navegación); sin él, un botón con `onClick`.
  onClick?: () => void
  href?: string
  destructiva?: boolean
  // Epígrafe del grupo; se pinta una vez antes de su primera acción.
  grupo?: string
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
  // El panel mide w-56 (224 px). Si el botón está a media pantalla (junto a
  // "Añadir"), anclarlo por la derecha lo saca por el borde izquierdo.
  const [alinearIzquierda, setAlinearIzquierda] = useState(false)
  const botonRef = useRef<HTMLButtonElement>(null)

  const alternar = () => {
    if (!abierto && botonRef.current) {
      setAlinearIzquierda(botonRef.current.getBoundingClientRect().right < 224 + 8)
    }
    setAbierto((v) => !v)
  }

  return (
    <div className="relative">
      <button
        ref={botonRef}
        onClick={alternar}
        aria-label={label}
        aria-expanded={abierto}
        className="w-11 h-11 flex items-center justify-center rounded-xl border border-border bg-card hover:bg-muted transition-colors"
      >
        <MoreVertical className="w-5 h-5" />
      </button>

      {abierto && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setAbierto(false)} />
          <div className={`absolute ${alinearIzquierda ? 'left-0' : 'right-0'} top-full mt-2 z-40 w-56 rounded-xl border border-border bg-card shadow-lg overflow-hidden`}>
            {acciones.map((accion, i) => {
              const epigrafe = epigrafeAntesDe(acciones, i)
              const clases = `w-full flex items-center gap-3 px-4 py-3 text-sm text-left hover:bg-muted transition-colors ${
                accion.destructiva ? 'text-red-600 dark:text-red-400' : 'text-foreground'
              }`
              return (
                <div key={i}>
                  {epigrafe && (
                    <p className="px-4 pt-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                      {epigrafe}
                    </p>
                  )}
                  {accion.href ? (
                    <Link href={accion.href} onClick={() => setAbierto(false)} className={clases}>
                      {accion.icono}
                      {accion.etiqueta}
                    </Link>
                  ) : (
                    <button
                      onClick={() => { setAbierto(false); accion.onClick?.() }}
                      className={clases}
                    >
                      {accion.icono}
                      {accion.etiqueta}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
