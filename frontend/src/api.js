import { BASE_URL } from './config.js'
import { getToken, setToken, clearToken } from './auth.js'

async function request(path, { method = 'GET', body } = {}) {
  const token = getToken()
  let response
  try {
    response = await fetch(BASE_URL + path, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      ...(body !== undefined && { body: JSON.stringify(body) }),
    })
  } catch {
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

  async farms() {
    const farms = await request('/farms')
    return Promise.all(farms.map(async (farm) => ({
      ...farm,
      plots: await request(`/farms/${farm.id}/plots`),
    })))
  },
  createFarm: (body) => request('/farms', { method: 'POST', body }),
  createPlot: (farmId, body) => request(`/farms/${farmId}/plots`, { method: 'POST', body }),
  cropSeasons: (plotId) => request(`/plots/${plotId}/crop-seasons`),
  createCropSeason: (plotId, body) => request(`/plots/${plotId}/crop-seasons`, { method: 'POST', body }),

  operations: ({ plotId, dateFrom, dateTo } = {}) => {
    const params = new URLSearchParams()
    if (plotId) params.set('plot_id', plotId)
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    return request(`/operations${params.size ? `?${params}` : ''}`)
  },
  operation: (id) => request(`/operations/${id}`),
  updateOperation: (id, body) => request(`/operations/${id}`, { method: 'PATCH', body }),
  createOperation: (plotId, body) => request(`/plots/${plotId}/operations`, { method: 'POST', body }),
  reminders: (operationId) => request(`/operations/${operationId}/reminders`),
  createReminder: (operationId, body) =>
    request(`/operations/${operationId}/reminders`, { method: 'POST', body }),

  async upcomingTasks() {
    const today = new Date()
    today.setMinutes(today.getMinutes() - today.getTimezoneOffset())
    const operations = await api.operations({ dateFrom: today.toISOString().slice(0, 10) })
    return operations
      .filter((operation) => ['planned', 'in_progress'].includes(operation.status))
      .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date))
      .slice(0, 3)
      .map((operation) => ({
        id: operation.id, title: operation.title, date: operation.scheduled_date,
      }))
  },

  notifications: () => request('/notifications'),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: 'POST' }),
}
