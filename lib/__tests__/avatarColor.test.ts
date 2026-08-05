import { colorAvatar, inicialesAvatar } from '../avatarColor'

describe('colorAvatar', () => {
  it('es determinista: el mismo nombre siempre da el mismo color', () => {
    expect(colorAvatar('María')).toBe(colorAvatar('María'))
  })

  it('devuelve un color hexadecimal válido', () => {
    expect(colorAvatar('Luis')).toMatch(/^#[0-9A-Fa-f]{6}$/)
  })
})

describe('inicialesAvatar', () => {
  it('toma las dos primeras letras en mayúsculas', () => {
    expect(inicialesAvatar('maría')).toBe('MA')
  })

  it('recorta espacios en los extremos antes de tomar las iniciales', () => {
    expect(inicialesAvatar('  Luis')).toBe('LU')
  })

  it('con un nombre de una sola letra devuelve solo esa letra', () => {
    expect(inicialesAvatar('A')).toBe('A')
  })
})
