import { notFound } from 'next/navigation'

// /diagnose es una herramienta de desarrollo: en produccion vuelca el JSON de /api/auth/estado y
// la URL interna del backend (NEXT_PUBLIC_API_URL, incrustada en el bundle) a quien la abra, sin
// iniciar sesion. En produccion responde 404.
export default function DiagnoseLayout({ children }: { children: React.ReactNode }) {
  if (process.env.NODE_ENV === 'production') notFound()
  return <>{children}</>
}
