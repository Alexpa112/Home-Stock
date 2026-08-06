'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { legal } from '@/lib/api'

export interface DatosLegales {
  titular: string
  email_contacto: string
  dominio: string
}

// Valores de respaldo si /api/legal/config no responde (p.ej. página abierta
// sin backend disponible): deben coincidir con stockhogar/config.py.
const DATOS_LEGALES_RESPALDO: DatosLegales = {
  titular: 'Alejandro Paz Silva',
  email_contacto: 'pazsilva.alejandro@gmail.com',
  dominio: 'dreame.dpdns.org',
}

export function useDatosLegales(): DatosLegales {
  const [datos, setDatos] = useState<DatosLegales>(DATOS_LEGALES_RESPALDO)

  useEffect(() => {
    legal
      .configuracion()
      .then((d) => setDatos(d))
      .catch(() => {})
  }, [])

  return datos
}

interface LegalPageLayoutProps {
  titulo: string
  ultimaActualizacion: string
  children: React.ReactNode
}

// Estilos de tipografia via selectores de descendiente (sin plugin
// @tailwindcss/typography en este proyecto): mismos tokens de color que el
// resto de la app (text-foreground / text-muted-foreground / border-border).
export function LegalPageLayout({ titulo, ultimaActualizacion, children }: LegalPageLayoutProps) {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-2xl mx-auto px-4 py-8 sm:py-12">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Volver
        </Link>

        <h1 className="text-2xl font-semibold tracking-tight mb-1">{titulo}</h1>
        <p className="text-xs text-muted-foreground mb-8">Última actualización: {ultimaActualizacion}</p>

        <div
          className="space-y-4 text-sm leading-relaxed text-muted-foreground
            [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-foreground [&_h2]:mt-7 [&_h2]:mb-2
            [&_p]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5
            [&_strong]:text-foreground [&_strong]:font-medium
            [&_a]:text-accent [&_a]:hover:underline"
        >
          {children}
        </div>
      </div>
    </main>
  )
}
