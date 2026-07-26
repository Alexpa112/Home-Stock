'use client'

import { TranslationProvider } from '@/contexts/TranslationContext'

export default function RootLayoutClient({ children }: { children: React.ReactNode }) {
  return <TranslationProvider>{children}</TranslationProvider>
}
