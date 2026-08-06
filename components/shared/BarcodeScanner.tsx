'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from '@/contexts/TranslationContext'
import { Modal } from '@/components/dashboard/Modal'

interface BarcodeScannerProps {
  onDetectado: (codigo: string) => void
  onCerrar: () => void
}

// Lectura de codigos de barras/EAN (P-03) con la BarcodeDetector API nativa
// del navegador (Chrome/Android; sin soporte en Safari/iOS a fecha de hoy).
// Se opta por la API nativa en vez de una libreria JS para no anadir peso ni
// dependencias nuevas: si el navegador no la soporta, se muestra un aviso y
// el usuario sigue pudiendo anadir el articulo escribiendo el nombre a mano.
export function BarcodeScanner({ onDetectado, onCerrar }: BarcodeScannerProps) {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [error, setError] = useState('')
  const [soportado, setSoportado] = useState(true)

  useEffect(() => {
    if (!('BarcodeDetector' in window)) {
      setSoportado(false)
      return
    }

    let activo = true
    let frameId: number

    const detector = new (window as any).BarcodeDetector({
      formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'code_39', 'qr_code'],
    })

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' } })
      .then((stream) => {
        if (!activo) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          videoRef.current.play().catch(() => {})
        }

        const detectar = async () => {
          if (!activo || !videoRef.current) return
          try {
            const codigos = await detector.detect(videoRef.current)
            if (codigos.length > 0) {
              activo = false
              onDetectado(codigos[0].rawValue)
              return
            }
          } catch {
            // Fotograma no valido para detectar (p. ej. video aun sin datos); se ignora y se reintenta.
          }
          frameId = requestAnimationFrame(detectar)
        }
        frameId = requestAnimationFrame(detectar)
      })
      .catch(() => setError('err_camara_no_disponible'))

    return () => {
      activo = false
      if (frameId) cancelAnimationFrame(frameId)
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [onDetectado])

  return (
    <Modal onCerrar={onCerrar}>
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">{t('escanear_codigo_barras')}</h2>
        {!soportado ? (
          <p className="text-sm text-muted-foreground">{t('escaner_no_soportado')}</p>
        ) : error ? (
          <p className="text-sm text-destructive">{t(error)}</p>
        ) : (
          <div className="relative overflow-hidden rounded-xl bg-black aspect-video">
            <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
            <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 h-16 border-2 border-white/70 rounded-lg pointer-events-none" />
          </div>
        )}
        <button type="button" onClick={onCerrar} className="btn-secondary w-full">
          {t('cancelar')}
        </button>
      </div>
    </Modal>
  )
}
