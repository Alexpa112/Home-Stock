'use client'

import { memo } from 'react'
import * as LucideIcons from 'lucide-react'
import * as HeroIcons from '@heroicons/react/24/solid'

interface IconRendererProps {
  name?: string | null
  className?: string
}

function IconRendererBase({ name, className = 'w-4 h-4' }: IconRendererProps) {
  if (!name) return null

  const iconName = String(name).trim()

  // Heroicons (prefijo "h-")
  if (iconName.startsWith('h-')) {
    const heroName = iconName.substring(2)
    const heroNamePascal = heroName
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join('')
    const HeroIcon = (HeroIcons as any)[heroNamePascal]
    if (HeroIcon) {
      return <HeroIcon className={className} />
    }
  }

  // Lucide icons
  const lucideName = iconName
    .split('-')
    .map((word, i) => {
      if (word === '') return ''
      return word.charAt(0).toUpperCase() + word.slice(1)
    })
    .join('')

  const LucideIcon = (LucideIcons as any)[lucideName]
  if (LucideIcon) {
    return <LucideIcon className={className} />
  }

  // Fallback: no se encontró el icono
  return null
}

// Las listas de stock y de la compra repintan todas sus filas en cada
// pulsación; con memo, resolver el nombre del icono (dos búsquedas de string
// + lookup en los namespaces de lucide/heroicons) solo se paga cuando el
// icono o su clase cambian de verdad.
export const IconRenderer = memo(IconRendererBase)
