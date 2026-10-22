import { esRutaInternaSegura, destinoSeguro } from '../rutaSegura'

describe('esRutaInternaSegura', () => {
  it('acepta rutas internas normales', () => {
    for (const r of ['/dashboard', '/dashboard/shopping', '/dashboard/gastos?vista=resumen', '/a/b#ancla', '/']) {
      expect(esRutaInternaSegura(r)).toBe(true)
    }
  })

  it('rechaza URLs absolutas y sin esquema', () => {
    for (const r of ['https://evil.com', 'http://evil.com/x', '//evil.com', '//evil.com/dashboard', 'evil.com', 'javascript:alert(1)', 'data:text/html,x']) {
      expect(esRutaInternaSegura(r)).toBe(false)
    }
  })

  it('rechaza barras invertidas', () => {
    expect(esRutaInternaSegura('/\\evil.com')).toBe(false)
    expect(esRutaInternaSegura('/\\/evil.com')).toBe(false)
  })

  it('rechaza tabuladores y saltos de linea que el navegador elimina (/%09/evil.com)', () => {
    expect(esRutaInternaSegura('/\t/evil.com')).toBe(false)
    expect(esRutaInternaSegura('/\n/evil.com')).toBe(false)
    expect(esRutaInternaSegura('/\r/evil.com')).toBe(false)
    expect(esRutaInternaSegura('/\u0000/evil.com')).toBe(false)
    expect(esRutaInternaSegura('/\u0085/evil.com')).toBe(false)
  })

  it('un %09 sin decodificar es inofensivo (se queda como parte del camino)', () => {
    expect(esRutaInternaSegura('/%09/evil.com')).toBe(true)
  })

  it('rechaza esquemas escondidos en la ruta y valores raros', () => {
    expect(esRutaInternaSegura('/redir?u=https://evil.com')).toBe(false)
    expect(esRutaInternaSegura('')).toBe(false)
    expect(esRutaInternaSegura(null)).toBe(false)
    expect(esRutaInternaSegura(undefined)).toBe(false)
    expect(esRutaInternaSegura(42)).toBe(false)
    expect(esRutaInternaSegura('/' + 'a'.repeat(3000))).toBe(false)
  })
})

describe('destinoSeguro', () => {
  it('devuelve la ruta si es segura y el valor por defecto si no', () => {
    expect(destinoSeguro('/dashboard/recetas')).toBe('/dashboard/recetas')
    expect(destinoSeguro('//evil.com')).toBe('/dashboard')
    expect(destinoSeguro(null)).toBe('/dashboard')
    expect(destinoSeguro('/\t/evil.com', '/x')).toBe('/x')
  })
})
