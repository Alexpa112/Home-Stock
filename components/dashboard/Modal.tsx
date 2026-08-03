'use client'

import { ReactNode } from 'react'

interface ModalProps {
  onCerrar: () => void
  children: ReactNode
}

// Modal fija centrada (abajo en móvil), igual patrón que IconPicker: así el
// formulario de alta/edición siempre queda visible sobre el viewport actual,
// sin importar en qué punto de scroll de la lista estaba el usuario al abrirlo.
export function Modal({ onCerrar, children }: ModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4" onClick={onCerrar}>
      <div
        className="card w-full sm:max-w-md max-h-[90dvh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
