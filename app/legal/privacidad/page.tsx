'use client'

import { LegalPageLayout, useDatosLegales } from '@/components/legal/LegalPageLayout'

export default function PrivacidadPage() {
  const { titular, email_contacto, dominio } = useDatosLegales()

  return (
    <LegalPageLayout titulo="Política de Privacidad" ultimaActualizacion="4 de agosto de 2026">
      <h2>Responsable del tratamiento</h2>
      <ul>
        <li><strong>Titular:</strong> {titular}</li>
        <li><strong>Correo de contacto:</strong> {email_contacto}</li>
        <li><strong>Web:</strong> {dominio}</li>
      </ul>

      <h2>Qué datos tratamos</h2>
      <ul>
        <li>
          <strong>Cuenta:</strong> nombre de usuario y contraseña (guardada cifrada, nunca en
          claro), o email, nombre y foto de perfil si te registras con Google o Apple.
        </li>
        <li>
          <strong>Contenido que introduces:</strong> productos de tu inventario, listas de la
          compra, hogares y las personas con las que los compartes.
        </li>
        <li>
          <strong>Fotos de tickets:</strong> las imágenes de tickets de compra que subes para el
          escaneo automático de artículos.
        </li>
        <li>
          <strong>Preferencias:</strong> idioma, tema (claro/oscuro) y otras opciones de la
          aplicación.
        </li>
      </ul>

      <h2>Con qué finalidad</h2>
      <p>
        Usamos estos datos exclusivamente para prestarte el servicio: autenticarte, guardar tu
        inventario y listas, permitirte compartir un hogar con otras personas y reconocer
        automáticamente los artículos de tus tickets fotografiados.
      </p>

      <h2>Base legal</h2>
      <p>
        La ejecución del servicio que solicitas al crear una cuenta (art. 6.1.b RGPD) y, cuando
        inicias sesión con Google o Apple o marcas la casilla de aceptación al registrarte, tu
        consentimiento expreso (art. 6.1.a RGPD).
      </p>

      <h2>Con quién compartimos tus datos</h2>
      <p>Dreame! no vende ni cede tus datos a terceros con fines comerciales. Sí recurre a estos encargados del tratamiento, imprescindibles para el funcionamiento del servicio:</p>
      <ul>
        <li>
          <strong>Google LLC:</strong> si inicias sesión con Google, y para el escaneo automático
          de tickets (API de Gemini), a la que se envía la foto del ticket para extraer los
          artículos. Al ser una empresa estadounidense, esto implica una transferencia
          internacional de datos, amparada en las Cláusulas Contractuales Tipo de la Comisión
          Europea.
        </li>
        <li><strong>Apple Inc.:</strong> únicamente si inicias sesión con "Continuar con Apple".</li>
      </ul>

      <h2>Cuánto tiempo conservamos tus datos</h2>
      <p>
        Mientras tu cuenta permanezca activa. Puedes eliminarla en cualquier momento desde
        Ajustes → Eliminar cuenta: al hacerlo se borran de forma permanente tu perfil, tu
        inventario, tus listas y las fotos de tickets asociadas.
      </p>

      <h2>Tus derechos</h2>
      <p>
        Puedes ejercer en cualquier momento tus derechos de acceso, rectificación, supresión,
        portabilidad, oposición y limitación del tratamiento escribiendo a {email_contacto}, o
        eliminando tu propia cuenta directamente desde la aplicación. También puedes reclamar ante
        la Agencia Española de Protección de Datos (www.aepd.es) si consideras que tus derechos no
        se han respetado.
      </p>

      <h2>Seguridad</h2>
      <p>
        Las contraseñas se almacenan cifradas (nunca en texto plano), la conexión se realiza por
        HTTPS y ofrecemos verificación en dos pasos por correo electrónico de forma opcional.
      </p>

      <h2>Menores de edad</h2>
      <p>
        Dreame! no está dirigida a menores de 14 años. Si detectamos una cuenta creada por un
        menor sin el consentimiento de sus tutores, la eliminaremos.
      </p>

      <h2>Cambios en esta política</h2>
      <p>
        Si actualizamos esta política de forma sustancial, te lo notificaremos dentro de la
        aplicación y te pediremos que la aceptes de nuevo antes de seguir usando el servicio.
      </p>
    </LegalPageLayout>
  )
}
