import { useTranslation } from 'react-i18next'
import {
  FilterRegular,
  DismissRegular,
  PersonRegular,
  CheckmarkRegular,
} from '@fluentui/react-icons'
import { useFilters } from '../hooks/useFilters'
import type { TaskStatus, TaskPriority } from '../types/task'
import { TASK_STATUSES } from '../types/task'
import { STATUS_META, PRIORITY_COLORS } from '../constants/task'
import { Dropdown } from './ui/Dropdown'

// ── helpers ──────────────────────────────────────────────────────────────────

/** Priority display metadata with dot symbol for the filter dropdown. */
const PRIORITY_META: Record<
  TaskPriority,
  { label: string; color: string; dot: string }
> = {
  0: { label: 'None', color: PRIORITY_COLORS[0], dot: '○' },
  1: { label: 'Low', color: PRIORITY_COLORS[1], dot: '▲' },
  2: { label: 'Medium', color: PRIORITY_COLORS[2], dot: '▲' },
  3: { label: 'High', color: PRIORITY_COLORS[3], dot: '▲' },
  4: { label: 'Urgent', color: PRIORITY_COLORS[4], dot: '!!' },
}

// ── FilterChip ────────────────────────────────────────────────────────────────

function FilterChip({
  label,
  active,
  count,
  children,
}: {
  label: string
  active: boolean
  count?: number
  children: React.ReactNode
}) {
  return (
    <Dropdown
      trigger={
        <button
          type="button"
          className={[
            'inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md border text-xs font-medium transition-all duration-100',
            active
              ? 'border-accent/60 bg-accent/10 text-accent'
              : 'border-border bg-bg-tertiary text-text-secondary hover:border-border hover:text-text-primary hover:bg-bg-hover',
          ].join(' ')}
          aria-label={label}
        >
          {label}
          {count != null && count > 0 && (
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-accent text-white text-[10px] font-bold leading-none">
              {count}
            </span>
          )}
        </button>
      }
    >
      {children}
    </Dropdown>
  )
}

// ── FilterBar ─────────────────────────────────────────────────────────────────

/**
 * Shared filter bar used by Kanban and Table views.
 * All state is URL-synced via nuqs through the useFilters hook.
 */
export function FilterBar() {
  const { t } = useTranslation()
  const { filters, setFilters, resetFilters, hasActiveFilters } = useFilters()

  function toggleStatus(s: TaskStatus) {
    const next = filters.status.includes(s)
      ? (filters.status.filter((x) => x !== s) as TaskStatus[])
      : ([...filters.status, s] as TaskStatus[])
    setFilters({ status: next })
  }

  function togglePriority(p: TaskPriority) {
    const next = filters.priority.includes(p)
      ? (filters.priority.filter((x) => x !== p) as TaskPriority[])
      : ([...filters.priority, p] as TaskPriority[])
    setFilters({ priority: next })
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Status filter */}
      <FilterChip
        label={t('filter.status', 'Status')}
        active={filters.status.length > 0}
        count={filters.status.length}
      >
        <div className="py-1">
          {TASK_STATUSES.map((s) => {
            const meta = STATUS_META[s]
            const checked = filters.status.includes(s)
            return (
              <button
                key={s}
                type="button"
                onClick={() => toggleStatus(s)}
                className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors duration-75"
              >
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: meta.color }}
                />
                <span className="flex-1 text-left">{meta.label}</span>
                {checked && (
                  <CheckmarkRegular
                    className="text-accent"
                    style={{ fontSize: 12 }}
                  />
                )}
              </button>
            )
          })}
        </div>
      </FilterChip>

      {/* Priority filter */}
      <FilterChip
        label={t('filter.priority', 'Priority')}
        active={filters.priority.length > 0}
        count={filters.priority.length}
      >
        <div className="py-1">
          {([0, 1, 2, 3, 4] as TaskPriority[]).map((p) => {
            const meta = PRIORITY_META[p]
            const checked = filters.priority.includes(p)
            return (
              <button
                key={p}
                type="button"
                onClick={() => togglePriority(p)}
                className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors duration-75"
              >
                <span
                  className="text-[10px] font-mono w-3 flex-shrink-0"
                  style={{ color: meta.color }}
                >
                  {meta.dot}
                </span>
                <span className="flex-1 text-left">{meta.label}</span>
                {checked && (
                  <CheckmarkRegular
                    className="text-accent"
                    style={{ fontSize: 12 }}
                  />
                )}
              </button>
            )
          })}
        </div>
      </FilterChip>

      {/* Assignee filter */}
      <FilterChip
        label={t('filter.assignee', 'Assignee')}
        active={filters.assignee !== '' || filters.unassigned}
        count={
          (filters.assignee !== '' ? 1 : 0) + (filters.unassigned ? 1 : 0)
        }
      >
        <div className="py-1 min-w-[180px]">
          <button
            type="button"
            onClick={() =>
              setFilters({
                assignee: filters.assignee === 'me' ? '' : 'me',
                unassigned: false,
              })
            }
            className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors duration-75"
          >
            <PersonRegular style={{ fontSize: 13 }} />
            <span className="flex-1 text-left">
              {t('filter.assignedToMe', 'Assigned to me')}
            </span>
            {filters.assignee === 'me' && (
              <CheckmarkRegular
                className="text-accent"
                style={{ fontSize: 12 }}
              />
            )}
          </button>
          <button
            type="button"
            onClick={() =>
              setFilters({
                unassigned: !filters.unassigned,
                assignee: '',
              })
            }
            className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors duration-75"
          >
            <span className="w-[13px] text-center text-[10px] font-mono flex-shrink-0">
              —
            </span>
            <span className="flex-1 text-left">
              {t('filter.unassigned', 'Unassigned')}
            </span>
            {filters.unassigned && (
              <CheckmarkRegular
                className="text-accent"
                style={{ fontSize: 12 }}
              />
            )}
          </button>
        </div>
      </FilterChip>

      {/* Active filter indicator */}
      {hasActiveFilters && (
        <div className="flex items-center gap-1.5">
          <span className="text-text-tertiary text-xs font-mono">|</span>
          <button
            type="button"
            onClick={resetFilters}
            className="inline-flex items-center gap-1 h-7 px-2 rounded-md text-xs text-text-tertiary hover:text-danger transition-colors duration-100"
            aria-label="Clear all filters"
          >
            <FilterRegular style={{ fontSize: 12 }} />
            {t('filter.clear', 'Clear')}
            <DismissRegular style={{ fontSize: 10 }} />
          </button>
        </div>
      )}
    </div>
  )
}
