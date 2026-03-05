import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'
import { PersonRegular } from '@fluentui/react-icons'
import type { User } from '../../api/users'

interface MentionListProps {
  items: User[]
  command: (attrs: { id: string; label: string }) => void
}

export interface MentionListHandle {
  onKeyDown: (event: KeyboardEvent) => boolean
}

/**
 * Dropdown list for @mention autocomplete in the rich editor.
 * Supports keyboard navigation (ArrowUp/ArrowDown/Enter).
 */
const MentionList = forwardRef<MentionListHandle, MentionListProps>(
  ({ items, command }, ref) => {
    const [selectedIndex, setSelectedIndex] = useState(0)
    const listRef = useRef<HTMLDivElement>(null)

    // Reset selection when items change
    useEffect(() => {
      setSelectedIndex(0)
    }, [items])

    // Scroll selected item into view
    useEffect(() => {
      const el = listRef.current?.querySelector<HTMLButtonElement>(
        `[data-index="${selectedIndex}"]`,
      )
      el?.scrollIntoView({ block: 'nearest' })
    }, [selectedIndex])

    function selectItem(index: number) {
      const item = items[index]
      if (item) {
        command({ id: item.id, label: item.name })
      }
    }

    useImperativeHandle(ref, () => ({
      onKeyDown: (event: KeyboardEvent) => {
        if (event.key === 'ArrowUp') {
          setSelectedIndex((i) => (i - 1 + items.length) % items.length)
          return true
        }
        if (event.key === 'ArrowDown') {
          setSelectedIndex((i) => (i + 1) % items.length)
          return true
        }
        if (event.key === 'Enter') {
          selectItem(selectedIndex)
          return true
        }
        return false
      },
    }))

    if (!items.length) {
      return (
        <div className="
          bg-bg-secondary border border-border rounded-lg shadow-lg
          px-3 py-2 text-xs text-text-tertiary
        ">
          No members found
        </div>
      )
    }

    return (
      <div
        ref={listRef}
        className="
          bg-bg-secondary border border-border rounded-lg shadow-lg
          py-1 min-w-[200px] max-h-[220px] overflow-y-auto
        "
        role="listbox"
        aria-label="Mention suggestions"
      >
        {items.map((item, index) => (
          <button
            key={item.id}
            data-index={index}
            role="option"
            aria-selected={index === selectedIndex}
            onClick={() => selectItem(index)}
            className={`
              w-full flex items-center gap-2.5 px-3 py-1.5 text-left
              transition-colors duration-75
              ${index === selectedIndex
                ? 'bg-bg-hover text-text-primary'
                : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              }
            `}
          >
            <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
              {item.avatar_url ? (
                <img
                  src={item.avatar_url}
                  alt={item.name}
                  className="w-6 h-6 rounded-full object-cover"
                />
              ) : (
                <PersonRegular className="w-3.5 h-3.5 text-accent" />
              )}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-medium truncate">{item.name}</span>
              <span className="text-[10px] text-text-tertiary truncate">{item.email}</span>
            </div>
          </button>
        ))}
      </div>
    )
  },
)

MentionList.displayName = 'MentionList'

export default MentionList
