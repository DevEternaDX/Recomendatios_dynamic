"use client"

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { getTriggersSeries, listRules } from '@/lib/api'

type SeriesPoint = { date: string; count: number }

export default function StatsPage() {
  const [startISO, setStartISO] = useState(() => {
    const d = new Date(); d.setDate(d.getDate()-7); return d.toISOString().slice(0,10)
  })
  const [endISO, setEndISO] = useState(() => new Date().toISOString().slice(0,10))
  const [allRules, setAllRules] = useState<any[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [data, setData] = useState<{ series: { rule_id: string; points: SeriesPoint[] }[] } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      try { setAllRules(await listRules()) } catch {}
    })()
  }, [])

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const res = await getTriggersSeries(startISO, endISO, selected)
      setData(res)
    } catch (e:any) {
      setError(e?.message || 'Error')
    } finally {
      setLoading(false)
    }
  }

  const dates = useMemo(()=>{
    if (!data?.series?.[0]) return [] as string[]
    return data.series[0].points.map(p=>p.date)
  }, [data])

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Estadísticas</h1>
        <Link href="/" className="btn">Volver</Link>
      </div>

      <div className="card grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
        <div>
          <label className="block text-sm">Desde</label>
          <input type="date" value={startISO} onChange={e=> setStartISO(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm">Hasta</label>
          <input type="date" value={endISO} onChange={e=> setEndISO(e.target.value)} />
        </div>
        <div className="md:col-span-2">
          <label className="block text-sm">Reglas</label>
          <div className="flex flex-wrap gap-2 max-h-40 overflow-auto p-2 bg-white/5 rounded">
            {allRules.map(r => {
              const checked = selected.includes(r.id)
              return (
                <label key={r.id} className="inline-flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={checked} onChange={e=>{
                    setSelected(prev => e.target.checked ? [...prev, r.id] : prev.filter(x=>x!==r.id))
                  }} />
                  <span className="font-mono">{r.id}</span>
                </label>
              )
            })}
          </div>
        </div>
        <div className="md:col-span-4">
          <button className="btn btn-primary" onClick={run} disabled={loading}>Actualizar</button>
        </div>
      </div>

      {loading && <div className="text-muted">Cargando…</div>}
      {error && <div className="text-red-400">{error}</div>}

      {data && (
        <div className="card overflow-x-auto">
          <Chart series={data.series} />
        </div>
      )}
    </main>
  )
}

function Chart({ series }: { series: { rule_id: string; points: { date: string; count: number }[] }[] }) {
  const padding = { left: 40, right: 12, top: 12, bottom: 28 }
  const dates = series[0]?.points?.map(p=>p.date) || []
  const width = Math.max(640, padding.left + padding.right + dates.length * 40)
  const height = 320
  const maxY = Math.max(1, ...series.flatMap(s=> s.points.map(p=> p.count)))

  function x(i: number) { return padding.left + i * 40 }
  function y(v: number) {
    const innerH = height - padding.top - padding.bottom
    return padding.top + (innerH - (v / maxY) * innerH)
  }

  const palette = ['#22d3ee','#a78bfa','#34d399','#f472b6','#fbbf24','#60a5fa','#f87171']

  return (
    <svg width={width} height={height} className="min-w-[640px]">
      {/* Ejes */}
      <line x1={padding.left} y1={y(0)} x2={width - padding.right} y2={y(0)} stroke="rgba(255,255,255,0.2)" />
      <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="rgba(255,255,255,0.2)" />
      {/* Ticks Y */}
      {[0, 0.25, 0.5, 0.75, 1].map((t,i)=>{
        const val = Math.round(maxY * t)
        const yy = y(val)
        return (
          <g key={i}>
            <line x1={padding.left} y1={yy} x2={width - padding.right} y2={yy} stroke="rgba(255,255,255,0.06)" />
            <text x={padding.left - 8} y={yy} dy="0.32em" textAnchor="end" className="fill-white/60 text-[10px]">{val}</text>
          </g>
        )
      })}
      {/* Labels X */}
      {dates.map((d, i)=> (
        <text key={d} x={x(i)} y={height - padding.bottom + 14} textAnchor="middle" className="fill-white/60 text-[10px]">{d.slice(5)}</text>
      ))}
      {/* Series */}
      {series.map((s, si)=> {
        const color = palette[si % palette.length]
        const path = s.points.map((p,i)=> `${i===0?'M':'L'} ${x(i)} ${y(p.count)}`).join(' ')
        return (
          <g key={s.rule_id}>
            <path d={path} fill="none" stroke={color} strokeWidth={2} />
            {s.points.map((p,i)=> (
              <circle key={i} cx={x(i)} cy={y(p.count)} r={3} fill={color} />
            ))}
            <text x={width - padding.right} y={y(s.points[s.points.length-1]?.count||0)} dx={-4} dy={-4} textAnchor="end" className="fill-white/80 text-[10px] font-mono">{s.rule_id}</text>
          </g>
        )
      })}
      {/* Título ejes */}
      <text x={padding.left} y={padding.top - 2} className="fill-white/80 text-[11px]">Triggers / día</text>
      <text x={width - padding.right} y={height - 4} textAnchor="end" className="fill-white/80 text-[11px]">Fecha</text>
    </svg>
  )
}


