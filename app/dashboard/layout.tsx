'use client'

import Link from 'next/link'
import type { ReactNode } from 'react'
import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { Camera, ClipboardList, History, LogOut, Menu, Package, Settings, ShoppingCart, X } from 'lucide-react'
import { ProtectedRoute } from '@/components/shared/ProtectedRoute'
import { logoutAndRedirect } from '@/lib/session'

const navigationItems = [
  { href: '/dashboard', label: 'Stock', icon: Package },
  { href: '/dashboard/shopping', label: 'Compras', icon: ShoppingCart },
  { href: '/dashboard/listas', label: 'Listas', icon: ClipboardList },
  { href: '/dashboard/ticket', label: 'Escanear ticket', icon: Camera },
  { href: '/dashboard/historial', label: 'Historial', icon: History },
  { href: '/dashboard/settings', label: 'Ajustes', icon: Settings },
]

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = async () => {
    try {
      await logoutAndRedirect()
    } catch (error) {
      console.error('Error al cerrar sesión:', error)
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background text-foreground">
        <header className="sticky top-0 z-50 border-b border-border bg-card lg:hidden">
          <div className="flex items-center justify-between h-14 px-4">
            <h1 className="text-lg font-bold">Dreame!</h1>
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2 hover:bg-muted rounded-lg transition-colors" aria-label="Toggle menu">
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

          {mobileMenuOpen && (
            <nav className="border-t border-border px-4 py-2">
              <div className="space-y-1">
                {navigationItems.map((item) => {
                  const Icon = item.icon
                  const isActive = pathname === item.href
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors min-h-[44px] ${isActive ? 'bg-accent text-accent-foreground' : 'text-foreground hover:bg-muted'}`}
                    >
                      <Icon className="w-5 h-5" />
                      {item.label}
                    </Link>
                  )
                })}
                <button onClick={handleLogout} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-foreground hover:bg-muted transition-colors min-h-[44px]">
                  <LogOut className="w-5 h-5" />
                  Cerrar Sesión
                </button>
              </div>
            </nav>
          )}
        </header>

        <div className="lg:flex lg:h-screen lg:overflow-hidden">
          <aside className="hidden lg:flex lg:flex-col lg:w-64 border-r border-border bg-card">
            <div className="flex items-center gap-2 h-16 px-4 border-b border-border">
              <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
                <Package className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-lg font-bold">Dreame!</h1>
            </div>

            <nav className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
              {navigationItems.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors min-h-[44px] ${isActive ? 'bg-accent text-accent-foreground' : 'text-foreground hover:bg-muted'}`}
                  >
                    <Icon className="w-5 h-5" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </nav>

            <div className="p-4 border-t border-border">
              <button onClick={handleLogout} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-foreground hover:bg-muted transition-colors min-h-[44px]">
                <LogOut className="w-5 h-5" />
                <span>Cerrar Sesión</span>
              </button>
            </div>
          </aside>

          <main className="flex-1 overflow-auto lg:overflow-y-auto">
            <div className="h-full">{children}</div>
          </main>
        </div>
      </div>
    </ProtectedRoute>
  )
}
