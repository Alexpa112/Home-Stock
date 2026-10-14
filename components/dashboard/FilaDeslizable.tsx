'use client'

import { ReactNode, useRef, useState } from 'react'
import { Check, Undo2 } from 'lucide-react'
import {
  clasificarMovimiento, desplazamientoVisible, empiezaEnElBorde, gestoCompleto, UMBRAL_COMPLETA,
} from '@/lib/deslizar'

interface FilaDeslizableProps {
  children: ReactNode
  // Se llama al soltar con el gesto completo (a la derecha, pasado el umbral).
  onCompletar: () => void
  // Se llama en cuanto el movimiento deja de ser una pulsación; la pantalla lo
  // usa para cancelar su pulsación larga.
  onMovimiento: () => void
  // La pulsación larga ya se disparó (se abrió la edición): el gesto se ignora.
  bloqueado: () => boolean
  // true = la fila ya está comprada y el gesto la restaura.
  restaura?: boolean
}

// Envoltorio de gesto para una fila. La casilla de dentro NO se toca: sigue
// siendo el camino accesible (lector de pantalla, teclado, quien no puede
// deslizar). Con `touch-action: pan-y` el navegador deja pasar el movimiento
// horizontal y solo se queda el scroll vertical.
export function FilaDeslizable({ children, onCompletar, onMovimiento, bloqueado, restaura = false }: FilaDeslizableProps) {
  const [dx, setDx] = useState(0)
  const [arrastrando, setArrastrando] = useState(false)
  const inicio = useRef<{ x: number; y: number } | null>(null)
  const direccion = useRef<'pendiente' | 'horizontal' | 'vertical'>('pendiente')

  const reiniciar = () => {
    inicio.current = null
    direccion.current = 'pendiente'
    setArrastrando(false)
    setDx(0)
  }

  const alEmpezar = (e: React.TouchEvent) => {
    const toque = e.touches[0]
    if (!toque || empiezaEnElBorde(toque.clientX)) {
      inicio.current = null
      return
    }
    inicio.current = { x: toque.clientX, y: toque.clientY }
    direccion.current = 'pendiente'
  }

  const alMover = (e: React.TouchEvent) => {
    const ini = inicio.current
    const toque = e.touches[0]
    if (!ini || !toque || bloqueado()) return
    const mx = toque.clientX - ini.x
    const my = toque.clientY - ini.y
    if (direccion.current === 'pendiente') {
      direccion.current = clasificarMovimiento(mx, my)
      if (direccion.current !== 'pendiente') onMovimiento()
      if (direccion.current === 'horizontal') setArrastrando(true)
    }
    if (direccion.current === 'horizontal') setDx(desplazamientoVisible(mx))
  }

  const alSoltar = () => {
    const completo = direccion.current === 'horizontal' && !bloqueado() && gestoCompleto(dx)
    reiniciar()
    if (completo) onCompletar()
  }

  const Icono = restaura ? Undo2 : Check
  const avance = Math.min(1, dx / UMBRAL_COMPLETA)

  return (
    <div className="relative overflow-hidden rounded-2xl" style={{ touchAction: 'pan-y' }}>
      <div
        aria-hidden="true"
        className={`absolute inset-0 pointer-events-none flex items-center pl-5 ${restaura ? 'bg-muted text-muted-foreground' : 'bg-green-500 text-white'}`}
        style={{ opacity: avance }}
      >
        <Icono className="w-6 h-6" />
      </div>
      <div
        className="relative"
        onTouchStart={alEmpezar}
        onTouchMove={alMover}
        onTouchEnd={alSoltar}
        onTouchCancel={reiniciar}
        style={{
          transform: dx ? `translateX(${dx}px)` : undefined,
          transition: arrastrando ? 'none' : 'transform 160ms ease-out',
        }}
      >
        {children}
      </div>
    </div>
  )
}
