import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router'

/**
 * Returns true when the event target is an interactive input element
 * where global shortcuts should not fire.
 */
function isInputFocused(e: KeyboardEvent): boolean {
  const target = e.target as HTMLElement | null
  if (!target) return false
  const tag = target.tagName.toLowerCase()
  return (
    tag === 'input' ||
    tag === 'textarea' ||
    tag === 'select' ||
    target.isContentEditable
  )
}

export interface KeyboardShortcutOptions {
  /** Open the "create task" modal/panel */
  onCreateTask?: () => void
  /** Focus the search / command palette */
  onSearch?: () => void
  /** Toggle the command palette (Cmd/Ctrl+K) */
  onCommandPalette?: () => void
  /** Move selection up in a task list */
  onNavigateUp?: () => void
  /** Move selection down in a task list */
  onNavigateDown?: () => void
  /** Close the currently open panel or modal */
  onClose?: () => void
}

/**
 * Registers global keyboard shortcuts following the Linear-style convention.
 *
 * Shortcuts:
 *   c          → create task
 *   k          → navigate up
 *   j          → navigate down
 *   /          → focus search
 *   Cmd/Ctrl+K → command palette
 *   1          → Kanban view
 *   2          → Table view
 *   3          → Gantt view
 *   4          → Dashboard view
 *   Escape     → close panel / modal
 *
 * All single-key shortcuts are suppressed when an input field has focus.
 */
export function useKeyboardShortcuts(options: KeyboardShortcutOptions = {}) {
  const navigate = useNavigate()

  const {
    onCreateTask,
    onSearch,
    onCommandPalette,
    onNavigateUp,
    onNavigateDown,
    onClose,
  } = options

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().includes('MAC')
      const modifier = isMac ? e.metaKey : e.ctrlKey

      // Cmd/Ctrl+K — command palette (fires even inside inputs)
      if (modifier && e.key === 'k') {
        e.preventDefault()
        onCommandPalette?.()
        return
      }

      // Escape — close panel/modal (fires even inside inputs)
      if (e.key === 'Escape') {
        onClose?.()
        return
      }

      // All remaining shortcuts are suppressed inside inputs
      if (isInputFocused(e)) return

      switch (e.key) {
        case 'c':
          e.preventDefault()
          onCreateTask?.()
          break

        case 'k':
          e.preventDefault()
          onNavigateUp?.()
          break

        case 'j':
          e.preventDefault()
          onNavigateDown?.()
          break

        case '/':
          e.preventDefault()
          onSearch?.()
          break

        case '1':
          e.preventDefault()
          navigate('kanban')
          break

        case '2':
          e.preventDefault()
          navigate('table')
          break

        case '3':
          e.preventDefault()
          navigate('gantt')
          break

        case '4':
          e.preventDefault()
          navigate('dashboard')
          break

        default:
          break
      }
    },
    [
      onCommandPalette,
      onClose,
      onCreateTask,
      onNavigateUp,
      onNavigateDown,
      onSearch,
      navigate,
    ],
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
