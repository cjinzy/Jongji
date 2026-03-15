/**
 * Labelled text input used in the onboarding flow.
 * Supports an optional hint text and an "optional" badge.
 */
export function InputField({
  label,
  hint,
  optional,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string
  hint?: string
  optional?: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-text-secondary uppercase tracking-wider">
          {label}
        </label>
        {optional && (
          <span className="text-[10px] text-text-tertiary bg-bg-hover px-1.5 py-0.5 rounded">
            optional
          </span>
        )}
      </div>
      <input
        {...props}
        className="w-full px-3 py-2.5 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all duration-150"
      />
      {hint && <p className="text-xs text-text-tertiary">{hint}</p>}
    </div>
  )
}
