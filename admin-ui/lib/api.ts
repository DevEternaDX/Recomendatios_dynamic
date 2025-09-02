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
