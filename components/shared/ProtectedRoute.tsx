'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslation } from '@/contexts/TranslationContext'
import { AceptarTerminosModal } from '@/components/shared/AceptarTerminosModal'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter()
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthorized, setIsAuthorized] = useState(false)
  const [terminosPendientes, setTerminosPendientes] = useState(false)

  const checkAuth = useCallback(async () => {
    try {
      // /api/auth/estado siempre responde 200 (es publica); hay que mirar
      // el campo 'usuario' para saber si de verdad hay sesion iniciada.
      const response = await fetch('/api/auth/estado', {
        credentials: 'include',
      })
      const datos = response.ok ? await response.json() : null

      if (!response.ok || !datos?.usuario) {
        router.replace('/')
        return
      }

      // Sincronizar tema del backend con la clase CSS y localStorage
      const tema = datos.tema_preferido || 'auto'
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      const usarDark = tema === 'dark' || (tema === 'auto' && prefersDark)
      document.documentElement.classList.toggle('dark', usarDark)
      document.documentElement.classList.toggle('light', !usarDark)
      localStorage.setItem('theme', usarDark ? 'dark' : 'light')

      // Usuarios ya logueados antes de esta version de Terminos/Privacidad, o
      // que entraron por Google/Apple (no pasan por la casilla del formulario
      // de registro manual): deben aceptar antes de ver el resto de la app.
      setTerminosPendientes(Boolean(datos.terminos_pendientes))
      setIsAuthorized(true)
    } catch (error) {
      console.error('Auth check failed:', error)
      router.push('/')
    } finally {
      setIsLoading(false)
    }
  }, [router])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-muted border-t-accent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-muted-foreground">{t('cargando')}</p>
        </div>
      </div>
    )
  }

  if (!isAuthorized) {
    return null
  }

  if (terminosPendientes) {
    return <AceptarTerminosModal onAceptado={() => setTerminosPendientes(false)} />
  }

  return <>{children}</>
}
