'use client'

import { ReactNode } from 'react'
import { ChevronsUpDown, Home } from 'lucide-react'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { MenuAcciones, AccionMenu } from '@/components/dashboard/MenuAcciones'
import { useHogar } from '@/contexts/HogarContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { abrirSelectorHogar } from '@/lib/selectorHogar'

interface CabeceraPantallaProps {
  titulo: string
  icono?: ReactNode
  // Solo escritorio: en móvil el espacio es caro y el título basta.
  subtitulo?: ReactNode
  acciones?: AccionMenu[]
  labelAcciones?: string
  // Controles propios de la pantalla (p. ej. "Añadir" en escritorio).
  children?: ReactNode
}

// Cabecera única de las pantallas del dashboard: título + chip del hogar (solo
// móvil, abre el selector) + menú ⋯. Sustituye a la barra superior fija de 48 px
// del layout, que se repetía en todas las pantallas.
export function CabeceraPantalla({ titulo, icono, subtitulo, acciones, labelAcciones, children }: CabeceraPantallaProps) {
  const { t } = useTranslation()
  const { hogarActivoId, propios, compartidos } = useHogar()
  const hogarActivo = [...propios, ...compartidos].find((h) => h.id === hogarActivoId)

  return (
    <div className="flex items-center justify-between gap-3">
      <div>
        <h1 className="text-xl lg:text-3xl font-bold flex items-center gap-2">
          {icono}
          <span>{titulo}</span>
        </h1>
        {subtitulo && <p className="hidden lg:block text-muted-foreground mt-1">{subtitulo}</p>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {children}
        <button
          type="button"
          onClick={abrirSelectorHogar}
          aria-label={t('cambiar_hogar')}
          className="lg:hidden flex items-center gap-1.5 px-2 min-h-[44px] rounded-xl border border-border bg-card hover:bg-muted transition-colors"
        >
          <span
            className="w-5 h-5 rounded-md flex items-center justify-center shrink-0 text-white"
            style={{ backgroundColor: hogarActivo?.color || '#B5551A' }}
          >
            {hogarActivo?.icono ? <IconRenderer name={hogarActivo.icono} className="w-3 h-3" /> : <Home className="w-3 h-3" />}
          </span>
          <span className="text-xs font-semibold max-w-[5rem] truncate">{hogarActivo?.nombre}</span>
          <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
        {acciones && acciones.length > 0 && <MenuAcciones label={labelAcciones ?? t('mas_acciones')} acciones={acciones} />}
      </div>
    </div>
  )
}
