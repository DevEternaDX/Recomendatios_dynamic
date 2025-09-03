"use client"

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

export default function LogsPage() {
  const [startISO, setStartISO] = useState<string>('')
  const [endISO, setEndISO] = useState<string>('')
  const [ruleId, setRuleId] = useState<string>('')
  const [user, setUser] = useState<string>('')
  const [action, setAction] = useState<string>('')
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params: any = {}
      if (startISO) params.start = startISO
      if (endISO) params.end = endISO
      if (ruleId) params.rule_id = ruleId
      if (user) params.user = user
      if (action) params.action = action
      const { data } = await api.get('/analytics/logs', { params })
      setRows(data || [])
    } catch (e:any) {
      setError(e?.message || 'Error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(()=>{ load() }, [])

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Logs</h1>
        <Link href="/" className="btn">Volver</Link>
      </div>

      <div className="card grid grid-cols-1 md:grid-cols-6 gap-3 items-end">
        <div>
          <label className="block text-sm">Desde</label>
          <input type="date" value={startISO} onChange={e=> setStartISO(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm">Hasta</label>
          <input type="date" value={endISO} onChange={e=> setEndISO(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm">Regla</label>
          <input value={ruleId} onChange={e=> setRuleId(e.target.value)} placeholder="rule_id" />
        </div>
        <div>
          <label className="block text-sm">Usuario</label>
          <input value={user} onChange={e=> setUser(e.target.value)} placeholder="usuario" />
        </div>
        <div>
          <label className="block text-sm">Acción</label>
          <input value={action} onChange={e=> setAction(e.target.value)} placeholder="create/update/delete" />
        </div>
        <div className="md:col-span-6">
          <button className="btn btn-primary" onClick={load} disabled={loading}>Filtrar</button>
        </div>
      </div>

      {loading && <div className="text-muted">Cargando…</div>}
      {error && <div className="text-red-400">{error}</div>}

      <div className="card overflow-x-auto">
        <table className="min-w-[800px] text-sm">
          <thead>
            <tr className="text-left text-xs text-muted">
              <th className="p-2">ID</th>
              <th className="p-2">Fecha</th>
              <th className="p-2">Usuario</th>
              <th className="p-2">Rol</th>
              <th className="p-2">Acción</th>
              <th className="p-2">Entidad</th>
              <th className="p-2">Detalle</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r:any)=> (
              <tr key={r.id} className="border-t border-white/5 align-top">
                <td className="p-2 font-mono text-xs">{r.id}</td>
                <td className="p-2 font-mono text-xs">{r.created_at}</td>
                <td className="p-2">{r.user||'—'}</td>
                <td className="p-2">{r.role||'—'}</td>
                <td className="p-2">{r.action}</td>
                <td className="p-2">{r.entity_type}:{r.entity_id}</td>
                <td className="p-2">
                  <details>
                    <summary className="cursor-pointer">Ver JSON</summary>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                      <pre className="text-xs bg-white/5 p-2 overflow-x-auto">{JSON.stringify(r.before, null, 2)}</pre>
                      <pre className="text-xs bg-white/5 p-2 overflow-x-auto">{JSON.stringify(r.after, null, 2)}</pre>
                    </div>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}


