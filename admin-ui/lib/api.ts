import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

export const api = axios.create({ baseURL: API_BASE })

export async function listRules(params?: { enabled?: boolean; category?: string; q?: string }) {
  const { data } = await api.get('/rules', { params })
  return data as any[]
}

export async function getRule(id: string) {
  const { data } = await api.get(`/rules/${id}`)
  return data as any
}

export async function createRule(rule: any) {
  const { data } = await api.post('/rules', { rule })
  return data as { id: string }
}

export async function updateRule(id: string, patch: any) {
  const { data } = await api.put(`/rules/${id}`, patch)
  return data as { id: string }
}

export async function enableRule(id: string, enabled: boolean) {
  const { data } = await api.post(`/rules/${id}/enable`, { enabled })
  return data as { id: string; enabled: boolean }
}

export async function cloneRule(id: string, newId: string) {
  const { data } = await api.post(`/rules/${id}/clone`, { new_id: newId })
  return data as { id: string }
}

export async function deleteRule(id: string) {
  const { data } = await api.delete(`/rules/${id}`)
  return data as { id: string; deleted: boolean }
}

// Variants granular API
export async function addVariant(ruleId: string, body: { text: string; weight?: number; active?: boolean; locale?: string }) {
  const { data } = await api.post(`/rules/${ruleId}/variants`, body)
  return data as { message_id: number }
}

export async function patchVariant(ruleId: string, messageId: number, body: { text?: string; weight?: number; active?: boolean }) {
  const { data } = await api.patch(`/rules/${ruleId}/variants/${messageId}`, body)
  return data as { message_id: number }
}

export async function deleteVariant(ruleId: string, messageId: number) {
  const { data } = await api.delete(`/rules/${ruleId}/variants/${messageId}`)
  return data as { message_id: number; deleted: boolean }
}

// Import/Export and Stats
export async function exportRules(format: 'json'|'yaml' = 'json') {
  const { data } = await api.get('/rules/export', { params: { format } })
  return data
}

export async function importRules(payload: any, format: 'json'|'yaml' = 'json') {
  const { data } = await api.post('/rules/import', { data: payload, format })
  return data as { created: string[] }
}

export async function getRuleStats(ruleId: string) {
  const { data } = await api.get(`/rules/${ruleId}/stats`)
  return data as { rule_id: string; fires: number; by_message: Record<string, number> }
}

export async function getRuleChangelog(ruleId: string, limit = 50) {
  const { data } = await api.get(`/rules/${ruleId}/changelog`, { params: { limit } })
  return data as Array<{ id: number; created_at: string; user?: string; role?: string; action: string; before: any; after: any }>
}

export async function getTriggersSeries(startISO: string, endISO: string, ruleIds?: string[]) {
  const params: any = { start: startISO, end: endISO }
  if (ruleIds && ruleIds.length) params.rule_ids = ruleIds.join(',')
  const { data } = await api.get('/analytics/triggers', { params })
  return data as { start: string; end: string; series: Array<{ rule_id: string; points: Array<{ date: string; count: number }> }> }
}

export async function importRulesCsv(csvText: string, opts?: { tenant_id?: string; locale?: string; replace?: boolean; enable?: boolean; default_priority?: number; default_severity?: number }) {
  const { data } = await api.post('/rules/import_csv', {
    csv_text: csvText,
    tenant_id: opts?.tenant_id,
    locale: opts?.locale,
    replace: opts?.replace ?? true,
    enable: opts?.enable ?? false,
    default_priority: opts?.default_priority ?? 50,
    default_severity: opts?.default_severity ?? 1,
  })
  return data as { created: string[]; updated: string[] }
}

export async function listVariables() {
  const { data } = await api.get('/variables')
  return data as any[]
}

export async function upsertVariable(v: any) {
  const { data } = await api.post('/variables', v)
  return data
}

export async function simulate(user_id: string, dateISO: string, tenant_id?: string, debug?: boolean) {
  const { data } = await api.post('/simulate', { user_id, date: dateISO, tenant_id, debug })
  return data
}

export async function simulateRange(user_id: string, startISO: string, endISO: string, tenant_id?: string, debug?: boolean) {
  const days: string[] = []
  const start = new Date(startISO)
  const end = new Date(endISO)
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    days.push(d.toISOString().slice(0,10))
  }
  // Ejecutar en serie para no saturar backend
  const results: any[] = []
  for (const day of days) {
    const { data } = await api.post('/simulate', { user_id, date: day, tenant_id, debug })
    results.push({ date: day, ...data })
  }
  return results
}
