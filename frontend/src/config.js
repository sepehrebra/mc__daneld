// اطلاعات برند: بعداً اسم واقعی و لینک مقصد را اینجا بگذار.
export const BRAND = {
  name: 'مزرعه‌یار',   // نام شرکت
  href: '/',           // مقصد لینک لوگو و نام شرکت (بعداً عوض کن)
}

// آدرس API جنگو. می‌توانی در فایل .env بنویسی: VITE_API_URL=https://...
export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// true = داده‌های آزمایشی نمایش داده می‌شود (بدون بک‌اند).
// وقتی بک‌اند آماده شد، false کن.
export const USE_MOCK = true
