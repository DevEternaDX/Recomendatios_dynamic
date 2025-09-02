"use client"

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { getRule, updateRule } from '@/lib/api'

function ConditionRow({ cond, onChange, onDelete }: { cond: any; onChange: (v:any)=>void; onDelete: ()=>void }) {
  return (
    <div className="flex gap-2 items-center">
      <input className="w-40" placeholder="var" value={cond.var || ''} onChange={e => onChange({ ...cond, var: e.target.value })} />
      <select value={cond.agg || 'current'} onChange={e => onChange({ ...cond, agg: e.target.value })}>
        {['current','mean_3d','mean_7d','mean_14d','median_14d','delta_pct_3v14','zscore_28d'].map(a => <option key={a} value={a}>{a}</option>)}
      </select>
      <select value={cond.op || '>'} onChange={e => onChange({ ...cond, op: e.target.value })}>
        {['<','<=','>','>=','==','between','in'].map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      <input className="w-40" placeholder="valor" value={cond.value ?? ''} onChange={e => onChange({ ...cond, value: parseValue(e.target.value) })} />
      <button className="btn" onClick={onDelete}>Eliminar</button>
    </div>
  )
}

function parseValue(s: string) {
  if (s.includes(',')) return s.split(',').map(x => x.trim()).map(Number)
  const n = Number(s)
  return isNaN(n) ? s : n
}

function GroupEditor({ node, onChange }: { node:any; onChange: (v:any)=>void }) {
  if (node.all) {
    return <Group type="all" items={node.all} onChange={items => onChange({ all: items })} />
  } else if (node.any) {
    return <Group type="any" items={node.any} onChange={items => onChange({ any: items })} />
  } else if (node.none) {
    return <Group type="none" items={node.none} onChange={items => onChange({ none: items })} />
  }
  return <ConditionRow cond={node} onChange={onChange} onDelete={() => onChange(null)} />
}

function Group({ type, items, onChange }: { type: 'all'|'any'|'none'; items:any[]; onChange:(v:any[])=>void }) {
  function addCondition() {
    onChange([...(items||[]), { var:'', agg:'current', op:'>', value:0 }])
  }
  function addGroup(kind: 'all'|'any'|'none') {
    onChange([...(items||[]), { [kind]: [] }])
  }
  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <span className="px-2 py-1 rounded bg-white/10 uppercase text-xs">{type}</span>
        <button className="btn" onClick={addCondition}>+ condición</button>
        <button className="btn" onClick={() => addGroup('all')}>+ ALL</button>
        <button className="btn" onClick={() => addGroup('any')}>+ ANY</button>
        <button className="btn" onClick={() => addGroup('none')}>+ NONE</button>
      </div>
      <div className="space-y-3">
        {(items||[]).map((child, idx) => (
          <GroupEditor key={idx} node={child} onChange={v => {
            const next = [...items]
            if (v === null) next.splice(idx, 1)
            else next[idx] = v
            onChange(next)
          }} />
        ))}
      </div>
    </div>
  )
}

export default function RuleEditorPage() {
  const params = useParams() as { id: string }
  const router = useRouter()
  const [data, setData] = useState<any | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      const r = await getRule(params.id)
      setData(r)
    })()
  }, [params.id])

  async function save() {
    if (!data) return
    setSaving(true)
    setError(null)
    try {
      await updateRule(data.id, {
        enabled: data.enabled,
        category: data.category,
        priority: data.priority,
        severity: data.severity,
        cooldown_days: data.cooldown_days,
        max_per_day: data.max_per_day,
        tags: data.tags,
        logic: data.logic,
        messages: data.messages,
      })
      alert('Guardado')
      router.push('/rules')
    } catch (e:any) {
      setError(e?.message || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  if (!data) return <main className="p-6 text-muted">Cargando…</main>

  return (
    <main className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Editar Regla: <span className="font-mono">{data.id}</span></h1>
        <div className="space-x-2">
          <Link href="/rules" className="btn">Volver</Link>
          <button className="btn btn-primary" onClick={save} disabled={saving}>Guardar</button>
        </div>
      </div>
      {error && <div className="text-red-400">{error}</div>}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1 space-y-3 card">
          <div>
            <label className="block text-sm">Categoría</label>
            <input className="w-full" value={data.category || ''} onChange={e => setData({ ...data, category: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm">Tenant</label>
            <input className="w-full" value={data.tenant_id || ''} onChange={e => setData({ ...data, tenant_id: e.target.value })} />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-sm">Priority</label>
              <input type="number" className="w-full" value={data.priority} onChange={e => setData({ ...data, priority: Number(e.target.value) })} />
            </div>
            <div>
              <label className="block text-sm">Severity</label>
              <input type="number" className="w-full" value={data.severity} onChange={e => setData({ ...data, severity: Number(e.target.value) })} />
            </div>
            <div>
              <label className="block text-sm">Cooldown</label>
              <input type="number" className="w-full" value={data.cooldown_days} onChange={e => setData({ ...data, cooldown_days: Number(e.target.value) })} />
            </div>
          </div>
          <div>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={data.enabled} onChange={e => setData({ ...data, enabled: e.target.checked })} />
              Habilitada
            </label>
          </div>
        </div>
        <div className="md:col-span-2 space-y-4">
          <div className="card">
            <h2 className="font-medium mb-2">Lógica</h2>
            <GroupEditor node={data.logic} onChange={v => setData({ ...data, logic: v })} />
          </div>
          <div className="card">
            <h2 className="font-medium mb-2">Mensajes</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(data.messages?.candidates || []).map((c:any, idx:number) => (
                <div key={idx} className="card">
                  <div className="text-xs text-muted">Weight {c.weight}</div>
                  <textarea className="w-full mt-1" rows={4} value={c.text} onChange={e => {
                    const next = { ...data }
                    next.messages.candidates[idx].text = e.target.value
                    setData(next)
                  }} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
