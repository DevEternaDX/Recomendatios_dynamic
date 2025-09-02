import Link from 'next/link'

export default function Home() {
  return (
    <main className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Panel</h1>
        <p className="text-sm text-muted">Accesos rápidos</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link href="/rules" className="card hover:brightness-110">
          <div className="text-accent text-xs uppercase">Reglas</div>
          <div className="text-lg font-medium">Gestión de reglas</div>
          <div className="text-muted text-sm">Listar, crear y editar reglas</div>
        </Link>
        <Link href="/simulate" className="card hover:brightness-110">
          <div className="text-accent text-xs uppercase">Simulación</div>
          <div className="text-lg font-medium">Probar reglas</div>
          <div className="text-muted text-sm">Por usuario y fecha</div>
        </Link>
        <Link href="/variables" className="card hover:brightness-110">
          <div className="text-accent text-xs uppercase">Variables</div>
          <div className="text-lg font-medium">Registro de variables</div>
          <div className="text-muted text-sm">Definiciones y agregadores</div>
        </Link>
      </div>
    </main>
  )
}
