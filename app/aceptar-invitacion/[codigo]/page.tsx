'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { CheckCircle2, AlertCircle, Loader } from 'lucide-react'
import { permisos } from '@/lib/api'

export default function AceptarInvitacionPage() {
  const params = useParams<{ codigo: string }>()
  const router = useRouter()
  const [estado, setEstado] = useState<'cargando' | 'ok' | 'error'>('cargando')
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    // Si no hay sesion, ProtectedRoute no envuelve esta pagina (es publica en
    // Flask para poder mostrar el destino tras login); aqui simplemente se
    // intenta y, si el backend responde 401, se manda a login conservando
    // la vuelta a esta misma URL.
    const aceptar = async () => {
      try {
        const datos: any = await permisos.aceptarInvitacion(params.codigo)
        setMensaje(datos.mensaje || '¡Invitación aceptada!')
        setEstado('ok')
        setTimeout(() => router.push('/dashboard/listas'), 1500)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error aceptando la invitación'
        if (msg.toLowerCase().includes('no has iniciado sesión')) {
          window.location.href = `/?next=/aceptar-invitacion/${params.codigo}`
          return
        }
        setMensaje(msg)
        setEstado('error')
      }
    }
    aceptar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.codigo])

  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
      <div className="max-w-sm text-center space-y-4">
        {estado === 'cargando' && (
          <>
            <Loader className="w-10 h-10 mx-auto animate-spin text-accent" />
            <p>Aceptando invitación...</p>
          </>
        )}
        {estado === 'ok' && (
          <>
            <CheckCircle2 className="w-10 h-10 mx-auto text-green-500" />
            <p>{mensaje}</p>
            <p className="text-sm text-muted-foreground">Redirigiendo a tus listas...</p>
          </>
        )}
        {estado === 'error' && (
          <>
            <AlertCircle className="w-10 h-10 mx-auto text-red-500" />
            <p>{mensaje}</p>
            <a href="/dashboard" className="text-accent hover:underline text-sm">Ir al dashboard</a>
          </>
        )}
      </div>
    </main>
  )
}
