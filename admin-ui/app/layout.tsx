import './globals.css'
import React from 'react'
import Link from 'next/link'

export const metadata = {
  title: 'ETERNA DX – Admin',
  description: 'Motor de reglas dinámico',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <body className="min-h-screen bg-bg text-foreground antialiased">
        <div className="min-h-screen flex">
          <aside className="hidden md:flex w-64 flex-col bg-sidebar border-r border-white/10 p-4 gap-2">
            <div className="h-12 flex items-center gap-2 px-2">
              <div className="h-8 w-8 rounded bg-accent/20 flex items-center justify-center text-accent font-bold">E</div>
              <div className="text-sm font-medium opacity-80">ETERNA DX – Admin</div>
            </div>
            <nav className="mt-2 flex flex-col gap-1">
              <Link href="/" className="nav-item">Dashboard</Link>
              <Link href="/rules" className="nav-item">Reglas</Link>
              <Link href="/simulate" className="nav-item">Simulación</Link>
              <Link href="/variables" className="nav-item">Variables</Link>
              <Link href="/stats" className="nav-item">Estadísticas</Link>
              <Link href="/logs" className="nav-item">Logs</Link>
            </nav>
            <div className="mt-auto text-xs text-muted px-2">v0.1.0</div>
          </aside>
          <main className="flex-1 p-4 md:p-6">{children}</main>
        </div>
      </body>
    </html>
  )
}
