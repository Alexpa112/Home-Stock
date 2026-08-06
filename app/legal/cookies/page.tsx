'use client'

import { LegalPageLayout, useDatosLegales } from '@/components/legal/LegalPageLayout'

export default function CookiesPage() {
  const { dominio } = useDatosLegales()

  return (
    <LegalPageLayout titulo="Política de Cookies" ultimaActualizacion="4 de agosto de 2026">
      <p>
        Una cookie es un pequeño archivo que un sitio web guarda en tu navegador. En {dominio} solo
        usamos una:
      </p>

      <h2>Cookie de sesión</h2>
      <ul>
        <li><strong>Nombre:</strong> session</li>
        <li><strong>Finalidad:</strong> mantenerte identificado mientras usas la aplicación, para que no tengas que iniciar sesión en cada visita.</li>
        <li><strong>Duración:</strong> hasta 365 días, o hasta que cierres sesión manualmente.</li>
        <li><strong>Tipo:</strong> técnica y propia, imprescindible para el funcionamiento de la aplicación.</li>
      </ul>

      <h2>¿Necesita tu consentimiento?</h2>
      <p>
        No. Al ser una cookie estrictamente necesaria para prestar el servicio que solicitas
        (mantener tu sesión iniciada), está exenta del deber de consentimiento previo según el
        artículo 22.2 de la LSSI y el criterio de la Agencia Española de Protección de Datos.
      </p>

      <h2>Qué NO usamos</h2>
      <p>
        Dreame! no utiliza cookies de analítica, publicidad ni de redes sociales, ni comparte
        ninguna cookie con terceros. Si en el futuro incorporásemos alguna, te lo pediríamos
        explícitamente mediante un aviso antes de activarla.
      </p>

      <h2>Cómo eliminarla</h2>
      <p>
        Puedes borrar esta cookie en cualquier momento desde la configuración de tu navegador
        (Ajustes → Privacidad y seguridad → Cookies); al hacerlo, se cerrará tu sesión y deberás
        volver a iniciarla.
      </p>
    </LegalPageLayout>
  )
}
