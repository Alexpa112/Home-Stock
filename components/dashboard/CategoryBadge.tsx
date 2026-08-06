'use client'

import { IconRenderer } from './IconRenderer'

// Paleta fija para categorías predefinidas; para el resto se genera un color
// determinista a partir del nombre para que sea consistente entre renders.
export const CATEGORY_STYLES: Record<string, string> = {
  Alimentos:  'bg-orange-100  text-orange-800  dark:bg-orange-900/40  dark:text-orange-300',
  Bebidas:    'bg-blue-100    text-blue-800    dark:bg-blue-900/40    dark:text-blue-300',
  Limpieza:   'bg-violet-100  text-violet-800  dark:bg-violet-900/40  dark:text-violet-300',
  Higiene:    'bg-pink-100    text-pink-800    dark:bg-pink-900/40    dark:text-pink-300',
  Mascotas:   'bg-amber-100   text-amber-800   dark:bg-amber-900/40   dark:text-amber-300',
  Electrónica:'bg-cyan-100    text-cyan-800    dark:bg-cyan-900/40    dark:text-cyan-300',
  Otros:      'bg-muted       text-muted-foreground',
}

// Paleta de fallback para categorías personalizadas (rotación por hash)
export const FALLBACK_PALETTES = [
  'bg-teal-100   text-teal-800   dark:bg-teal-900/40   dark:text-teal-300',
  'bg-rose-100   text-rose-800   dark:bg-rose-900/40   dark:text-rose-300',
  'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
  'bg-lime-100   text-lime-800   dark:bg-lime-900/40   dark:text-lime-300',
  'bg-sky-100    text-sky-800    dark:bg-sky-900/40    dark:text-sky-300',
]

export function hashIndex(str: string, len: number) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0
  return h % len
}

// Mismo criterio que CATEGORY_STYLES/FALLBACK_PALETTES de arriba (misma
// categoría → mismo color en toda la app), pero en degradado sólido para
// usarse como fondo de una ficha entera (vista grid de la compra) en vez de
// como texto de una insignia pequeña.
const CATEGORY_TILE_GRADIENTS: Record<string, string> = {
  Alimentos: 'from-orange-400 to-orange-600',
  Bebidas: 'from-blue-400 to-blue-600',
  Limpieza: 'from-violet-400 to-violet-600',
  Higiene: 'from-pink-400 to-pink-600',
  Mascotas: 'from-amber-400 to-amber-600',
  Electrónica: 'from-cyan-400 to-cyan-600',
  Otros: 'from-slate-400 to-slate-600',
}

const FALLBACK_TILE_GRADIENTS = [
  'from-teal-400 to-teal-600',
  'from-rose-400 to-rose-600',
  'from-indigo-400 to-indigo-600',
  'from-lime-500 to-lime-700',
  'from-sky-400 to-sky-600',
]

export function getCategoryTileGradient(category: string): string {
  return CATEGORY_TILE_GRADIENTS[category]
    ?? FALLBACK_TILE_GRADIENTS[hashIndex(category, FALLBACK_TILE_GRADIENTS.length)]
}

interface CategoryBadgeProps {
  category: string
  icon?: string | null
}

export function CategoryBadge({ category, icon }: CategoryBadgeProps) {
  const cls = CATEGORY_STYLES[category]
    ?? FALLBACK_PALETTES[hashIndex(category, FALLBACK_PALETTES.length)]

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md ${cls}`}>
      {icon && <IconRenderer name={icon} className="w-3 h-3" />}
      {category}
    </span>
  )
}
