'use client'

import { useEffect, useState } from 'react'
import { TranslationProvider } from '@/contexts/TranslationContext'
import { ListPreferencesProvider } from '@/contexts/ListPreferencesContext'
import { useCacheBuster } from '@/lib/useCacheBuster'
import { useMantenimientoStream } from '@/lib/useMantenimientoStream'
import { mantenimientoActivo, suscribirMantenimiento } from '@/lib/mantenimiento'
import MaintenancePage from '@/components/MaintenancePage'

function MantenimientoGate({ children }: { children: React.ReactNode }) {
  const [activo, setActivo] = useState(mantenimientoActivo)
  useMantenimientoStream()

  useEffect(() => suscribirMantenimiento(setActivo), [])

  if (activo) return <MaintenancePage />
  return <>{children}</>
}

export default function RootLayoutClient({ children }: { children: React.ReactNode }) {
  useCacheBuster()

  return (
    <TranslationProvider>
      <ListPreferencesProvider>
        <MantenimientoGate>{children}</MantenimientoGate>
      </ListPreferencesProvider>
    </TranslationProvider>
  )
}
