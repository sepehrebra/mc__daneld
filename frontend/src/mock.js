// داده‌های آزمایشی؛ فقط وقتی USE_MOCK = true است استفاده می‌شوند.
const day = (n) => {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

export const mockTasks = [
  { id: 1, title: 'آبیاری قطعه‌ی شمالی', date: day(1) },
  { id: 2, title: 'کوددهی گندم', date: day(3) },
  { id: 3, title: 'سم‌پاشی باغ سیب', date: day(6) },
]

export const mockFarms = [
  { id: 1, name: 'مزرعه‌ی گندم', plots: [{ id: 11, name: 'قطعه‌ی شمالی' }, { id: 12, name: 'قطعه‌ی جنوبی' }] },
  { id: 2, name: 'باغ سیب', plots: [{ id: 21, name: 'ردیف ۱ تا ۱۰' }] },
  { id: 3, name: 'زمین کنار رودخانه', plots: [] },
]
