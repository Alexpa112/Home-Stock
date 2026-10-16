'use client'

import { IconRenderer } from '@/components/dashboard/IconRenderer'
import type { ArticuloCatalogo } from '@/lib/tipos'

interface ListaSugerenciasProps {
  sugerencias: ArticuloCatalogo[]
  onSeleccionar: (item: ArticuloCatalogo) => void
}

/** Desplegable de autocompletado bajo el campo "nombre" (stock y lista de la compra). */
export function ListaSugerencias({ sugerencias, onSeleccionar }: ListaSugerenciasProps) {
  if (sugerencias.length === 0) return null
  return (
    <ul className="absolute z-10 left-0 right-0 mt-1 bg-card border border-border rounded-xl shadow-lg overflow-hidden">
      {sugerencias.map((item) => (
        <li key={`${item.origen}-${item.nombre}`}>
          {/* onMouseDown (no onClick): el campo pierde el foco antes y ocultaria la lista. */}
          <button
            type="button"
            onMouseDown={() => onSeleccionar(item)}
            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-muted transition-colors"
          >
            {item.icono && <IconRenderer name={item.icono} className="w-4 h-4 text-muted-foreground" />}
            <span className="text-sm">{item.nombre}</span>
            {item.categoria && <span className="text-xs text-muted-foreground ml-auto">{item.categoria}</span>}
          </button>
        </li>
      ))}
    </ul>
  )
}
