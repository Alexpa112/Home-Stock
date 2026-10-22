/**
 * ¿Es `ruta` un destino interno seguro para redirigir tras el login (`?next=`)?
 *
 * Una redireccion abierta deja que un enlace de phishing a NUESTRO login mande
 * al usuario a otro sitio justo despues de autenticarse. Reglas:
 *  - empieza por una sola "/" (nada de "//host", que es una URL sin esquema);
 *  - sin barras invertidas ni caracteres de control: el analizador de URLs de los
 *    navegadores ELIMINA tabuladores y saltos de linea, asi que "/%09/evil.com"
 *    (que searchParams ya entrega decodificado como "/\t/evil.com") se convertia
 *    en "//evil.com";
 *  - y, como comprobacion final, resuelta contra un origen ficticio sigue en ese
 *    mismo origen.
 */
export function esRutaInternaSegura(ruta: unknown): ruta is string {
  if (typeof ruta !== 'string' || ruta.length === 0 || ruta.length > 2048) return false
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f-\u009f\\]/.test(ruta)) return false
  if (!ruta.startsWith('/') || ruta.startsWith('//')) return false
  if (ruta.includes('://')) return false
  try {
    const origen = 'http://origen.invalid'
    return new URL(ruta, origen).origin === origen
  } catch {
    return false
  }
}

export function destinoSeguro(ruta: string | null | undefined, porDefecto = '/dashboard'): string {
  return esRutaInternaSegura(ruta) ? ruta : porDefecto
}
