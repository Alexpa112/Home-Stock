// Reduccion de fotos grandes ANTES de subirlas al escaner de tickets.
//
// Una foto de un movil actual (48-50 MP, o HEIC/JPEG de alta calidad) pesa
// 10-20 MB y el servidor rechaza todo lo que pase de 10 MB: el usuario veia
// "Archivo demasiado grande" sin poder hacer nada. El backend reescala a 2000 px
// de ancho para el OCR de todos modos, asi que mandar 50 MP solo gasta datos.

// Por encima de este peso se intenta reducir; por debajo, se sube tal cual.
export const UMBRAL_REDUCIR_BYTES = 3 * 1024 * 1024
// Tope de megapixeles tras reducir. Se limita por AREA y no por lado mayor: un
// ticket largo y estrecho (1500x6000) no debe perder anchura util de texto.
export const MAX_PIXELES = 8_000_000
export const CALIDAD_JPEG = 0.88

const TIPOS_REDUCIBLES = /^image\/(jpeg|jpg|png|webp|bmp|gif)$/i

export function debeReducirse(tipo: string, bytes: number): boolean {
  return TIPOS_REDUCIBLES.test(tipo) && bytes > UMBRAL_REDUCIR_BYTES
}

export function dimensionesObjetivo(
  ancho: number,
  alto: number,
  maxPixeles = MAX_PIXELES,
): { ancho: number; alto: number } {
  const pixeles = ancho * alto
  if (pixeles <= maxPixeles) return { ancho, alto }
  const k = Math.sqrt(maxPixeles / pixeles)
  return { ancho: Math.round(ancho * k), alto: Math.round(alto * k) }
}

// Devuelve un JPEG reducido, o el archivo original si no hace falta, si el
// navegador no puede (sin createImageBitmap/canvas) o si el resultado no pesa
// menos. Nunca lanza: reducir es una optimizacion, no un requisito.
export async function prepararFotoParaSubida(archivo: File): Promise<File> {
  if (!debeReducirse(archivo.type, archivo.size)) return archivo
  if (typeof createImageBitmap !== 'function' || typeof document === 'undefined') return archivo
  try {
    // 'from-image' aplica la orientacion EXIF: el canvas ya sale derecho.
    const bitmap = await createImageBitmap(archivo, { imageOrientation: 'from-image' })
    const { ancho, alto } = dimensionesObjetivo(bitmap.width, bitmap.height)
    const lienzo = document.createElement('canvas')
    lienzo.width = ancho
    lienzo.height = alto
    const ctx = lienzo.getContext('2d')
    if (!ctx) {
      bitmap.close?.()
      return archivo
    }
    ctx.drawImage(bitmap, 0, 0, ancho, alto)
    bitmap.close?.()
    const blob = await new Promise<Blob | null>((resolver) => lienzo.toBlob(resolver, 'image/jpeg', CALIDAD_JPEG))
    if (!blob || blob.size >= archivo.size) return archivo
    const nombre = archivo.name.replace(/\.[^.]+$/, '') || 'ticket'
    return new File([blob], `${nombre}.jpg`, { type: 'image/jpeg', lastModified: Date.now() })
  } catch {
    return archivo
  }
}
