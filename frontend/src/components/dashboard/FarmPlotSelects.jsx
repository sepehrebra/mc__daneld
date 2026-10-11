import Select from '../Select.jsx'

// دو لیست وابسته: مزرعه و قطعه‌ی زراعی همان مزرعه.
// form = خروجی useForm، farms = { data, loading }
// required=false یعنی برای فیلتر است و گزینه‌ی «همه» دارد.
export default function FarmPlotSelects({ form, farms, required }) {
  const { register, watch, setValue, formState: { errors } } = form
  const farmId = watch('farm')
  const list = farms.data ?? []
  const plots = list.find((f) => String(f.id) === farmId)?.plots ?? []

  let plotPlaceholder = required ? 'انتخاب قطعه' : 'همه‌ی قطعه‌ها'
  if (!farmId) plotPlaceholder = 'اول مزرعه را انتخاب کن'
  else if (plots.length === 0) plotPlaceholder = 'این مزرعه قطعه‌ای ندارد'

  return (
    <>
      <Select
        label="مزرعه"
        placeholder={required ? 'انتخاب مزرعه' : 'همه‌ی مزرعه‌ها'}
        disabled={farms.loading}
        error={errors.farm?.message}
        {...register('farm', {
          required: required && 'مزرعه را انتخاب کن',
          onChange: () => setValue('plot', ''),
        })}
      >
        {list.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
      </Select>

      <Select
        label="قطعه‌ی زراعی"
        placeholder={plotPlaceholder}
        disabled={!farmId || plots.length === 0}
        error={errors.plot?.message}
        {...register('plot', { required: required && 'قطعه را انتخاب کن' })}
      >
        {plots.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </Select>
    </>
  )
}
