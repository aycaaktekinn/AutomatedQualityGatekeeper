// Typed client for the REST API contract (OpenAPI at /docs).

export type Status = 'queued' | 'running' | 'completed' | 'partial' | 'failed'
export type CharacteristicName = 'maintainability' | 'security' | 'reliability'
export type SeverityName = 'low' | 'medium' | 'high'

export interface CharacteristicScore {
  value: number | null
  details: Record<string, number>
}

export interface ToolRun {
  tool: string
  version: string
  ok: boolean
  error: string | null
  findings: number
}

export interface Analysis {
  id: string
  repo_url: string
  status: Status
  commit_sha: string | null
  grade: string | null
  overall: number | null
  scores: Record<CharacteristicName, CharacteristicScore> | null
  tools: ToolRun[] | null
  stats: Record<string, number> | null
  error: string | null
  created_at: string
  finished_at: string | null
}

export interface Finding {
  tool: string
  rule_id: string
  characteristic: CharacteristicName
  severity: SeverityName
  file: string
  line: number
  message: string
  snippet: string
}

export const FINAL_STATUSES: Status[] = ['completed', 'partial', 'failed']

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // keep the generic message: the body was not JSON
    }
    throw new Error(detail)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

export const api = {
  createAnalysis: (repoUrl: string) =>
    request<{ id: string; status: Status }>('/api/analyses', {
      method: 'POST',
      body: JSON.stringify({ repo_url: repoUrl }),
    }),
  listAnalyses: () => request<Analysis[]>('/api/analyses'),
  getAnalysis: (id: string) => request<Analysis>(`/api/analyses/${encodeURIComponent(id)}`),
  history: (id: string) => request<Analysis[]>(`/api/analyses/${encodeURIComponent(id)}/history`),
  findings: (id: string, filters: { characteristic?: string; severity?: string; file?: string }) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value))
    return request<Finding[]>(`/api/analyses/${encodeURIComponent(id)}/findings?${params}`)
  },
  deleteAnalysis: (id: string) =>
    request<void>(`/api/analyses/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
