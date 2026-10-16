'use client'

import { AlertCircle } from 'lucide-react'
import { useTranslation } from '@/contexts/TranslationContext'

interface AvisoErrorProps {
  /** Texto del error; si esta vacio no se pinta nada. */
  mensaje?: string | null
  /** Con titulo ("Error") encima del mensaje, como en las pantallas de listas. */
  conTitulo?: boolean
}

/** Banner rojo de error de pantalla (antes copiado en cada pagina). */
export function AvisoError({ mensaje, conTitulo = false }: AvisoErrorProps) {
  const { t } = useTranslation()
  if (!mensaje) return null
  return (
    <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
      <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
      {conTitulo ? (
        <div>
          <p className="font-medium">{t('error')}</p>
          <p className="text-sm">{mensaje}</p>
        </div>
      ) : (
        <p className="text-sm">{mensaje}</p>
      )}
    </div>
  )
}
