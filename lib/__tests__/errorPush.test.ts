import { claveErrorPush } from '../errorPush'

const dom = (name: string) => Object.assign(new Error('texto del navegador'), { name })

describe('claveErrorPush', () => {
  it('conserva las claves de traduccion propias y del backend', () => {
    expect(claveErrorPush(new Error('err_push_no_disponible'))).toBe('err_push_no_disponible')
    expect(claveErrorPush(new Error('err_suscripcion_push_invalida'))).toBe('err_suscripcion_push_invalida')
  })

  it('NotAllowedError con el permiso denegado es el aviso de permiso bloqueado', () => {
    expect(claveErrorPush(dom('NotAllowedError'), 'denied')).toBe('permiso_notificaciones_denegado')
  })

  it('NotAllowedError sin permiso denegado (iOS sin instalar o fuera de gesto) no es un error de conexion', () => {
    expect(claveErrorPush(dom('NotAllowedError'), 'default')).toBe('err_push_no_permitido')
    expect(claveErrorPush(dom('NotAllowedError'), 'granted')).toBe('err_push_no_permitido')
    expect(claveErrorPush(dom('NotAllowedError'))).toBe('err_push_no_permitido')
  })

  it('los fallos de suscripcion del navegador tienen su propio aviso', () => {
    for (const nombre of ['AbortError', 'InvalidStateError', 'InvalidAccessError', 'NotSupportedError', 'SecurityError']) {
      expect(claveErrorPush(dom(nombre), 'granted')).toBe('err_push_fallo_suscripcion')
    }
  })

  it('un error de red sigue siendo error de conexion', () => {
    expect(claveErrorPush(new TypeError('Failed to fetch'))).toBe('err_conexion_servidor')
    expect(claveErrorPush('algo raro')).toBe('err_conexion_servidor')
    expect(claveErrorPush(null)).toBe('err_conexion_servidor')
  })
})
