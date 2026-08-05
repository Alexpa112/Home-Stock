'use client'

import { WifiOff } from 'lucide-react'
import { useOnlineStatus } from '@/lib/useOnlineStatus'
import { useTranslation } from '@/contexts/TranslationContext'

/** Aviso persistente cuando no hay conexion (P-02): los datos que se vean
 * mientras tanto son los ultimos guardados (lib/dataCache.ts) o la ultima
 * pagina cacheada por el service worker, no necesariamente actuales. */
export function OfflineBanner() {
  const online = useOnlineStatus()
  const { t } = useTranslation()

  if (online) return null

  return (
    <div className="fixed top-0 inset-x-0 z-[60] bg-amber-500 text-amber-950 text-xs font-medium py-1.5 px-4 flex items-center justify-center gap-1.5 safe-area-pt">
      <WifiOff className="w-3.5 h-3.5 shrink-0" />
      <span>{t('sin_conexion_aviso')}</span>
    </div>
  )
}
