'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Package, ShoppingCart, Settings, LogOut, ClipboardList, Camera, History, Home, ChevronsUpDown } from 'lucide-react'
import { useState } from 'react'
import { ProtectedRoute } from '@/components/shared/ProtectedRoute'
import { SelectorHogarPantallaCompleta } from '@/components/shared/SelectorHogarPantallaCompleta'
import { HogarProvider, useHogar } from '@/contexts/HogarContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { auth } from '@/lib/api'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <HogarProvider>
        <DashboardShell>{children}</DashboardShell>
      </HogarProvider>
    </ProtectedRoute>
  )
}

function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { hogarActivoId, loading, propios, compartidos } = useHogar()
  const { t } = useTranslation()
  const [mostrarSelectorHogar, setMostrarSelectorHogar] = useState(false)
  const hogarActivo = [...propios, ...compartidos].find((h) => h.id === hogarActivoId)

  // Bottom bar móvil: las 5 rutas más usadas
  const tabItems = [
    { href: '/dashboard', label: t('nav_stock'), icon: Package },
    { href: '/dashboard/shopping', label: t('nav_compra'), icon: ShoppingCart },
    { href: '/dashboard/ticket', label: t('nav_escanear'), icon: Camera },
    { href: '/dashboard/listas', label: t('listas'), icon: ClipboardList },
    { href: '/dashboard/settings', label: t('ajustes'), icon: Settings },
  ]

  // Sidebar desktop: todas las rutas
  const sidebarItems = [
    { href: '/dashboard', label: t('nav_stock'), icon: Package },
    { href: '/dashboard/shopping', label: t('nav_lista_compra'), icon: ShoppingCart },
    { href: '/dashboard/listas', label: t('mis_listas'), icon: ClipboardList },
    { href: '/dashboard/ticket', label: t('escanear_ticket'), icon: Camera },
    { href: '/dashboard/historial', label: t('historial'), icon: History },
    { href: '/dashboard/settings', label: t('ajustes'), icon: Settings },
  ]

  const handleLogout = async () => {
    try {
      await auth.logout()
      window.location.href = '/'
    } catch {
      // ignorar, la redirección se producirá igualmente
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-muted border-t-accent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-muted-foreground">{t('cargando')}</p>
        </div>
      </div>
    )
  }

  if (!hogarActivoId) {
    return <SelectorHogarPantallaCompleta />
  }

  if (mostrarSelectorHogar) {
    return <SelectorHogarPantallaCompleta onCerrar={() => setMostrarSelectorHogar(false)} />
  }

  return (
      <div className="min-h-screen bg-background text-foreground lg:flex lg:h-screen lg:overflow-hidden">

        {/* ── Sidebar desktop ── */}
        <aside className="hidden lg:flex lg:flex-col lg:w-60 shrink-0 border-r border-border bg-card">
          {/* Logo */}
          <div className="flex items-center gap-2.5 h-14 px-5 border-b border-border">
            <div className="w-7 h-7 bg-accent rounded-lg flex items-center justify-center shrink-0">
              <Package className="w-4 h-4 text-white" />
            </div>
            <span className="text-base font-bold tracking-tight">Dreame!</span>
          </div>

          {/* Selector de hogar: abre la pantalla completa (tapa todo) */}
          <button
            onClick={() => setMostrarSelectorHogar(true)}
            className="flex items-center gap-2.5 mx-3 mt-3 mb-1 px-2.5 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-left"
          >
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-white"
              style={{ backgroundColor: hogarActivo?.color || '#B5551A' }}
            >
              <Home className="w-3.5 h-3.5" />
            </div>
            <span className="flex-1 min-w-0 text-sm font-semibold truncate">{hogarActivo?.nombre || t('mi_stock')}</span>
            <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          </button>

          {/* Nav links */}
          <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
            {sidebarItems.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href
              return (
                <Link
                  key={href}
                  href={href}
                  className={`
                    group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 min-h-[44px]
                    ${isActive
                      ? 'bg-accent/10 text-accent'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                    }
                  `}
                >
                  <Icon className={`w-4 h-4 shrink-0 transition-colors ${isActive ? 'text-accent' : 'text-muted-foreground group-hover:text-foreground'}`} />
                  {label}
                  {isActive && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-accent" />}
                </Link>
              )
            })}
          </nav>

          {/* Logout */}
          <div className="px-3 pb-4 pt-2 border-t border-border">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-150 min-h-[44px]"
            >
              <LogOut className="w-4 h-4 shrink-0" />
              {t('cerrar_sesion')}
            </button>
          </div>
        </aside>

        {/* ── Contenido principal ── */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* Header móvil: logo + selector de hogar (abre pantalla completa) */}
          <header className="sticky top-0 z-40 lg:hidden flex items-center justify-between h-12 px-4 border-b border-border bg-card/90 backdrop-blur-sm">
            <span className="text-base font-bold tracking-tight">Dreame!</span>
            <button
              onClick={() => setMostrarSelectorHogar(true)}
              className="flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-muted transition-colors"
            >
              <div
                className="w-5 h-5 rounded-md flex items-center justify-center shrink-0 text-white"
                style={{ backgroundColor: hogarActivo?.color || '#B5551A' }}
              >
                <Home className="w-3 h-3" />
              </div>
              <span className="text-xs font-semibold max-w-[9rem] truncate">{hogarActivo?.nombre}</span>
              <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground" />
            </button>
          </header>

          {/* Scroll area */}
          <main className="flex-1 overflow-y-auto pb-20 lg:pb-0">
            {children}
          </main>
        </div>

        {/* ── Bottom tab bar móvil ── */}
        <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 bg-card/95 backdrop-blur-md border-t border-border">
          <div className="flex items-stretch h-16 safe-area-pb">
            {tabItems.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href
              return (
                <Link
                  key={href}
                  href={href}
                  className={`
                    flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors min-h-[44px]
                    ${isActive ? 'text-accent' : 'text-muted-foreground'}
                  `}
                >
                  <div className={`p-1.5 rounded-xl transition-all duration-150 ${isActive ? 'bg-accent/10' : ''}`}>
                    <Icon className={`w-5 h-5 ${isActive ? 'text-accent' : ''}`} />
                  </div>
                  <span>{label}</span>
                </Link>
              )
            })}
          </div>
        </nav>

      </div>
  )
}
