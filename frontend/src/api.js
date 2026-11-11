import { BASE_URL } from './config.js'
import { getToken, setToken, clearToken } from './auth.js'

async function request(path, { method = 'GET', body, signal } = {}) {
  const token = getToken()
  let response
  try {
    response = await fetch(BASE_URL + path, {
      method,
      signal,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      ...(body !== undefined && { body: JSON.stringify(body) }),
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new Error('ارتباط با سرور برقرار نشد. اجرای بک‌اند را بررسی کن.')
  }

  if (response.status === 401 && token) {
    clearToken()
    window.location.href = '/login'
    throw new Error('نشست منقضی شده است. دوباره وارد شو.')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail
    throw new Error(typeof detail === 'string' ? detail : 'درخواست انجام نشد. دوباره تلاش کن.')
  }
  return response.status === 204 ? null : response.json()
}

export const api = {
  async register({ name, phone, password }) {
    return request('/auth/register', {
      method: 'POST', body: { full_name: name.trim(), phone, password },
    })
  },

  async login({ phone, password }) {
    const data = await request('/auth/login', { method: 'POST', body: { phone, password } })
    setToken(data.access_token)
    return data
  },

  async logout() {
    try {
      if (getToken()) await request('/auth/logout', { method: 'POST' })
    } finally {
      clearToken()
    }
  },

  farms: () => request('/farms'),
  farm: (id) => request(`/farms/${id}`),
  createFarm: (body) => request('/farms', { method: 'POST', body }),
  createPlot: (farmId, body) => request(`/farms/${farmId}/plots`, { method: 'POST', body }),

  operations: (filters = {}, signal) => {
    const params = new URLSearchParams()
    for (const key of ['from', 'to', 'farm', 'plot', 'status', 'sort', 'order', 'limit', 'offset']) {
      if (filters[key] != null && filters[key] !== '') params.set(key, filters[key])
    }
    return request(`/operations${params.size ? `?${params}` : ''}`, { signal })
  },
  async operation(id, plot, signal) {
    // The Django contract exposes individual items through the collection.
    const limit = 100
    for (let offset = 0; !signal?.aborted; offset += limit) {
      const items = await api.operations({ plot, sort: 'created', limit, offset }, signal)
      const item = items.find((operation) => String(operation.id) === String(id))
      if (item) return item
      if (items.length < limit) break
    }
    throw new Error('عملیات پیدا نشد.')
  },
  updateOperation: (id, body) => request(`/operations/${id}`, { method: 'PATCH', body }),
  createOperation: (plotId, body) => request('/operations', { method: 'POST', body: { ...body, plot_id: Number(plotId) } }),

  async upcomingTasks() {
    const operations = await api.operations({ status: 'planned,in_progress', order: 'asc', limit: 3 })
    return operations.map(({ id, title, scheduled_date }) => ({ id, title, date: scheduled_date }))
  },
}
