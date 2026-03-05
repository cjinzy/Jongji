import { useId } from 'react'

interface TimePickerProps {
  /** Time string in "HH:mm" format, e.g. "22:00" */
  value: string
  onChange: (value: string) => void
  label?: string
  disabled?: boolean
  id?: string
}

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))
const MINUTES = ['00', '15', '30', '45']

/**
 * Compact time picker with separate hour and minute selects.
 * Uses "HH:mm" string format. Minutes snapped to 15-min intervals.
 */
export default function TimePicker({
  value,
  onChange,
  label,
  disabled = false,
  id,
}: TimePickerProps) {
  const autoId = useId()
  const pickerId = id ?? autoId

  const [hh, mm] = value.split(':')
  const hour = hh ?? '00'
  const minute = MINUTES.includes(mm) ? mm : '00'

  function handleHour(h: string) {
    onChange(`${h}:${minute}`)
  }

  function handleMinute(m: string) {
    onChange(`${hour}:${m}`)
  }

  const selectClass = [
    'h-8 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm',
    'px-2 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30',
    'transition-all duration-150 cursor-pointer appearance-none',
    disabled ? 'opacity-40 cursor-not-allowed' : 'hover:border-text-tertiary',
  ].join(' ')

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={`${pickerId}-h`}
          className="block text-xs font-mono text-text-tertiary uppercase tracking-wider"
        >
          {label}
        </label>
      )}
      <div className="flex items-center gap-1">
        <select
          id={`${pickerId}-h`}
          value={hour}
          onChange={(e) => handleHour(e.target.value)}
          disabled={disabled}
          aria-label={label ? `${label} hour` : 'Hour'}
          className={`${selectClass} w-14`}
        >
          {HOURS.map((h) => (
            <option key={h} value={h}>
              {h}
            </option>
          ))}
        </select>
        <span className="text-text-tertiary text-sm font-mono select-none">:</span>
        <select
          id={`${pickerId}-m`}
          value={minute}
          onChange={(e) => handleMinute(e.target.value)}
          disabled={disabled}
          aria-label={label ? `${label} minute` : 'Minute'}
          className={`${selectClass} w-14`}
        >
          {MINUTES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
