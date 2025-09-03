"use client"

import { useState } from 'react'
import { simulate, simulateRange } from '@/lib/api'
import Link from 'next/link'

export default function SimulatePage() {
  const [userId, setUserId] = useState('demo_user')
  const [dateISO, setDateISO] = useState(new Date().toISOString().slice(0,10))
  const [tenantId, setTenantId] = useState('default')
  const [rangeMode, setRangeMode] = useState(false)
  const [dateStartISO, setDateStartISO] = useState(new Date().toISOString().slice(0,10))
  const [dateEndISO, setDateEndISO] = useState(new Date().toISOString().slice(0,10))
  const [resp, setResp] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      if (!rangeMode) {
        const r = await simulate(userId, dateISO, tenantId, true)
        setResp(r)
      } else {
        const r = await simulateRange(userId, dateStartISO, dateEndISO, tenantId, true)
        setResp(r)
      }
    } catch (e:any) {
      setError(e?.message || 'Error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Simular</h1>
        <Link href="/" className="btn">Volver</Link>
      </div>
      <div className="card flex gap-3 items-end">
        <div>
          <label className="block text-sm">user_id</label>
          <input value={userId} onChange={e=>setUserId(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm">tenant_id</label>
          <input value={tenantId} onChange={e=>setTenantId(e.target.value)} />
        </div>
        {!rangeMode && (
          <div>
            <label className="block text-sm">fecha</label>
            <input type="date" value={dateISO} onChange={e=>setDateISO(e.target.value)} />
          </div>
        )}
        {rangeMode && (
          <>
            <div>
              <label className="block text-sm">desde</label>
              <input type="date" value={dateStartISO} onChange={e=>setDateStartISO(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm">hasta</label>
              <input type="date" value={dateEndISO} onChange={e=>setDateEndISO(e.target.value)} />
            </div>
          </>
        )}
        <label className="inline-flex items-center gap-2 text-sm ml-2">
          <input type="checkbox" checked={rangeMode} onChange={e=> setRangeMode(e.target.checked)} />
          Rango
        </label>
        <button onClick={run} className="btn btn-primary">Ejecutar</button>
      </div>
      {loading && <div className="text-muted">Cargando…</div>}
      {error && <div className="text-red-400">{error}</div>}
      {resp && !rangeMode && (
        <div className="card">
          <div className="mb-2 text-sm">Eventos: {resp.count}</div>
          <div className="space-y-3">
            {resp.events?.map((e:any, idx:number) => (
              <div key={idx} className="card">
                <div className="font-mono text-xs">{e.rule_id}</div>
                <div className="text-sm">{e.message_text}</div>
                <details className="mt-2">
                  <summary className="cursor-pointer text-sm">WHY</summary>
                  <pre className="text-xs bg-white/5 p-2 overflow-x-auto">{JSON.stringify(e.why, null, 2)}</pre>
                </details>
              </div>
            ))}
          </div>
        </div>
      )}
      {resp && rangeMode && Array.isArray(resp) && (
        <div className="space-y-4">
          {resp.map((day:any, idx:number) => (
            <div key={idx} className="card">
              <div className="mb-2 text-sm font-mono">{day.date} — Eventos: {day.count}</div>
              <div className="space-y-3">
                {day.events?.map((e:any, j:number) => (
                  <div key={j} className="card">
                    <div className="font-mono text-xs">{e.rule_id}</div>
                    <div className="text-sm">{e.message_text}</div>
                    <details className="mt-2">
                      <summary className="cursor-pointer text-sm">WHY</summary>
                      <pre className="text-xs bg-white/5 p-2 overflow-x-auto">{JSON.stringify(e.why, null, 2)}</pre>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
