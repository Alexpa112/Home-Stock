'use client'

import { TranslationProvider } from '@/contexts/TranslationContext'
import { ListPreferencesProvider } from '@/contexts/ListPreferencesContext'

export default function RootLayoutClient({ children }: { children: React.ReactNode }) {
  return (
    <TranslationProvider>
      <ListPreferencesProvider>{children}</ListPreferencesProvider>
    </TranslationProvider>
  )
}
