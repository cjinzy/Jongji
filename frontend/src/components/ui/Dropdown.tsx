import { useRef, useState, type KeyboardEvent } from 'react'

interface DropdownProps {
  /** Element that opens/closes the dropdown when clicked. */
  trigger: React.ReactNode
  children: React.ReactNode
}

/**
 * Generic dropdown wrapper with backdrop, open/close state, and keyboard support.
 * Renders the trigger as an accessible button-like div and shows children in a
 * floating panel anchored below.
 */
export function Dropdown({ trigger, children }: DropdownProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div className="relative" ref={ref} onKeyDown={handleKeyDown}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => e.key === 'Enter' && setOpen((v) => !v)}
        aria-expanded={open}
      >
        {trigger}
      </div>
      {open && (
        <>
          {/* Backdrop — closes dropdown on outside click */}
          <div
            className="fixed inset-0 z-20"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute top-full mt-1.5 left-0 z-30 min-w-[160px] bg-bg-secondary border border-border rounded-lg shadow-xl shadow-black/40 overflow-hidden">
            {children}
          </div>
        </>
      )}
    </div>
  )
}
