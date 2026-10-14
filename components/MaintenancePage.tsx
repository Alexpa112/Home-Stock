'use client'

import { Wrench } from 'lucide-react'
import { useTranslation } from '@/contexts/TranslationContext'

export default function MaintenancePage() {
  const { t } = useTranslation()

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <Wrench className="w-14 h-14 text-muted-foreground" aria-hidden="true" />
      <h1 className="text-2xl font-semibold text-foreground">{t('mantenimiento_titulo')}</h1>
      <p className="text-muted-foreground">{t('mantenimiento_texto')}</p>
    </div>
  )
}
