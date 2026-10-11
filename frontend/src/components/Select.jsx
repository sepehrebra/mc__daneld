import { forwardRef } from 'react'
import { ChevronDown } from 'lucide-react'

// لیست کشویی با برچسب و پیام خطا. گزینه‌ها را به‌صورت children بده.
const Select = forwardRef(function Select({ label, error, placeholder, children, ...props }, ref) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium">{label}</label>
      <div className="relative">
        <select
          ref={ref}
          className={`h-12 w-full appearance-none rounded-xl border bg-surface ps-3 pe-10 text-base outline-none transition
            focus:border-primary focus:ring-2 focus:ring-wheat/60 disabled:bg-bg disabled:text-muted
            ${error ? 'border-danger' : 'border-line'}`}
          {...props}
        >
          <option value="">{placeholder}</option>
          {children}
        </select>
        <ChevronDown
          size={18}
          className="pointer-events-none absolute inset-y-0 end-3 my-auto text-muted"
        />
      </div>
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  )
})

export default Select
