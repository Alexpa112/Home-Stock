'use client'

import { useEffect, useRef, useState } from 'react'
import { Plus, ScanBarcode, X } from 'lucide-react'
import { useTranslation } from '@/contexts/TranslationContext'
import { buscarCatalogo } from '@/lib/catalogo'

export interface SugerenciaCatalogo {
  nombre: string
  icono: string | null
  categoria: string | null
  unidad: string | null
}

interface BarraRapidaProps {
  // Misma vía que el formulario completo: la pantalla crea el artículo y lo
  // fusiona en la lista (misma llamada de alta). Devuelve true si se añadió.
  onAnadir: (nombre: string, sugerencia?: SugerenciaCatalogo) => Promise<boolean>
  onEscanear: () => void
  // Abre el formulario completo con lo escrito (categoría, unidad, icono...).
  onMasOpciones: (nombre: string) => void
  onCerrar: () => void
}

// Barra de una línea para meter varios artículos seguidos sin salir (rediseño
// 5B). Va sobre la barra de pestañas y, con el teclado abierto, se pega a él.
export function BarraRapida({ onAnadir, onEscanear, onMasOpciones, onCerrar }: BarraRapidaProps) {
  const { t } = useTranslation()
  const [texto, setTexto] = useState('')
  const [sugerencias, setSugerencias] = useState<SugerenciaCatalogo[]>([])
  const [enviando, setEnviando] = useState(false)
  const [aviso, setAviso] = useState('')
  const [bajo, setBajo] = useState<number | null>(null)
  const entrada = useRef<HTMLInputElement>(null)

  useEffect(() => {
    entrada.current?.focus()
    // Marca el <body> para que el botón flotante del layout se oculte (no
    // basta con taparlo: seguiría en el orden de tabulación y con su nombre).
    document.body.dataset.barraRapida = '1'
    return () => {
      delete document.body.dataset.barraRapida
    }
  }, [])

  // Con el teclado abierto, la ventana visual es más baja que la de diseño:
  // se pega al borde superior del teclado en vez de quedar tapada.
  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    const ajustar = () => {
      const tecladoPx = window.innerHeight - vv.height - vv.offsetTop
      setBajo(tecladoPx > 80 ? tecladoPx : null)
    }
    ajustar()
    vv.addEventListener('resize', ajustar)
    vv.addEventListener('scroll', ajustar)
    return () => {
      vv.removeEventListener('resize', ajustar)
      vv.removeEventListener('scroll', ajustar)
    }
  }, [])

  // Cinta de sugerencias: el mismo catálogo del formulario completo.
  useEffect(() => {
    const q = texto.trim()
    let vigente = true
    const timer = setTimeout(() => {
      buscarCatalogo(q || undefined)
        .then((data: unknown) => {
          if (vigente) setSugerencias(Array.isArray(data) ? (data as SugerenciaCatalogo[]).slice(0, 8) : [])
        })
        .catch(() => {})
    }, 250)
    return () => {
      vigente = false
      clearTimeout(timer)
    }
  }, [texto])

  const anadir = async (nombre: string, sugerencia?: SugerenciaCatalogo) => {
    const limpio = nombre.trim()
    if (!limpio || enviando) return
    setEnviando(true)
    const ok = await onAnadir(limpio, sugerencia)
    setEnviando(false)
    if (ok) {
      setTexto('')
      setAviso(`${t('añadido_a_la_compra')}: ${limpio}`)
      entrada.current?.focus()
    }
  }

  return (
    <div
      className="lg:hidden fixed inset-x-0 !mb-0 z-[56] bg-card border-t border-border px-3 pt-2 pb-3 shadow-[0_-4px_16px_rgba(0,0,0,0.08)]"
      style={{ bottom: bajo !== null ? `${bajo}px` : 'var(--mobile-toolbar-h)' }}
      onKeyDown={(e) => { if (e.key === 'Escape') onCerrar() }}
    >
      <div className="flex gap-2 overflow-x-auto pb-2" aria-label={t('elegir_del_catalogo')}>
        {sugerencias.map((s) => (
          <button
            key={s.nombre}
            type="button"
            onClick={() => anadir(s.nombre, s)}
            className="shrink-0 px-3 min-h-[44px] rounded-full border border-border bg-background text-sm text-foreground whitespace-nowrap active:scale-95 transition-transform"
          >
            {s.nombre}
          </button>
        ))}
      </div>

      <form
        className="flex items-center gap-2"
        onSubmit={(e) => { e.preventDefault(); anadir(texto) }}
      >
        <label htmlFor="barra-rapida-nombre" className="sr-only">{t('añadir_articulo')}</label>
        <input
          id="barra-rapida-nombre"
          ref={entrada}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder={`${t('añadir_articulo')}…`}
          autoComplete="off"
          enterKeyHint="done"
          className="input-field flex-1 min-w-0 !text-base"
        />
        <button
          type="button"
          onClick={onEscanear}
          aria-label={t('escanear_codigo_barras')}
          className="w-12 h-12 shrink-0 flex items-center justify-center rounded-xl border border-border bg-background"
        >
          <ScanBarcode className="w-5 h-5" />
        </button>
        <button
          type="submit"
          disabled={!texto.trim() || enviando}
          aria-label={t('añadir')}
          className="w-12 h-12 shrink-0 flex items-center justify-center rounded-xl bg-accent text-accent-foreground disabled:opacity-50"
        >
          <Plus className="w-5 h-5" />
        </button>
      </form>

      <div className="flex items-center justify-between mt-1 min-h-[44px]">
        <button
          type="button"
          onClick={() => onMasOpciones(texto.trim())}
          className="px-1 min-h-[44px] text-sm font-medium text-accent"
        >
          {t('mas_opciones')}
        </button>
        <p role="status" aria-live="polite" className="flex-1 text-center text-xs text-muted-foreground truncate px-2">{aviso}</p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label={t('cancelar')}
          className="w-11 h-11 flex items-center justify-center rounded-xl hover:bg-muted"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
