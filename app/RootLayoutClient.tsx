'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { TranslationProvider, useTranslation } from '@/contexts/TranslationContext'
import { ListPreferencesProvider } from '@/contexts/ListPreferencesContext'
import { useCacheBuster } from '@/lib/useCacheBuster'
import { useMantenimientoStream } from '@/lib/useMantenimientoStream'
import { mantenimientoActivo, suscribirMantenimiento } from '@/lib/mantenimiento'
import MaintenancePage from '@/components/MaintenancePage'
import { OfflineBanner } from '@/components/shared/OfflineBanner'

function MantenimientoGate({ children }: { children: React.ReactNode }) {
  const [activo, setActivo] = useState(mantenimientoActivo)
  useMantenimientoStream()

  useEffect(() => suscribirMantenimiento(setActivo), [])

  if (activo) return <MaintenancePage />
  return <>{children}</>
}

// El <title> de metadata (app/layout.tsx) es fijo y en espanol; aqui se sustituye
// por el del idioma activo. Se reaplica al navegar porque Next vuelve a escribir
// el titulo de metadata en cada cambio de ruta.
function TituloPestana() {
  const { t } = useTranslation()
  const ruta = usePathname()

  useEffect(() => {
    document.title = t('titulo_pestana')
  }, [t, ruta])

  return null
}

export default function RootLayoutClient({ children }: { children: React.ReactNode }) {
  useCacheBuster()

  // Registro del service worker (P-01/P-02): se hace aqui, no solo al
  // activar notificaciones push, para que el modo offline funcione aunque
  // el usuario nunca las active. Silencioso si el navegador no lo soporta.
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {})
    }
  }, [])

  return (
    <TranslationProvider>
      <ListPreferencesProvider>
        <TituloPestana />
        <OfflineBanner />
        <MantenimientoGate>{children}</MantenimientoGate>
      </ListPreferencesProvider>
    </TranslationProvider>
  )
}
