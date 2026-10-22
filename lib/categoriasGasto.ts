/**
 * Nombre a mostrar de una categoria de gasto.
 *
 * Las categorias por defecto se guardan en espanol (stockhogar/config.py,
 * CATEGORIAS_GASTO_DEFECTO) y ese nombre es el valor que se envia al backend,
 * asi que no se cambia: solo se traduce al pintarlo. Una categoria propia del
 * usuario (o cualquier otro nombre) se muestra tal cual.
 */
export function nombreCategoriaGasto(nombre: string, t: (clave: string) => string): string {
  switch (nombre) {
    case 'Alimentación': return t('catgasto_alimentacion')
    case 'Transporte': return t('catgasto_transporte')
    case 'Vivienda': return t('catgasto_vivienda')
    case 'Ocio': return t('catgasto_ocio')
    case 'Salud': return t('catgasto_salud')
    case 'Suministros': return t('catgasto_suministros')
    case 'Otros': return t('catgasto_otros')
    default: return nombre
  }
}
