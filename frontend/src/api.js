const BASE = '/api'

async function request(path) {
  const response = await fetch(BASE + path)
  if (!response.ok) throw new Error(`${path} -> ${response.status}`)
  return response.json()
}

export const api = {
  status: () => request('/system/status'),
  experiments: (limit = 100) => request(`/experiments?limit=${limit}`),
  measurements: (runId, limit = 800) =>
    request(`/measurements?limit=${limit}${runId ? `&run_id=${runId}` : ''}`),
  predictions: (runId, limit = 200) =>
    request(`/predictions?limit=${limit}${runId ? `&run_id=${runId}` : ''}`),
  events: (limit = 10) => request(`/events?limit=${limit}`),
}
