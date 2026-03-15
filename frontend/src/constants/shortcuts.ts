/**
 * Global keyboard shortcut definitions following the Linear-style convention.
 *
 * Each entry describes the key(s) that trigger an action and, for
 * modifier-based shortcuts, whether Cmd (Mac) / Ctrl (other) is required.
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
 */

export interface ShortcutDef {
  /** The KeyboardEvent.key value to match */
  key: string
  /** Requires Cmd (Mac) or Ctrl (other) modifier */
  modifier?: boolean
  /** Fires even when an input element is focused */
  ignoresInput?: boolean
  /** Navigate to this route (relative) instead of calling a handler */
  navigateTo?: string
  /** Handler option name from KeyboardShortcutOptions */
  handler?: string
  /** Call preventDefault on the event */
  preventDefault?: boolean
}

export const KEYBOARD_SHORTCUTS: ShortcutDef[] = [
  // Modifier shortcuts — fire even inside inputs
  {
    key: 'k',
    modifier: true,
    ignoresInput: true,
    handler: 'onCommandPalette',
    preventDefault: true,
  },
  {
    key: 'Escape',
    ignoresInput: true,
    handler: 'onClose',
    preventDefault: false,
  },

  // Single-key shortcuts — suppressed inside inputs
  { key: 'c', handler: 'onCreateTask', preventDefault: true },
  { key: 'k', handler: 'onNavigateUp', preventDefault: true },
  { key: 'j', handler: 'onNavigateDown', preventDefault: true },
  { key: '/', handler: 'onSearch', preventDefault: true },

  // Navigation shortcuts
  { key: '1', navigateTo: 'kanban', preventDefault: true },
  { key: '2', navigateTo: 'table', preventDefault: true },
  { key: '3', navigateTo: 'gantt', preventDefault: true },
  { key: '4', navigateTo: 'dashboard', preventDefault: true },
]
