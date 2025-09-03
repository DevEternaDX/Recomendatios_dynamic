"use client"

import { useEffect, useState } from 'react'
import { createRule, listVariables } from '@/lib/api'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function NewRulePage() {
  const router = useRouter()
  const [vars, setVars] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<any>({
    id: '',
    tenant_id: 'default',
    category: '',
    priority: 50,
    severity: 1,
    cooldown_days: 0,
    max_per_day: 0,
    enabled: false,
    logic: { all: [] as any[] },
    messages: { locale: 'es-ES', candidates: [{ text: 'Mensaje', weight: 1 }] },
  })

  useEffect(() => {
    (async () => {
      try { setVars(await listVariables()) } catch {}
    })()
  }, [])

  function addCondition() {
    setForm((f:any) => ({ ...f, logic: { all: [ ...(f.logic?.all||[]), { var: '', agg: 'current', op: '>', value: 0 } ] } }))
  }

  function parseValue(op: string, raw: string) {
    const s = (raw||'').trim()
    if (op === 'between' || op === 'in') {
      const parts = s.split(',').map(t => t.trim()).filter(Boolean)
      return parts.map(p => {
        const n = Number(p)
        return isNaN(n) ? p : n
      })
    }
    const n = Number(s)
    return isNaN(n) ? s : n
  }

  async function save() {
    setSaving(true)
    setError(null)
    try {
      if (!form.id) throw new Error('ID requerido')
      const payload = {
        id: form.id,
        enabled: !!form.enabled,
        tenant_id: form.tenant_id || 'default',
        category: form.category || 'general',
        priority: Number(form.priority)||0,
        severity: Number(form.severity)||1,
        cooldown_days: Number(form.cooldown_days)||0,
        max_per_day: Number(form.max_per_day)||0,
        tags: [],
        logic: form.logic,
        messages: form.messages,
      }
      await createRule(payload)
      router.push('/rules')
    } catch (e:any) {
      setError(e?.message || 'Error al crear')
    } finally { setSaving(false) }
  }

  return (
    <main className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Nueva Regla</h1>
        <div className="space-x-2">
          <Link href="/rules" className="btn">Volver</Link>
          <button className="btn btn-primary" onClick={save} disabled={saving}>Crear</button>
        </div>
      </div>
      {error && <div className="text-red-400">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="space-y-3 card">
          <div>
            <label className="block text-sm">ID</label>
            <input className="w-full" value={form.id} onChange={e=>setForm({...form,id:e.target.value})} />
          </div>
          <div>
            <label className="block text-sm">Tenant</label>
            <input className="w-full" value={form.tenant_id} onChange={e=>setForm({...form,tenant_id:e.target.value})} />
          </div>
          <div>
            <label className="block text-sm">Categoría</label>
            <input className="w-full" value={form.category} onChange={e=>setForm({...form,category:e.target.value})} />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-sm">Priority</label>
              <input type="number" className="w-full" value={form.priority} onChange={e=>setForm({...form,priority:Number(e.target.value)})} />
            </div>
            <div>
              <label className="block text-sm">Severity</label>
              <input type="number" className="w-full" value={form.severity} onChange={e=>setForm({...form,severity:Number(e.target.value)})} />
            </div>
            <div>
              <label className="block text-sm">Cooldown</label>
              <input type="number" className="w-full" value={form.cooldown_days} onChange={e=>setForm({...form,cooldown_days:Number(e.target.value)})} />
            </div>
          </div>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.enabled} onChange={e=>setForm({...form,enabled:e.target.checked})} />
            Habilitada
          </label>
        </div>
        <div className="md:col-span-2 space-y-4">
          <div className="card">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-medium">Lógica</h2>
              <button className="btn" onClick={addCondition}>+ condición</button>
            </div>
            <div className="space-y-3">
              {(form.logic?.all||[]).map((cond:any, idx:number)=> (
                <div key={idx} className="flex gap-2 items-center">
                  <select className="w-48" value={cond.var||''} onChange={e=>{
                    const next=[...form.logic.all]; next[idx]={...cond,var:e.target.value}; setForm({...form,logic:{all:next}})
                  }}>
                    <option value="">-- variable --</option>
                    {vars.map(v=> <option key={v.key} value={v.key}>{v.key}</option>)}
                  </select>
                  <select value={cond.agg||'current'} onChange={e=>{ const next=[...form.logic.all]; next[idx]={...cond,agg:e.target.value}; setForm({...form,logic:{all:next}}) }}>
                    {['current','mean_3d','mean_7d','mean_14d','median_14d','delta_pct_3v14','zscore_28d'].map(a=> <option key={a} value={a}>{a}</option>)}
                  </select>
                  <select value={cond.op||'>'} onChange={e=>{ const next=[...form.logic.all]; next[idx]={...cond,op:e.target.value}; setForm({...form,logic:{all:next}}) }}>
                    {['<','<=','>','>=','==','between','in'].map(o=> <option key={o} value={o}>{o}</option>)}
                  </select>
                  <input className="w-40" placeholder={(cond.op==='between'||cond.op==='in')? 'v1,v2' : 'valor'} value={Array.isArray(cond.value)? cond.value.join(',') : (cond.value??'').toString()} onChange={e=>{ const next=[...form.logic.all]; next[idx]={...cond,value: parseValue(cond.op||'>', e.target.value)}; setForm({...form,logic:{all:next}}) }} />
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <h2 className="font-medium mb-2">Mensajes</h2>
            <div className="space-y-3">
              {(form.messages?.candidates||[]).map((cand:any, idx:number)=> (
                <div key={idx} className="flex items-start gap-2">
                  <textarea className="w-full" rows={3} value={cand.text} onChange={e=>{
                    const next={...form};
                    const arr=[...(next.messages?.candidates||[])];
                    arr[idx] = { ...arr[idx], text: e.target.value };
                    next.messages = { ...(next.messages||{locale:'es-ES',candidates:[]}), candidates: arr };
                    setForm(next)
                  }} />
                  <div className="w-28">
                    <label className="block text-sm">Peso</label>
                    <input type="number" className="w-full" value={cand.weight||1} onChange={e=>{
                      const next={...form};
                      const arr=[...(next.messages?.candidates||[])];
                      arr[idx] = { ...arr[idx], weight: Number(e.target.value)||1 };
                      next.messages = { ...(next.messages||{locale:'es-ES',candidates:[]}), candidates: arr };
                      setForm(next)
                    }} />
                    <button className="btn w-full mt-2" onClick={()=>{
                      const next={...form};
                      const arr=[...(next.messages?.candidates||[])];
                      arr.splice(idx,1);
                      next.messages = { ...(next.messages||{locale:'es-ES',candidates:[]}), candidates: arr.length? arr : [{ text: 'Mensaje', weight: 1 }] };
                      setForm(next)
                    }}>Eliminar</button>
                  </div>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <button className="btn" onClick={()=>{
                  const next={...form};
                  const arr=[...(next.messages?.candidates||[])];
                  arr.push({ text: 'Nueva variante', weight: 1 });
                  next.messages = { ...(next.messages||{locale:'es-ES',candidates:[]}), candidates: arr };
                  setForm(next)
                }}>+ variante</button>
                <div className="flex items-center gap-2">
                  <span className="text-sm">Locale</span>
                  <input className="w-28" value={form.messages?.locale||'es-ES'} onChange={e=>{
                    const next={...form};
                    next.messages = { ...(next.messages||{candidates:[]}), locale: e.target.value, candidates: next.messages?.candidates||[{text:'Mensaje',weight:1}] };
                    setForm(next)
                  }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}


