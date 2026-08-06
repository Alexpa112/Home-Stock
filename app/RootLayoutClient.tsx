'use client'

import { useEffect, useState } from 'react'
import { TranslationProvider } from '@/contexts/TranslationContext'
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
        <OfflineBanner />
        <MantenimientoGate>{children}</MantenimientoGate>
      </ListPreferencesProvider>
    </TranslationProvider>
  )
}
