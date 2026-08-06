'use client'

import { Receipt, Plus } from 'lucide-react'

interface GastosVacioProps {
  titulo: string
  descripcion: string
  textoBoton: string
  onAnadir: () => void
}

// Opción 12A del rediseño de gastos (docs/REDISENO_GASTOS.md): el estado
// vacío deja de ser un párrafo gris suelto y ofrece la acción de alta
// directamente, explicando en una frase el valor de la función.
export function GastosVacio({ titulo, descripcion, textoBoton, onAnadir }: GastosVacioProps) {
  return (
    <div className="card flex flex-col items-center text-center gap-3 py-10">
      <span className="w-14 h-14 rounded-2xl bg-muted text-muted-foreground flex items-center justify-center">
        <Receipt className="w-6 h-6" />
      </span>
      <div className="space-y-1">
        <p className="font-semibold text-foreground">{titulo}</p>
        <p className="text-sm text-muted-foreground max-w-xs">{descripcion}</p>
      </div>
      <button onClick={onAnadir} className="btn-primary flex items-center gap-2 mt-1">
        <Plus className="w-4 h-4" /> {textoBoton}
      </button>
    </div>
  )
}
