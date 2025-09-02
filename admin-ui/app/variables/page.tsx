"use client"

import { useEffect, useState } from 'react'
import { listVariables } from '@/lib/api'
import Link from 'next/link'

export default function VariablesPage() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const data = await listVariables()
        setRows(data)
      } catch (e:any) {
        setError(e?.message || 'Error')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Variables</h1>
          <p className="text-sm text-muted">Definiciones y agregadores disponibles</p>
        </div>
        <Link href="/" className="btn">Volver</Link>
      </div>
      {loading && <div className="text-muted">Cargando…</div>}
      {error && <div className="text-red-400">{error}</div>}
      {!loading && !error && (
        <div className="card">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="p-2 text-left">key</th>
                <th className="p-2">tipo</th>
                <th className="p-2">unidad</th>
                <th className="p-2">aggs</th>
                <th className="p-2">rango</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(v => (
                <tr key={v.key} className="border-t border-white/10">
                  <td className="p-2 font-mono text-xs">{v.key}</td>
                  <td className="p-2 text-center">{v.type}</td>
                  <td className="p-2 text-center">{v.unit}</td>
                  <td className="p-2 text-center">{(v.allowed_aggregators||[]).join(', ')}</td>
                  <td className="p-2 text-center">{v.valid_range?.join('..')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
