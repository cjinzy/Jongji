import { memo } from 'react'

interface ToolbarBtnProps {
  onClick: () => void
  active?: boolean
  disabled?: boolean
  title: string
  children: React.ReactNode
}

/**
 * Icon button used in the RichEditor toolbar.
 * Wrapped in React.memo to avoid re-renders when unrelated editor state changes.
 */
const ToolbarBtn = memo(function ToolbarBtn({
  onClick,
  active,
  disabled,
  title,
  children,
}: ToolbarBtnProps) {
  return (
    <button
      type="button"
      onMouseDown={(e) => {
        // Prevent editor from losing focus
        e.preventDefault()
        onClick()
      }}
      disabled={disabled}
      title={title}
      aria-label={title}
      aria-pressed={active}
      className={`
        w-7 h-7 rounded flex items-center justify-center
        transition-colors duration-100 focus-visible:outline-none
        focus-visible:ring-1 focus-visible:ring-accent
        ${active
          ? 'bg-accent/20 text-accent'
          : 'text-text-tertiary hover:text-text-primary hover:bg-bg-hover'
        }
        ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {children}
    </button>
  )
})

export { ToolbarBtn }
