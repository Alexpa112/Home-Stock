'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { CheckCircle2, AlertCircle, Loader } from 'lucide-react'
import { auth } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

export default function VerificarEmailPage() {
  const params = useParams<{ token: string }>()
  const { t } = useTranslation()
  const [estado, setEstado] = useState<'cargando' | 'ok' | 'error'>('cargando')
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    const verificar = async () => {
      try {
        await auth.verificarEmail(params.token)
        setMensaje(t('email_verificado_ok'))
        setEstado('ok')
      } catch (err) {
        setMensaje(err instanceof Error ? err.message : t('err_token_invalido'))
        setEstado('error')
      }
    }
    verificar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.token])

  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
      <div className="max-w-sm text-center space-y-4">
        {estado === 'cargando' && (
          <>
            <Loader className="w-10 h-10 mx-auto animate-spin text-accent" />
            <p>{t('verificando_email')}</p>
          </>
        )}
        {estado === 'ok' && (
          <>
            <CheckCircle2 className="w-10 h-10 mx-auto text-green-500" />
            <p>{mensaje}</p>
          </>
        )}
        {estado === 'error' && (
          <>
            <AlertCircle className="w-10 h-10 mx-auto text-red-500" />
            <p>{mensaje}</p>
          </>
        )}
      </div>
    </main>
  )
}
