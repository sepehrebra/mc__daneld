import { Controller } from 'react-hook-form'
import DatePickerModule from 'react-multi-date-picker'
import persian from 'react-date-object/calendars/persian'
import persian_fa from 'react-date-object/locales/persian_fa'
import { X } from 'lucide-react'

// این کتابخانه CommonJS است و گاهی با default تو در تو import می‌شود
const DatePicker = DatePickerModule.default ?? DatePickerModule

// فیلد تاریخ شمسی. با range={true} بازه‌ی تاریخ می‌گیرد.
// با clearable={true} کاربر می‌تواند مقدار را پاک کند (برای فیلدهای اختیاری).
export default function DateField({
  control, name, label, rules, error, placeholder = 'انتخاب تاریخ',
  range = false, clearable = false,
}) {
  return (
    <div>
      <label htmlFor={name} className="mb-1.5 block text-sm font-medium">{label}</label>
      <Controller
        control={control}
        name={name}
        rules={rules}
        render={({ field }) => {
          const hasValue = range ? field.value?.length > 0 : Boolean(field.value)
          return (
            <div className="relative">
              <DatePicker
                id={name}
                value={field.value}
                onChange={(v) => field.onChange(v)}
                calendar={persian}
                locale={persian_fa}
                range={range}
                editable={false}
                placeholder={placeholder}
                className="green rmdp-mobile"
                containerClassName="w-full"
                inputClass={`h-12 w-full rounded-xl border bg-surface px-3 text-base outline-none transition
                  focus:border-primary focus:ring-2 focus:ring-wheat/60
                  ${error ? 'border-danger' : 'border-line'}`}
              />
              {clearable && hasValue && (
                <button
                  type="button"
                  onClick={() => field.onChange(range ? [] : null)}
                  className="absolute inset-y-0 end-0 flex w-11 items-center justify-center text-muted"
                  aria-label="پاک کردن تاریخ"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          )
        }}
      />
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  )
}
