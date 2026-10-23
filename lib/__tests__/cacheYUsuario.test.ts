/**
 * La cache de pantallas (sh-cache:*) pertenece a UN usuario: si cambia el de la sesion, o no hay
 * sesion, se borra antes de que ninguna pantalla la pinte (dispositivos compartidos).
 */
import { setCached, getCached, sincronizarCacheConUsuario } from '../dataCache'

class LocalStorageFalso {
  [clave: string]: any
  getItem(k: string) {
    return k in this && typeof this[k] === 'string' ? this[k] : null
  }
  setItem(k: string, v: string) {
    this[k] = v
  }
  removeItem(k: string) {
    delete this[k]
  }
}

describe('sincronizarCacheConUsuario', () => {
  beforeEach(() => {
    ;(global as any).window = {}
    ;(global as any).localStorage = new LocalStorageFalso()
  })
  afterEach(() => {
    delete (global as any).window
    delete (global as any).localStorage
  })

  it('el mismo usuario conserva su cache entre cargas', () => {
    sincronizarCacheConUsuario(7)
    setCached('stock:productos', [{ id: 1 }])
    sincronizarCacheConUsuario(7)
    expect(getCached('stock:productos')).toEqual([{ id: 1 }])
  })

  it('otro usuario en el mismo navegador no ve la cache del anterior', () => {
    sincronizarCacheConUsuario(7)
    setCached('gastos:lista', [{ importe: 99 }])
    sincronizarCacheConUsuario(8)
    expect(getCached('gastos:lista')).toBeUndefined()
    expect((global as any).localStorage.getItem('sh-cache-usuario')).toBe('8')
  })

  it('sin sesion (caduco la cookie) se borra todo', () => {
    sincronizarCacheConUsuario(7)
    setCached('recetas:lista', ['x'])
    sincronizarCacheConUsuario(null)
    expect(getCached('recetas:lista')).toBeUndefined()
  })

  it('la primera visita anonima tambien limpia restos de versiones anteriores', () => {
    ;(global as any).localStorage.setItem('sh-cache:viejo', JSON.stringify({ data: 'resto', timestamp: 1 }))
    sincronizarCacheConUsuario(null)
    expect((global as any).localStorage.getItem('sh-cache:viejo')).toBeNull()
  })

  it('no falla en el servidor (sin window)', () => {
    delete (global as any).window
    expect(() => sincronizarCacheConUsuario(1)).not.toThrow()
  })
})
