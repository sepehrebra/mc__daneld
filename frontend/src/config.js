// اطلاعات برند: بعداً اسم واقعی و لینک مقصد را اینجا بگذار.
export const BRAND = {
  name: 'مزرعه‌یار',   // نام شرکت
  href: '/',           // مقصد لینک لوگو و نام شرکت (بعداً عوض کن)
}

// در توسعه، Vite مسیر /api را به بک‌اند محلی می‌فرستد.
// برای سرور جداگانه، VITE_API_URL را روی آدرس کامل /api/v1 تنظیم کن.
export const BASE_URL = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
