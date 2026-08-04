'use client'

import { LegalPageLayout, useDatosLegales } from '@/components/legal/LegalPageLayout'

export default function AvisoLegalPage() {
  const { titular, email_contacto, dominio } = useDatosLegales()

  return (
    <LegalPageLayout titulo="Aviso Legal" ultimaActualizacion="4 de agosto de 2026">
      <p>
        En cumplimiento del artículo 10 de la Ley 34/2002, de 11 de julio, de Servicios de la
        Sociedad de la Información y de Comercio Electrónico (LSSI-CE), se informa de los
        siguientes datos del titular de esta aplicación:
      </p>

      <h2>Titular</h2>
      <ul>
        <li><strong>Nombre:</strong> {titular}</li>
        <li><strong>Naturaleza:</strong> persona física, proyecto personal sin actividad mercantil</li>
        <li><strong>Correo de contacto:</strong> {email_contacto}</li>
        <li><strong>Dominio:</strong> {dominio}</li>
      </ul>

      <h2>Objeto</h2>
      <p>
        Dreame! es una aplicación web y PWA de uso personal/doméstico para gestionar el
        inventario de un hogar, listas de la compra y su reconocimiento automático a partir de
        fotos de tickets de compra. Es un servicio gratuito, sin publicidad ni cobros de ningún
        tipo.
      </p>

      <h2>Condiciones de uso</h2>
      <p>
        El acceso y uso de Dreame! implica la aceptación de los <a href="/legal/terminos">Términos
        y Condiciones</a> y de la <a href="/legal/privacidad">Política de Privacidad</a>, que
        forman parte de este Aviso Legal.
      </p>

      <h2>Propiedad intelectual</h2>
      <p>
        El código, el diseño y la marca "Dreame!" son propiedad de {titular}. No está permitida su
        reproducción, distribución o modificación sin autorización previa, salvo lo que
        expresamente permita la licencia del código si este se publica como software libre.
      </p>

      <h2>Legislación aplicable</h2>
      <p>
        Estas condiciones se rigen por la legislación española. Para cualquier controversia que no
        pueda resolverse amistosamente, serán competentes los juzgados y tribunales que
        correspondan conforme a la normativa de protección de personas consumidoras.
      </p>
    </LegalPageLayout>
  )
}
