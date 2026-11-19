import { BASE_URL } from './config.js'
import { getToken, setSession, clearSession } from './auth.js'

// آدرس endpointها (بعد از BASE_URL که شامل /api/v1 است).
// اگر با بک‌اند فرق داشت فقط همین‌جا عوض کن.
const ENDPOINTS = {
  register: '/auth/register',
  login: '/auth/login',
  me: '/auth/me',
  logout: '/auth/logout',
  farms: '/farms',
  plots: '/plots',
  operations: '/operations',
  upcomingTasks: '/operations?status=planned,in_progress&order=asc&limit=3', // نزدیک‌ترین‌ها اول
  recentOperations: '/operations?limit=5&sort=created', // آخرین ثبت‌شده‌ها اول
}

class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

// auth=false برای درخواست‌هایی که توکن ندارند (ثبت‌نام و ورود)
async function request(path, { method = 'GET', body, auth = true } = {}) {
  const token = auth ? getToken() : null
  const res = await fetch(BASE_URL + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: body && JSON.stringify(body),
  })

  // توکن نامعتبر یا منقضی: به صفحه‌ی ورود برگرد
  if (res.status === 401 && auth) {
    clearSession()
    window.location.href = '/login'
    throw new ApiError(401, 'نشست تمام شده؛ دوباره وارد شو.')
  }
  if (!res.ok) throw new ApiError(res.status, 'مشکلی پیش آمد. دوباره تلاش کن.')
  return res.status === 204 ? null : res.json()
}

// پیام فارسی مناسب هر کد خطا را روی خطا می‌گذارد و دوباره پرتاب می‌کند
const withMessages = (messages) => (e) => {
  if (messages[e.status]) e.message = messages[e.status]
  throw e
}

const farmUrl = (id) => `${ENDPOINTS.farms}/${id}`
const plotUrl = (id) => `${ENDPOINTS.plots}/${id}`
const operationUrl = (id) => `${ENDPOINTS.operations}/${id}`
const DUPLICATE_PLOT = { 409: 'نام یا کد این قطعه در مزرعه تکراری است.' }

export const api = {
  // ---------- احراز هویت ----------
  // body: { full_name, phone (E.164), password, email? }  ->  201
  register: (body) =>
    request(ENDPOINTS.register, { method: 'POST', body, auth: false }).catch(
      withMessages({ 409: 'این شماره یا ایمیل قبلاً ثبت شده است.', 422: 'اطلاعات واردشده معتبر نیست. دوباره بررسی کن.' })
    ),

  // body: { phone (E.164), password }  ->  { access_token, expires_at }
  async login(body) {
    const data = await request(ENDPOINTS.login, { method: 'POST', body, auth: false }).catch(
      withMessages({ 401: 'شماره یا رمز عبور اشتباه است.', 422: 'اطلاعات واردشده معتبر نیست.' })
    )
    setSession({ token: data.access_token, expiresAt: data.expires_at })
  },

  // پاسخ: { full_name, phone, ... }
  me: () => request(ENDPOINTS.me),

  // نشست در بک‌اند باطل می‌شود (204)؛ حتی اگر درخواست خطا بدهد، نشست محلی پاک می‌شود
  async logout() {
    try {
      await request(ENDPOINTS.logout, { method: 'POST' })
    } catch {
      /* مهم نیست */
    } finally {
      clearSession()
    }
  },

  // ---------- مزرعه‌ها ----------
  // پاسخ: [{ id, name, plots: [{ id, name }] }]
  farms: () => request(ENDPOINTS.farms),

  // GET /farms/{id}: مزرعه + قطعه‌ها (ستون‌های جدول farms) و برای هر قطعه:
  // { id, name, code, area_m2, soil_type, description,
  //   today_count, overdue_count, current_season, next_operation, last_irrigation_at }
  farm: (id) => request(farmUrl(id)).catch(withMessages({ 404: 'این مزرعه پیدا نشد.' })),

  // POST /farms: { name, address?, description? }
  createFarm: (body) => request(ENDPOINTS.farms, { method: 'POST', body }),

  // PATCH /farms/{id}: { name, province, city, address, latitude, longitude, description }  (null = پاک کردن)
  updateFarm: (id, body) => request(farmUrl(id), { method: 'PATCH', body }),

  // ---------- قطعه‌ها ----------
  // GET /plots/{id}: ستون‌های جدول plots به‌علاوه‌ی
  // { farm, today_count, overdue_count, current_season, last_done, next_operations, recent_operations }
  plot: (id) => request(plotUrl(id)).catch(withMessages({ 404: 'این قطعه پیدا نشد.' })),

  // POST /farms/{id}/plots: { name, code?, area_m2, soil_type?, description? }
  createPlot: (farmId, body) =>
    request(`${farmUrl(farmId)}/plots`, { method: 'POST', body }).catch(withMessages(DUPLICATE_PLOT)),

  // PATCH /plots/{id}: { name, code, area_m2, soil_type, description }  (null = پاک کردن)
  updatePlot: (id, body) => request(plotUrl(id), { method: 'PATCH', body }).catch(withMessages(DUPLICATE_PLOT)),

  // ---------- عملیات ----------
  // شکل هر عملیات در همه‌ی پاسخ‌ها:
  // { id, title, operation_type, description, scheduled_date, scheduled_time, status,
  //   completed_date, farm: {id, name}, plot: {id, name} }
  upcomingTasks: () => request(ENDPOINTS.upcomingTasks),
  recentOperations: () => request(ENDPOINTS.recentOperations),

  // POST /operations: { plot_id, operation_type, title, scheduled_date, scheduled_time?, description?,
  //                     crop_name?, variety?, status?, completed_date? }
  createOperation: (body) => request(ENDPOINTS.operations, { method: 'POST', body }),

  // PATCH /operations/{id}: فقط فیلدهای تغییرکرده؛ null یعنی پاک کردن
  updateOperation: (id, body) => request(operationUrl(id), { method: 'PATCH', body }),

  // DELETE /operations/{id}  ->  204
  deleteOperation: (id) => request(operationUrl(id), { method: 'DELETE' }),

  // GET /operations/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD
  calendarOperations: (from, to) => request(`${ENDPOINTS.operations}/calendar?from=${from}&to=${to}`),

  // GET /operations?from&to&farm&plot&status&order&limit&offset
  searchOperations(params) {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    return request(`${ENDPOINTS.operations}?${qs}`)
  },
}
