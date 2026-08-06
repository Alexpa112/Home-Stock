'use client'

import { Receipt } from 'lucide-react'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { CATEGORY_STYLES, FALLBACK_PALETTES, hashIndex } from '@/components/dashboard/CategoryBadge'

interface CategoriaIconoProps {
  categoria?: string | null
  icono?: string | null
  className?: string
}

// Opción 11A del rediseño de gastos (docs/REDISENO_GASTOS.md): el icono de la
// categoría se pinta dentro de un cuadro de color, en vez de gris plano. Usa
// el mismo criterio de color por nombre que CategoryBadge (mapa fijo para las
// categorías predefinidas, hash determinista para el resto) para que una
// categoría tenga siempre el mismo color en toda la app. Sin categoría se
// muestra un cuadro neutro con un icono genérico, para no romper la
// alineación de las tarjetas que sí tienen categoría.
export function CategoriaIcono({ categoria, icono, className = 'w-9 h-9' }: CategoriaIconoProps) {
  if (!categoria) {
    return (
      <span className={`${className} shrink-0 rounded-xl flex items-center justify-center bg-muted text-muted-foreground`}>
        <Receipt className="w-4 h-4" />
      </span>
    )
  }

  const cls = CATEGORY_STYLES[categoria] ?? FALLBACK_PALETTES[hashIndex(categoria, FALLBACK_PALETTES.length)]

  return (
    <span className={`${className} shrink-0 rounded-xl flex items-center justify-center ${cls}`}>
      <IconRenderer name={icono} className="w-4 h-4" />
    </span>
  )
}
