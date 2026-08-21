'use client'

import { LegalPageLayout, useDatosLegales } from '@/components/legal/LegalPageLayout'

export default function TerminosPage() {
  const { titular, email_contacto } = useDatosLegales()

  return (
    <LegalPageLayout titulo="Términos y Condiciones" ultimaActualizacion="4 de agosto de 2026">
      <h2>1. Objeto y aceptación</h2>
      <p>
        Estos términos regulan el uso de Dreame!, aplicación de gestión de inventario del hogar y
        listas de la compra ofrecida por {titular}. Al crear una cuenta o usar la aplicación
        aceptas íntegramente estos términos y la <a href="/legal/privacidad">Política de
        Privacidad</a>.
      </p>

      <h2>2. Descripción del servicio</h2>
      <p>
        Dreame! permite llevar el inventario de productos de tu hogar, gestionar listas de la
        compra, compartir esa información con otras personas de tu confianza y escanear tickets de
        compra para añadir artículos automáticamente mediante reconocimiento de imagen.
      </p>

      <h2>3. Registro y cuenta de usuario</h2>
      <p>
        Debes tener al menos 14 años para crear una cuenta. Eres responsable de mantener la
        confidencialidad de tu contraseña y de toda actividad realizada desde tu cuenta. Avísanos
        a {email_contacto} si sospechas un uso no autorizado.
      </p>

      <h2>4. Uso correcto del servicio</h2>
      <p>
        No debes usar Dreame! para fines ilícitos, ni subir contenido (incluidas fotos de tickets)
        del que no tengas derecho a disponer, ni intentar acceder a cuentas o hogares que no sean
        tuyos.
      </p>

      <h2>5. Hogares compartidos</h2>
      <p>
        Al invitar a otra persona a un hogar, esa persona podrá ver y, según el permiso que le
        concedas, editar el inventario y las listas de ese hogar. Eres responsable de a quién
        invitas y del nivel de acceso que le otorgas.
      </p>

      <h2>6. Gratuidad y disponibilidad</h2>
      <p>
        Dreame! es un servicio gratuito, sin publicidad ni pagos. Se presta «tal cual», sin
        garantizar una disponibilidad ininterrumpida: puede haber paradas por mantenimiento o
        causas ajenas a nuestro control.
      </p>

      <h2>7. Propiedad intelectual</h2>
      <p>
        El código, el diseño y la marca «Dreame!» pertenecen a {titular}. El contenido que tú
        introduces (productos, listas, fotos de tickets) sigue siendo tuyo; nos autorizas a
        tratarlo únicamente para prestarte el servicio.
      </p>

      <h2>8. Limitación de responsabilidad</h2>
      <p>
        El reconocimiento automático de tickets es una ayuda basada en inteligencia artificial y
        puede contener errores: revisa siempre los artículos detectados antes de confirmarlos. No
        garantizamos la exactitud de ese reconocimiento ni nos hacemos responsables de decisiones
        tomadas exclusivamente en base a él.
      </p>

      <h2>9. Baja del servicio</h2>
      <p>
        Puedes eliminar tu cuenta en cualquier momento desde Ajustes. Podemos suspender o eliminar
        cuentas que incumplan estos términos.
      </p>

      <h2>10. Modificación de estos términos</h2>
      <p>
        Si cambiamos estos términos de forma sustancial, te lo notificaremos dentro de la
        aplicación y deberás aceptarlos de nuevo antes de continuar usando el servicio.
      </p>

      <h2>11. Ley aplicable</h2>
      <p>
        Estos términos se rigen por la legislación española. Si eres consumidor, cualquier
        controversia se resolverá ante los juzgados y tribunales de tu domicilio.
      </p>
    </LegalPageLayout>
  )
}
