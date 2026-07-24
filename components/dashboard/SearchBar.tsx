'use client'

import { Search, X } from 'lucide-react'

interface SearchBarProps {
  placeholder?: string
  value: string
  onChange: (value: string) => void
  onClear?: () => void
}

export function SearchBar({
  placeholder = 'Buscar...',
  value,
  onChange,
  onClear,
}: SearchBarProps) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
      <input
        type="search"
        placeholder={placeholder}
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
          className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted transition-colors"
          aria-label="Limpiar búsqueda"
        >
          <X className="w-5 h-5 text-muted-foreground" />
        </button>
      )}
    </div>
  )
}
