/**
 * Traduce un error de la activacion de notificaciones push a una CLAVE de
 * traduccion (la UI pinta t(error)).
 *
 * Los errores propios y los del backend ya son claves. Los de las Web APIs
 * (DOMException de pushManager.subscribe) llegan en el idioma del navegador;
 * antes todos acababan como "err_conexion_servidor" ("error de conexion"), que
 * en iOS despistaba: alli subscribe() falla con NotAllowedError cuando el
 * sistema no lo permite (app sin instalar en la pantalla de inicio, iOS < 16.4
 * o llamada fuera del gesto del usuario), y no es un problema de red.
 */
export function claveErrorPush(err: unknown, permiso?: NotificationPermission): string {
  const mensaje = err instanceof Error ? err.message : ''
  if (/^[a-z0-9_]+$/.test(mensaje)) return mensaje

  const nombre = typeof err === 'object' && err !== null && 'name' in err ? String((err as { name: unknown }).name) : ''
  if (nombre === 'NotAllowedError') {
    return permiso === 'denied' ? 'permiso_notificaciones_denegado' : 'err_push_no_permitido'
  }
  if (['AbortError', 'InvalidStateError', 'InvalidAccessError', 'NotSupportedError', 'SecurityError'].includes(nombre)) {
    return 'err_push_fallo_suscripcion'
  }
  return 'err_conexion_servidor'
}
