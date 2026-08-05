/** Avatar de iniciales con color determinista por nombre, usado en
 * RepartoParticipantes.tsx (8B) y GastoDetalle.tsx (5A) — no es la misma
 * paleta que CategoryBadge.tsx porque identifica personas, no categorías. */

const AVATAR_COLORS = ['#3F6C51', '#7A5A8E', '#A65B3C', '#2F6484', '#8C5A6B', '#5A7A3F']

export function colorAvatar(nombre: string): string {
  let h = 0
  for (let i = 0; i < nombre.length; i++) h = (h * 31 + nombre.charCodeAt(i)) >>> 0
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}

export function inicialesAvatar(nombre: string): string {
  return nombre.trim().slice(0, 2).toUpperCase()
}
