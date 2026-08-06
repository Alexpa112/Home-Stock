'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { CheckCircle2, AlertCircle, Loader } from 'lucide-react'
import { auth } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

export default function RestablecerPasswordPage() {
  const params = useParams<{ token: string }>()
  const router = useRouter()
  const { t } = useTranslation()
  const [passwordNueva, setPasswordNueva] = useState('')
  const [passwordConfirmacion, setPasswordConfirmacion] = useState('')
  const [estado, setEstado] = useState<'formulario' | 'enviando' | 'ok' | 'error'>('formulario')
  const [mensaje, setMensaje] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (passwordNueva !== passwordConfirmacion) {
      setMensaje(t('error_contrasenas_no_coinciden'))
      setEstado('error')
      return
    }
    if (passwordNueva.length < 10) {
      setMensaje(t('err_password_min_8'))
      setEstado('error')
      return
    }
    setEstado('enviando')
    try {
      await auth.restablecerPassword(params.token, passwordNueva)
      setMensaje(t('password_restablecida_ok'))
      setEstado('ok')
      setTimeout(() => router.push('/'), 1500)
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : t('err_token_invalido'))
      setEstado('error')
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
      <div className="max-w-sm w-full space-y-4">
        <h1 className="text-xl font-semibold text-center">{t('titulo_restablecer_password')}</h1>

        {estado === 'enviando' && (
          <div className="text-center space-y-2">
            <Loader className="w-8 h-8 mx-auto animate-spin text-accent" />
            <p>{t('restableciendo_password')}</p>
          </div>
        )}

        {estado === 'ok' && (
          <div className="text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 mx-auto text-green-500" />
            <p>{mensaje}</p>
          </div>
        )}

        {(estado === 'formulario' || estado === 'error') && (
          <form onSubmit={handleSubmit} className="space-y-3">
            <input
              type="password"
              placeholder={t('placeholder_password_nueva')}
              value={passwordNueva}
              onChange={(e) => setPasswordNueva(e.target.value)}
              className="input-field"
              required
            />
            <input
              type="password"
              placeholder={t('placeholder_password_confirmacion')}
              value={passwordConfirmacion}
              onChange={(e) => setPasswordConfirmacion(e.target.value)}
              className="input-field"
              required
            />
            {estado === 'error' && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200 flex gap-2 items-start">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /> <span>{mensaje}</span>
              </div>
            )}
            <button type="submit" className="btn-primary w-full">
              {t('btn_restablecer_password')}
            </button>
          </form>
        )}
      </div>
    </main>
  )
}
