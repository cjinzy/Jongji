import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router'
import { KEYBOARD_SHORTCUTS } from '../constants/shortcuts'

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
 * Registers global keyboard shortcuts defined in `constants/shortcuts.ts`.
 * This hook is responsible only for event listener registration/cleanup.
 *
 * Shortcut definitions live in {@link KEYBOARD_SHORTCUTS}.
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
      const inputFocused = isInputFocused(e)

      const handlers: Record<string, (() => void) | undefined> = {
        onCreateTask,
        onSearch,
        onCommandPalette,
        onNavigateUp,
        onNavigateDown,
        onClose,
      }

      for (const shortcut of KEYBOARD_SHORTCUTS) {
        if (e.key !== shortcut.key) continue
        if (shortcut.modifier && !modifier) continue
        if (!shortcut.modifier && !shortcut.ignoresInput && modifier) continue
        if (!shortcut.ignoresInput && inputFocused) continue

        if (shortcut.preventDefault) e.preventDefault()

        if (shortcut.navigateTo) {
          navigate(shortcut.navigateTo)
          return
        }

        if (shortcut.handler) {
          handlers[shortcut.handler]?.()
          return
        }
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
