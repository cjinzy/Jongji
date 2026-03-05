import type { ReactNode } from 'react'

/**
 * Shared form field wrapper with label and children slot.
 */
export default function Field({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-mono text-text-tertiary uppercase tracking-wider">
        {label}
      </label>
      {children}
    </div>
  )
}
