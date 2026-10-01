import { ChefHat, History } from 'lucide-react'
import type { AccionMenu } from './MenuAcciones'

// Grupo "Ir a" del menú ⋯: lleva a las dos pantallas que no tienen pestaña en
// la barra inferior. La pantalla actual no se ofrece a sí misma.
export function accionesIrA(
  t: (clave: string) => string,
  actual?: 'recetas' | 'historial',
): AccionMenu[] {
  const grupo = t('menu_ir_a')
  const acciones: AccionMenu[] = []
  if (actual !== 'recetas') {
    acciones.push({ icono: <ChefHat className="w-4 h-4" />, etiqueta: t('nav_recetas'), href: '/dashboard/recetas', grupo })
  }
  if (actual !== 'historial') {
    acciones.push({ icono: <History className="w-4 h-4" />, etiqueta: t('historial'), href: '/dashboard/historial', grupo })
  }
  return acciones
}
