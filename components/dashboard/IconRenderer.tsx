'use client'

import * as LucideIcons from 'lucide-react'
import * as HeroIcons from '@heroicons/react/24/solid'

interface IconRendererProps {
  name?: string | null
  className?: string
}

export function IconRenderer({ name, className = 'w-4 h-4' }: IconRendererProps) {
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
