export async function api<T>(path: string, body?: unknown, method: 'GET' | 'POST' | 'PUT' = 'POST'): Promise<T> {
  const init = body === undefined
    ? { method: 'GET' as const }
    : { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
  const response = await fetch(path, init)
  const raw = await response.text()
  let data: Record<string, unknown> = {}
  try { data = raw ? JSON.parse(raw) : {} } catch { throw new Error(raw.slice(0, 200) || response.statusText) }
  if (!response.ok) throw new Error(String(data.detail ?? data.error ?? response.statusText))
  return data as T
}
