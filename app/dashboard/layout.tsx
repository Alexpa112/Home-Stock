'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Package, ShoppingCart, Settings, LogOut, ClipboardList, Camera, History } from 'lucide-react'
import { ProtectedRoute } from '@/components/shared/ProtectedRoute'
import { auth } from '@/lib/api'

// Bottom bar móvil: las 5 rutas más usadas
const tabItems = [
  { href: '/dashboard', label: 'Stock', icon: Package },
  { href: '/dashboard/shopping', label: 'Compra', icon: ShoppingCart },
  { href: '/dashboard/ticket', label: 'Escanear', icon: Camera },
  { href: '/dashboard/listas', label: 'Listas', icon: ClipboardList },
  { href: '/dashboard/settings', label: 'Ajustes', icon: Settings },
]

// Sidebar desktop: todas las rutas
const sidebarItems = [
  { href: '/dashboard', label: 'Stock', icon: Package },
  { href: '/dashboard/shopping', label: 'Lista de compra', icon: ShoppingCart },
  { href: '/dashboard/listas', label: 'Mis listas', icon: ClipboardList },
  { href: '/dashboard/ticket', label: 'Escanear ticket', icon: Camera },
  { href: '/dashboard/historial', label: 'Historial', icon: History },
  { href: '/dashboard/settings', label: 'Ajustes', icon: Settings },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  const handleLogout = async () => {
    try {
      await auth.logout()
      window.location.href = '/'
    } catch {
      // ignorar, la redirección se producirá igualmente
    }
  }

  return (
    <ProtectedRoute>
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
              Cerrar sesión
            </button>
          </div>
        </aside>

        {/* ── Contenido principal ── */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* Header móvil — solo logo, sin hamburguesa */}
          <header className="sticky top-0 z-40 lg:hidden flex items-center h-12 px-4 border-b border-border bg-card/90 backdrop-blur-sm">
            <span className="text-base font-bold tracking-tight">Dreame!</span>
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
    </ProtectedRoute>
  )
}
