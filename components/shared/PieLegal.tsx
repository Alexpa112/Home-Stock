'use client'

import { useTranslation } from '@/contexts/TranslationContext'

/**
 * Pie con los enlaces legales de las pantallas públicas.
 *
 * Estaba escrito a mano dentro de app/page.tsx, así que el resto de pantallas
 * públicas (restablecer contraseña, verificar email) se quedaban sin él: el
 * usuario que llegaba ahí desde un correo no tenía forma de alcanzar el aviso
 * legal ni la política de privacidad.
 */
export function PieLegal({ className = '' }: { className?: string }) {
  const { t } = useTranslation()

  const enlaces = [
    { href: '/legal/aviso-legal', etiqueta: t('enlace_aviso_legal') },
    { href: '/legal/privacidad', etiqueta: t('enlace_privacidad') },
    { href: '/legal/terminos', etiqueta: t('enlace_terminos') },
    { href: '/legal/cookies', etiqueta: t('enlace_cookies') },
  ]

  return (
    <footer
      className={`pb-6 px-4 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-muted-foreground ${className}`}
    >
      {enlaces.map(({ href, etiqueta }) => (
        <a key={href} href={href} className="hover:text-foreground hover:underline">
          {etiqueta}
        </a>
      ))}
    </footer>
  )
}
