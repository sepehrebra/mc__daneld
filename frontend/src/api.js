import { BASE_URL, USE_MOCK } from './config.js'
import { getToken, setToken, clearToken } from './auth.js'
import { mockTasks, mockFarms } from './mock.js'

// آدرس endpointهای جنگو: اگر با بک‌اند فرق داشت فقط همین‌جا عوض کن.
const ENDPOINTS = {
  login: '/auth/login/',
  upcomingTasks: '/tasks/upcoming/?limit=3',
  farms: '/farms/',
  operations: '/operations/',
}

const wait = (data) => new Promise((res) => setTimeout(() => res(data), 400))

async function request(path, { method = 'GET', body } = {}) {
  const token = getToken()
  const res = await fetch(BASE_URL + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: body && JSON.stringify(body),
  })

  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('دوباره وارد شو.')
  }
  if (!res.ok) throw new Error('مشکلی پیش آمد. دوباره تلاش کن.')
  return res.status === 204 ? null : res.json()
}

export const api = {
  // body: { phone, password }  ->  پاسخ: { access: "..." }
  async login(body) {
    if (USE_MOCK) {
      setToken('mock-token')
      return wait()
    }
    const data = await request(ENDPOINTS.login, { method: 'POST', body })
    setToken(data.access)
  },

  // پاسخ: [{ id, title, date: "2026-10-07" }]
  upcomingTasks: () =>
    USE_MOCK ? wait(mockTasks) : request(ENDPOINTS.upcomingTasks),

  // پاسخ: [{ id, name, plots: [{ id, name }] }]
  farms: () => (USE_MOCK ? wait(mockFarms) : request(ENDPOINTS.farms)),

  // body: { name, start_date, end_date | null, farm, plot }
  createOperation: (body) =>
    USE_MOCK ? wait({ ...body, id: 1 }) : request(ENDPOINTS.operations, { method: 'POST', body }),
}
