"use client"

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { listRules, enableRule, cloneRule, deleteRule, exportRules, importRules, importRulesCsv, deleteAllRules } from '@/lib/api'

export default function RulesPage() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const [importText, setImportText] = useState('')
  const [csvMode, setCsvMode] = useState(false)

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

  async function removeAll() {
    const totalRules = rows.length
    
    if (totalRules === 0) {
      alert('No hay reglas para eliminar')
      return
    }

    // Doble confirmación para operación peligrosa
    const firstConfirm = confirm(
      `⚠️ PELIGRO: Vas a eliminar TODAS las ${totalRules} reglas.\n\n` +
      `Esta acción NO se puede deshacer.\n\n` +
      `¿Estás seguro de que quieres continuar?`
    )
    
    if (!firstConfirm) return

    const secondConfirm = confirm(
      `🚨 ÚLTIMA CONFIRMACIÓN:\n\n` +
      `Se eliminarán ${totalRules} reglas permanentemente.\n\n` +
      `Escribe "ELIMINAR TODAS" mentalmente y haz clic en OK para confirmar.`
    )
    
    if (!secondConfirm) return

    try {
      const result = await deleteAllRules()
      alert(`✅ ${result.message}`)
      load() // Recargar la lista
    } catch (e: any) {
      alert(`❌ Error: ${e?.message || 'Error eliminando reglas'}`)
    }
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
          <button className="btn" onClick={async()=>{
            try {
              const data = await exportRules('json')
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = 'rules-export.json'
              a.click()
              URL.revokeObjectURL(url)
            } catch (e:any) { alert(e?.message||'Error exportando') }
          }}>Exportar JSON</button>
          <button className="btn" onClick={async()=>{
            try {
              const data = await exportRules('yaml')
              const blob = new Blob([typeof data === 'string' ? data : String(data)], { type: 'text/yaml' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = 'rules-export.yaml'
              a.click()
              URL.revokeObjectURL(url)
            } catch (e:any) { alert(e?.message||'Error exportando YAML (¿pyyaml instalado?)') }
          }}>Exportar YAML</button>
          <button className="btn" onClick={()=> setImporting(true)}>Importar</button>
          <button 
            className="btn bg-red-600 hover:bg-red-700 text-white" 
            onClick={removeAll}
            title="⚠️ Eliminar TODAS las reglas (solo para testing)"
          >
            🗑️ Eliminar Todas
          </button>
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
      {importing && (
        <div className="card space-y-2">
          <div className="flex items-center justify-between">
            <div className="font-medium">Importar Reglas (JSON, YAML o CSV)</div>
            <button className="btn" onClick={()=> setImporting(false)}>Cerrar</button>
          </div>
          <div className="flex items-center gap-3">
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={csvMode} onChange={e=> setCsvMode(e.target.checked)} /> CSV (dictionary.csv)
            </label>
            <input type="file" accept=".csv,.json,.yaml,.yml" onChange={async (e:any)=>{
              try {
                const file = e.target.files?.[0]
                if (!file) return
                const text = await file.text()
                setImportText(text)
                const name = (file.name||'').toLowerCase()
                setCsvMode(name.endsWith('.csv'))
              } catch {}
            }} />
            <span className="text-xs text-muted">o pega el contenido abajo</span>
          </div>
          <details className="bg-white/5 p-2 rounded">
            <summary className="cursor-pointer text-sm">Formato de importación (ayuda)</summary>
            <div className="text-xs mt-2 space-y-2">
              <div>
                <div className="font-medium">CSV</div>
                <div>Columnas: <code>message_id, category, template_text</code>. Variantes con sufijo <code>_vN</code> se agrupan por el ID base.</div>
                <pre className="bg-white/5 p-2 overflow-x-auto">{`message_id,category,template_text\nregla_test_v1,general,Mensaje 1\nregla_test_v2,general,Mensaje 2`}</pre>
              </div>
              <div>
                <div className="font-medium">JSON (lista de reglas)</div>
                <pre className="bg-white/5 p-2 overflow-x-auto">{`[\n  {\n    "id": "regla_test",\n    "enabled": true,\n    "tenant_id": "default",\n    "category": "general",\n    "priority": 50,\n    "severity": 1,\n    "cooldown_days": 0,\n    "max_per_day": 0,\n    "tags": [],\n    "logic": {},\n    "messages": {\n      "locale": "es-ES",\n      "candidates": [ { "text": "Mensaje 1", "weight": 1 } ]\n    }\n  }\n]`}</pre>
              </div>
              <div>
                <div className="font-medium">YAML (equivalente al JSON anterior)</div>
                <pre className="bg-white/5 p-2 overflow-x-auto">{`- id: regla_test\n  enabled: true\n  tenant_id: default\n  category: general\n  priority: 50\n  severity: 1\n  cooldown_days: 0\n  max_per_day: 0\n  tags: []\n  logic: {}\n  messages:\n    locale: es-ES\n    candidates:\n      - text: "Mensaje 1"\n        weight: 1`}</pre>
              </div>
            </div>
          </details>
          <textarea className="w-full" rows={8} value={importText} onChange={e=> setImportText(e.target.value)} placeholder="Pega aquí JSON/YAML o CSV" />
          <div className="space-x-2">
            <button className="btn btn-primary" onClick={async()=>{
              try {
                if (!importText.trim()) return
                if (csvMode) {
                  await importRulesCsv(importText)
                } else {
                  const looksJson = importText.trim().startsWith('[')
                  await importRules(looksJson ? JSON.parse(importText) : importText, looksJson ? 'json' : 'yaml')
                }
                setImporting(false)
                setImportText('')
                setCsvMode(false)
                await load()
              } catch (e:any) { alert(e?.message||'Error importando') }
            }}>Subir</button>
          </div>
        </div>
      )}
    </main>
  )
}
