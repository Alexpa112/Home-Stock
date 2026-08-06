/**
 * jest.config.lib.js corre estos tests con testEnvironment: 'node', sin
 * jsdom, asi que window/localStorage no existen por defecto (igual que en
 * un entorno de build/SSR) - se simulan a mano para poder probar las ramas
 * que dependen de ellos.
 */
import { setCached, getCached, clearAllCache } from '../dataCache'

/**
 * Fake minimo de localStorage: las entradas son propiedades propias
 * enumerables del propio objeto, asi que Object.keys(localStorage) se
 * comporta igual que en un navegador real sin tener que parchear globales
 * de Node.
 */
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

describe('clearAllCache', () => {
  afterEach(() => {
    delete (global as any).window
    delete (global as any).localStorage
  })

  it('borra las claves cacheadas de memoria y de localStorage', () => {
    ;(global as any).window = {}
    const almacen = new LocalStorageFalso()
    ;(global as any).localStorage = almacen

    setCached('stock:productos', { foo: 'bar' })
    expect(getCached('stock:productos')).toEqual({ foo: 'bar' })
    expect(Object.keys(almacen)).toContain('sh-cache:stock:productos')

    clearAllCache()

    expect(getCached('stock:productos')).toBeUndefined()
    expect(almacen.getItem('sh-cache:stock:productos')).toBeNull()
  })

  it('no lanza si no hay window (entorno de build/SSR)', () => {
    expect(() => clearAllCache()).not.toThrow()
  })
})
