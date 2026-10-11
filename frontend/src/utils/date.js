import DateObjectModule from 'react-date-object'
import gregorian from 'react-date-object/calendars/gregorian'
import gregorian_en from 'react-date-object/locales/gregorian_en'

const DateObject = DateObjectModule.default ?? DateObjectModule

// تاریخ انتخاب‌شده (شمسی) -> "2026-10-07" برای ارسال به جنگو
export function toISO(date) {
  if (!date) return null
  return new DateObject(date).convert(gregorian, gregorian_en).format('YYYY-MM-DD')
}

// "2026-10-07" -> "۱۵ مهر" برای نمایش به کاربر
export function formatFa(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('fa-IR', {
    day: 'numeric',
    month: 'long',
  })
}
