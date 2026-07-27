'use client'

import { TranslationProvider } from '@/contexts/TranslationContext'
import { ListPreferencesProvider } from '@/contexts/ListPreferencesContext'
import { useCacheBuster } from '@/lib/useCacheBuster'

export default function RootLayoutClient({ children }: { children: React.ReactNode }) {
  useCacheBuster()

  return (
    <TranslationProvider>
      <ListPreferencesProvider>{children}</ListPreferencesProvider>
    </TranslationProvider>
  )
}
