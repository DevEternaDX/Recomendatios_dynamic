"use client"

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { listRules, enableRule, cloneRule, deleteRule } from '@/lib/api'

export default function RulesPage() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setLoading(true)
      const data = await listRules()
      setRows(data)
    } catch (e: any) {
      setError(e?.message || 'Error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function toggle(id: string, enabled: boolean) {
    await enableRule(id, !enabled)
    await load()
  }

  async function duplicate(id: string) {
    const newId = prompt('Nuevo ID para la copia:')
    if (!newId) return
    await cloneRule(id, newId)
    await load()
  }

  async function remove(id: string) {
    if (!confirm(`Eliminar regla ${id}?`)) return
    await deleteRule(id)
    await load()
  }

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Gestión de Reglas</h1>
          <p className="text-sm text-muted">Activa, clona o elimina reglas</p>
        </div>
        <div className="space-x-2">
          <Link href="/" className="btn">Volver</Link>
          <Link href="/rules/new" className="btn btn-primary">Nueva Regla</Link>
        </div>
      </div>
      {loading && <div className="text-muted">Cargando…</div>}
      {error && <div className="text-red-400">{error}</div>}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {rows.map(r => (
            <div key={r.id} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{r.id}</div>
                  <div className="text-xs text-muted">{r.category || '—'}</div>
                </div>
                <div className="text-xs">
                  <span className="px-2 py-1 rounded bg-white/10 mr-1">P:{r.priority}</span>
                  <span className="px-2 py-1 rounded bg-white/10">S:{r.severity}</span>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <div className="text-sm">Estado: <span className={r.enabled ? 'text-accent' : 'text-muted'}>{r.enabled ? 'ON' : 'OFF'}</span></div>
                <div className="space-x-2">
                  <button className="btn" onClick={() => toggle(r.id, r.enabled)}>{r.enabled ? 'Desactivar' : 'Activar'}</button>
                  <button className="btn" onClick={() => duplicate(r.id)}>Clonar</button>
                  <button className="btn" onClick={() => remove(r.id)}>Eliminar</button>
                  <Link href={`/rules/${r.id}`} className="btn btn-primary">Editar</Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
