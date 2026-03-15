import { memo, useEffect, useRef } from 'react'
import {
  TaskListSquareLtrRegular,
  ChatRegular,
  ArrowEnterLeftRegular,
} from '@fluentui/react-icons'
import type { SearchResultItem } from '../../api/search'
import { HighlightText } from './HighlightText'

interface ResultItemProps {
  item: SearchResultItem
  isActive: boolean
  onSelect: (item: SearchResultItem) => void
  onMouseEnter: () => void
}

/**
 * Single search result row in the CommandPalette list.
 * Wrapped in React.memo to avoid re-renders for inactive items when activeIndex changes.
 */
const ResultItem = memo(function ResultItem({
  item,
  isActive,
  onSelect,
  onMouseEnter,
}: ResultItemProps) {
  const ref = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (isActive) {
      ref.current?.scrollIntoView({ block: 'nearest' })
    }
  }, [isActive])

  return (
    <button
      ref={ref}
      type="button"
      role="option"
      aria-selected={isActive}
      onClick={() => onSelect(item)}
      onMouseEnter={onMouseEnter}
      className={`w-full flex items-start gap-3 px-4 py-2.5 text-left transition-colors duration-75 outline-none ${
        isActive ? 'bg-bg-hover' : 'hover:bg-bg-hover/50'
      }`}
    >
      <span className="mt-0.5 shrink-0 text-text-tertiary">
        {item.type === 'task' ? (
          <TaskListSquareLtrRegular className="w-4 h-4" />
        ) : (
          <ChatRegular className="w-4 h-4" />
        )}
      </span>

      <span className="flex-1 min-w-0">
        <span className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-text-tertiary shrink-0 tracking-wide">
            {item.project_key}-{item.task_number}
          </span>
          <span className="text-sm text-text-primary truncate font-medium">
            {item.task_title}
          </span>
        </span>

        {item.highlight && item.highlight !== item.task_title && (
          <span className="block mt-0.5 text-xs text-text-tertiary truncate leading-relaxed">
            <HighlightText html={item.highlight} />
          </span>
        )}
      </span>

      {isActive && (
        <span className="shrink-0 mt-0.5 text-text-tertiary opacity-60">
          <ArrowEnterLeftRegular className="w-3.5 h-3.5" />
        </span>
      )}
    </button>
  )
})

export { ResultItem }
