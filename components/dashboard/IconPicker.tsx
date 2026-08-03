'use client'

import { useState } from 'react'
import { IconRenderer } from './IconRenderer'
import { SearchBar } from './SearchBar'
import { useTranslation } from '@/contexts/TranslationContext'

// Selección curada de iconos lucide-react relevantes para productos del
// hogar (alimentación, limpieza, higiene, mascotas...). IconRenderer
// convierte estos nombres kebab-case al componente PascalCase de lucide.
const ICONOS_PRODUCTO: { nombre: string; etiqueta: string }[] = [
  { nombre: 'milk', etiqueta: 'Leche' },
  { nombre: 'egg', etiqueta: 'Huevos' },
  { nombre: 'apple', etiqueta: 'Fruta' },
  { nombre: 'carrot', etiqueta: 'Verdura' },
  { nombre: 'beef', etiqueta: 'Carne' },
  { nombre: 'fish', etiqueta: 'Pescado' },
  { nombre: 'coffee', etiqueta: 'Café' },
  { nombre: 'wine', etiqueta: 'Vino' },
  { nombre: 'cookie', etiqueta: 'Galletas' },
  { nombre: 'wheat', etiqueta: 'Cereales' },
  { nombre: 'sandwich', etiqueta: 'Bocadillo' },
  { nombre: 'pizza', etiqueta: 'Pizza' },
  { nombre: 'soup', etiqueta: 'Sopa' },
  { nombre: 'candy', etiqueta: 'Dulces' },
  { nombre: 'popcorn', etiqueta: 'Snacks' },
  { nombre: 'croissant', etiqueta: 'Bollería' },
  { nombre: 'cherry', etiqueta: 'Fruta' },
  { nombre: 'citrus', etiqueta: 'Cítricos' },
  { nombre: 'drumstick', etiqueta: 'Pollo' },
  { nombre: 'chef-hat', etiqueta: 'Cocina' },
  { nombre: 'utensils-crossed', etiqueta: 'Cocina' },
  { nombre: 'shopping-basket', etiqueta: 'Compra' },
  { nombre: 'package', etiqueta: 'Genérico' },
  { nombre: 'box', etiqueta: 'Caja' },
  { nombre: 'refrigerator', etiqueta: 'Nevera' },
  { nombre: 'spray-can', etiqueta: 'Limpieza' },
  { nombre: 'trash-2', etiqueta: 'Basura' },
  { nombre: 'shirt', etiqueta: 'Ropa' },
  { nombre: 'pill', etiqueta: 'Medicina' },
  { nombre: 'syringe', etiqueta: 'Salud' },
  { nombre: 'bone', etiqueta: 'Mascotas' },
  { nombre: 'paw-print', etiqueta: 'Mascotas' },
  { nombre: 'cat', etiqueta: 'Gato' },
  { nombre: 'dog', etiqueta: 'Perro' },
  { nombre: 'lightbulb', etiqueta: 'Bombilla' },
  { nombre: 'plug', etiqueta: 'Electricidad' },
  { nombre: 'wrench', etiqueta: 'Bricolaje' },
  { nombre: 'hammer', etiqueta: 'Bricolaje' },
  { nombre: 'car', etiqueta: 'Coche' },
  { nombre: 'fuel', etiqueta: 'Gasolina' },
  { nombre: 'baby', etiqueta: 'Bebé' },
  { nombre: 'leaf', etiqueta: 'Planta' },
  { nombre: 'snowflake', etiqueta: 'Congelado' },
  { nombre: 'droplet', etiqueta: 'Líquido' },
  { nombre: 'flame', etiqueta: 'Especias' },
  { nombre: 'gift', etiqueta: 'Regalo' },
  { nombre: 'scissors', etiqueta: 'Higiene' },
  { nombre: 'palette', etiqueta: 'Manualidades' },
  { nombre: 'bath', etiqueta: 'Baño' },
  { nombre: 'home', etiqueta: 'Hogar' },
  { nombre: 'sparkles', etiqueta: 'Limpieza' },
]

interface IconPickerProps {
  valorActual: string | null | undefined
  onSeleccionar: (icono: string) => void
  onCerrar: () => void
}

export function IconPicker({ valorActual, onSeleccionar, onCerrar }: IconPickerProps) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')

  const filtrados = query.trim()
    ? ICONOS_PRODUCTO.filter((i) => i.etiqueta.toLowerCase().includes(query.trim().toLowerCase()))
    : ICONOS_PRODUCTO

  return (
    <div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center bg-black/40 p-4" onClick={onCerrar}>
      <div
        className="card w-full sm:max-w-md h-[75dvh] sm:h-auto sm:max-h-[75dvh] flex flex-col gap-3"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base">{t('elegir_icono')}</h3>
          <button type="button" onClick={onCerrar} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-muted" aria-label={t('cancelar')}>
            ✕
          </button>
        </div>

        <SearchBar placeholder={t('buscar_icono')} value={query} onChange={setQuery} />

        <div className="grid grid-cols-4 sm:grid-cols-5 gap-2 overflow-y-auto pr-1 flex-1 min-h-0 content-start">
          {filtrados.map((icono) => (
            <button
              key={icono.nombre}
              type="button"
              onClick={() => onSeleccionar(icono.nombre)}
              className={`flex flex-col items-center gap-1 p-2 rounded-xl border transition-colors ${
                valorActual === icono.nombre ? 'border-accent bg-accent/10' : 'border-border hover:bg-muted'
              }`}
            >
              <IconRenderer name={icono.nombre} className="w-5 h-5 text-foreground" />
              <span className="text-[0.65rem] text-muted-foreground leading-tight text-center line-clamp-1">{icono.etiqueta}</span>
            </button>
          ))}
          {filtrados.length === 0 && (
            <p className="col-span-full text-sm text-muted-foreground text-center py-4">{t('sin_resultados')}</p>
          )}
        </div>
      </div>
    </div>
  )
}
