'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from '@/contexts/TranslationContext'
import { Modal } from '@/components/dashboard/Modal'

interface BarcodeScannerProps {
  onDetectado: (codigo: string) => void
  onCerrar: () => void
}

type Estado = 'iniciando' | 'activo' | 'sin_soporte' | 'error'

const FORMATOS_DESEADOS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'code_39', 'qr_code']
// Con detectar en cada fotograma (60/s) se gasta bateria sin leer mejor un
// codigo que lleva medio segundo delante de la camara.
const INTERVALO_DETECCION_MS = 120
const LONGITUD_MAXIMA_CODIGO = 64

// Lectura de codigos de barras/EAN (P-03) con la BarcodeDetector API nativa
// del navegador (Chrome/Android; sin soporte en Safari/iOS ni Firefox). Se opta
// por la API nativa en vez de una libreria JS para no anadir peso ni
// dependencias nuevas. Cuando no hay camara, permiso o soporte, el codigo se
// puede ESCRIBIR a mano: la busqueda en el catalogo es la misma.
export function BarcodeScanner({ onDetectado, onCerrar }: BarcodeScannerProps) {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [estado, setEstado] = useState<Estado>('iniciando')
  const [codigoManual, setCodigoManual] = useState('')

  // La pantalla le pasa una funcion nueva en cada render. Si el efecto de la
  // camara dependiera de ella, cualquier re-render de la pantalla (un setState,
  // el refresco periodico) pararia y reabriria la camara: parpadeo negro y
  // nueva peticion de permisos. Se guarda en una ref y el efecto corre UNA vez.
  const onDetectadoRef = useRef(onDetectado)
  useEffect(() => {
    onDetectadoRef.current = onDetectado
  })

  useEffect(() => {
    let activo = true
    let frameId = 0
    let stream: MediaStream | null = null

    const detener = () => {
      activo = false
      if (frameId) cancelAnimationFrame(frameId)
      stream?.getTracks().forEach((track) => track.stop())
    }

    const iniciar = async () => {
      // navigator.mediaDevices no existe fuera de contextos seguros (http) ni
      // en navegadores antiguos: tocarlo sin comprobar lanzaba una excepcion.
      const Detector = (window as any).BarcodeDetector
      if (!Detector || !navigator.mediaDevices?.getUserMedia) {
        setEstado('sin_soporte')
        return
      }

      let detector: any
      try {
        // Un dispositivo puede traer BarcodeDetector sin soportar ninguno de
        // los formatos pedidos; el constructor lanza TypeError en ese caso.
        const soportados: string[] | null = Detector.getSupportedFormats
          ? await Detector.getSupportedFormats()
          : null
        const formatos = soportados ? FORMATOS_DESEADOS.filter((f) => soportados.includes(f)) : FORMATOS_DESEADOS
        if (formatos.length === 0) {
          setEstado('sin_soporte')
          return
        }
        detector = new Detector({ formats: formatos })
      } catch {
        setEstado('sin_soporte')
        return
      }

      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } } })
      } catch {
        if (activo) setEstado('error')
        return
      }
      if (!activo) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }

      setEstado('activo')
      const video = videoRef.current
      if (video) {
        video.srcObject = stream
        video.play().catch(() => {})
      }

      let ultimo = 0
      const detectar = async (ahora: number) => {
        if (!activo || !videoRef.current) return
        if (ahora - ultimo >= INTERVALO_DETECCION_MS) {
          ultimo = ahora
          try {
            const codigos = await detector.detect(videoRef.current)
            if (activo && codigos.length > 0 && codigos[0].rawValue) {
              detener()
              onDetectadoRef.current(codigos[0].rawValue)
              return
            }
          } catch {
            // Fotograma no valido para detectar (p. ej. video aun sin datos); se ignora y se reintenta.
          }
        }
        if (activo) frameId = requestAnimationFrame(detectar)
      }
      frameId = requestAnimationFrame(detectar)
    }

    iniciar()
    return detener
  }, [])

  const usarCodigoManual = (e: React.FormEvent) => {
    e.preventDefault()
    const codigo = codigoManual.trim()
    if (!codigo) return
    onDetectadoRef.current(codigo)
  }

  return (
    <Modal onCerrar={onCerrar}>
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">{t('escanear_codigo_barras')}</h2>
        {estado === 'sin_soporte' && <p className="text-sm text-muted-foreground">{t('escaner_no_soportado')}</p>}
        {estado === 'error' && <p className="text-sm text-destructive">{t('err_camara_no_disponible')}</p>}
        {(estado === 'iniciando' || estado === 'activo') && (
          <div className="relative overflow-hidden rounded-xl bg-black aspect-video">
            <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
            <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 h-16 border-2 border-white/70 rounded-lg pointer-events-none" />
          </div>
        )}

        <form onSubmit={usarCodigoManual} className="space-y-1.5">
          <label htmlFor="codigo-manual" className="block text-sm font-medium">
            {t('codigo_manual_etiqueta')}
          </label>
          <div className="flex gap-2">
            <input
              id="codigo-manual"
              value={codigoManual}
              onChange={(e) => setCodigoManual(e.target.value)}
              inputMode="numeric"
              autoComplete="off"
              maxLength={LONGITUD_MAXIMA_CODIGO}
              placeholder="8412345678901"
              className="input-field flex-1 min-w-0 !text-base"
            />
            <button
              type="submit"
              disabled={!codigoManual.trim()}
              className="btn-primary min-h-[44px] shrink-0 disabled:opacity-50"
            >
              {t('codigo_manual_boton')}
            </button>
          </div>
        </form>

        <button type="button" onClick={onCerrar} className="btn-secondary w-full min-h-[44px]">
          {t('cancelar')}
        </button>
      </div>
    </Modal>
  )
}
