'use client'

import { Search, X } from 'lucide-react'
import { useTranslation } from '@/contexts/TranslationContext'

interface SearchBarProps {
  placeholder?: string
  value: string
  onChange: (value: string) => void
  onClear?: () => void
}

export function SearchBar({
  placeholder,
  value,
  onChange,
  onClear,
}: SearchBarProps) {
  const { t } = useTranslation()
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
      <input
        type="search"
        placeholder={placeholder ?? t('buscar_generico')}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input-field pl-10 pr-10"
        inputMode="search"
      />
      {value && (
        <button
          onClick={() => {
            onChange('')
            onClear?.()
          }}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-muted rounded transition-colors"
          aria-label={t('limpiar_busqueda')}
        >
          <X className="w-5 h-5 text-muted-foreground" />
        </button>
      )}
    </div>
  )
}
