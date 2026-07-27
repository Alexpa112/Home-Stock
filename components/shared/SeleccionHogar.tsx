'use client'

import { useState } from 'react'
import { Home, Plus, Users, ChevronRight } from 'lucide-react'
import { useHogar } from '@/contexts/HogarContext'
import { useTranslation } from '@/contexts/TranslationContext'

export function SeleccionHogar() {
  const { propios, compartidos, seleccionar, crear } = useHogar()
  const { t } = useTranslation()
  const [entrandoId, setEntrandoId] = useState<number | null>(null)
  const [creando, setCreando] = useState(false)
  const [nombreNuevo, setNombreNuevo] = useState('')
  const [error, setError] = useState('')

  const hogares = [...propios, ...compartidos]

  const handleSeleccionar = async (id: number) => {
    setEntrandoId(id)
    setError('')
    try {
      await seleccionar(id)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_entrar_hogar'))
      setEntrandoId(null)
    }
  }

  const handleCrear = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nombreNuevo.trim()) return
    setError('')
    try {
      await crear(nombreNuevo.trim())
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_crear_hogar'))
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-1">
          <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mx-auto mb-2">
            <Home className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold">{t('elige_un_hogar')}</h1>
          <p className="text-muted-foreground text-sm">
            {t('selecciona_hogar_texto')}
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 text-sm rounded-lg">{error}</div>
        )}

        {hogares.length > 0 && (
          <div className="space-y-2">
            {hogares.map((hogar) => {
              const esCompartido = compartidos.some((c) => c.id === hogar.id)
              return (
                <button
                  key={hogar.id}
                  onClick={() => handleSeleccionar(hogar.id)}
                  disabled={entrandoId !== null}
                  className="w-full card flex items-center gap-3 text-left hover:bg-muted transition-colors disabled:opacity-60"
                >
                  <div
                    className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 text-white text-lg"
                    style={{ backgroundColor: hogar.color || '#B5551A' }}
                  >
                    <Home className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold truncate">{hogar.nombre}</p>
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      {esCompartido ? (
                        <>
                          <Users className="w-3 h-3" /> {t('compartido')}
                        </>
                      ) : (
                        t('tu_hogar')
                      )}
                    </p>
                  </div>
                  {entrandoId === hogar.id ? (
                    <span className="text-xs text-muted-foreground shrink-0">{t('entrando')}</span>
                  ) : (
                    <ChevronRight className="w-5 h-5 text-muted-foreground shrink-0" />
                  )}
                </button>
              )
            })}
          </div>
        )}

        {creando ? (
          <form onSubmit={handleCrear} className="card space-y-3">
            <input
              type="text"
              value={nombreNuevo}
              onChange={(e) => setNombreNuevo(e.target.value)}
              placeholder={t('placeholder_nombre_hogar')}
              className="input-field"
              autoFocus
              required
            />
            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">{t('crear_y_entrar')}</button>
              <button type="button" onClick={() => setCreando(false)} className="btn-secondary flex-1">{t('cancelar')}</button>
            </div>
          </form>
        ) : (
          <button
            onClick={() => setCreando(true)}
            className="btn-secondary w-full flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" /> {t('crear_hogar_nuevo')}
          </button>
        )}
      </div>
    </div>
  )
}
