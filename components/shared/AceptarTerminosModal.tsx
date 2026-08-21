'use client'

import { useState } from 'react'
import { ScrollText } from 'lucide-react'
import { auth } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

interface AceptarTerminosModalProps {
  onAceptado: () => void
}

// Pantalla bloqueante (sin cierre ni click-fuera) para usuarios que ya tenían
// sesión iniciada antes de esta version de los Terminos/Privacidad, o que
// entraron por Google y por tanto nunca pasaron por la casilla de
// aceptacion del formulario de registro manual (ver app/page.tsx).
export function AceptarTerminosModal({ onAceptado }: AceptarTerminosModalProps) {
  const { t } = useTranslation()
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  const handleAceptar = async () => {
    setCargando(true)
    setError('')
    try {
      await auth.aceptarTerminos()
      onAceptado()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_conexion_servidor'))
      setCargando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4">
      <div className="card max-w-sm w-full">
        <div className="flex justify-center mb-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10">
            <ScrollText className="h-6 w-6 text-accent" />
          </div>
        </div>
        <h2 className="text-lg font-semibold text-center text-foreground mb-2">{t('modal_terminos_titulo')}</h2>
        <p className="text-sm text-muted-foreground text-center mb-4">{t('modal_terminos_texto')}</p>

        <div className="flex items-center justify-center gap-3 text-xs mb-4">
          <a href="/legal/terminos" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
            {t('enlace_terminos')}
          </a>
          <a href="/legal/privacidad" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
            {t('enlace_privacidad')}
          </a>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200 mb-4">
            {error}
          </div>
        )}

        <button onClick={handleAceptar} disabled={cargando} className="btn-primary w-full">
          {cargando ? t('procesando') : t('btn_acepto_continuar')}
        </button>
      </div>
    </div>
  )
}
