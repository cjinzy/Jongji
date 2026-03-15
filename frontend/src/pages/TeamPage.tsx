import { useParams, Link, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  TableRegular,
  BoardRegular,
  ChartMultipleRegular,
  GridRegular,
  AddRegular,
  PinRegular,
  PinOffRegular,
} from '@fluentui/react-icons'
import { teamsApi } from '../api/teams'
import { useTeamStore } from '../stores/team'

/**
 * Team detail page — shows the list of projects belonging to a team.
 * Each project card links to its default Kanban view.
 */
export default function TeamPage() {
  const { t } = useTranslation()
  const { teamId = '' } = useParams<{ teamId: string }>()
  const navigate = useNavigate()
  const { pinnedProjectIds, togglePinnedProject } = useTeamStore()

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: teamsApi.list,
  })

  const team = teams?.find((t) => t.id === teamId)

  // Server state managed by TanStack Query (single source of truth)
  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects', teamId],
    queryFn: () => teamsApi.listProjects(teamId),
    enabled: !!teamId,
  })

  const pinned = projects?.filter((p) => pinnedProjectIds.includes(p.id)) ?? []
  const rest = projects?.filter((p) => !pinnedProjectIds.includes(p.id)) ?? []

  return (
    <div className="px-6 py-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-7 h-7 rounded-md bg-accent/20 border border-accent/30 flex items-center justify-center">
            <span className="text-accent text-xs font-bold font-mono">
              {team?.key ?? '—'}
            </span>
          </div>
          <h1 className="text-xl font-semibold text-text-primary tracking-tight">
            {team?.name ?? t('common.loading')}
          </h1>
        </div>
        {team?.description && (
          <p className="text-sm text-text-secondary ml-10">
            {team.description}
          </p>
        )}
      </div>

      {isLoading && (
        <p className="text-sm text-text-tertiary font-mono">
          {t('common.loading')}
        </p>
      )}

      {/* Pinned projects */}
      {pinned.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xs font-mono text-text-tertiary uppercase tracking-widest mb-3 flex items-center gap-2">
            <PinRegular style={{ fontSize: 11 }} />
            {t('team.pinned', 'Pinned')}
          </h2>
          <ProjectGrid
            projects={pinned}
            teamId={teamId}
            pinnedIds={pinnedProjectIds}
            onTogglePin={togglePinnedProject}
          />
        </section>
      )}

      {/* All projects */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-mono text-text-tertiary uppercase tracking-widest flex items-center gap-2">
            <GridRegular style={{ fontSize: 11 }} />
            {t('team.projects', 'Projects')}
          </h2>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md border border-border bg-bg-tertiary text-text-secondary text-xs font-medium hover:bg-bg-hover hover:text-text-primary transition-all duration-100"
            onClick={() => navigate(`/teams/${teamId}/new-project`)}
            aria-label={t('team.newProject', 'New project')}
          >
            <AddRegular style={{ fontSize: 13 }} />
            {t('team.newProject', 'New project')}
          </button>
        </div>
        {rest.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-32 border border-dashed border-border rounded-xl gap-2">
            <p className="text-sm text-text-tertiary font-mono">
              {t('team.noProjects', 'No projects yet')}
            </p>
          </div>
        )}
        {rest.length > 0 && (
          <ProjectGrid
            projects={rest}
            teamId={teamId}
            pinnedIds={pinnedProjectIds}
            onTogglePin={togglePinnedProject}
          />
        )}
      </section>
    </div>
  )
}

// ── ProjectGrid ───────────────────────────────────────────────────────────────

interface ProjectCardProps {
  id: string
  name: string
  key: string
  description?: string
}

function ProjectGrid({
  projects,
  teamId,
  pinnedIds,
  onTogglePin,
}: {
  projects: ProjectCardProps[]
  teamId: string
  pinnedIds: string[]
  onTogglePin: (id: string) => void
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {projects.map((project) => {
        const isPinned = pinnedIds.includes(project.id)
        return (
          <div
            key={project.id}
            className="group relative bg-bg-secondary border border-border rounded-xl p-4 hover:border-accent/40 hover:bg-bg-tertiary transition-all duration-150"
          >
            {/* Pin button */}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault()
                onTogglePin(project.id)
              }}
              className={[
                'absolute top-3 right-3 p-1 rounded transition-all duration-100',
                isPinned
                  ? 'text-accent opacity-100'
                  : 'text-text-tertiary opacity-0 group-hover:opacity-100 hover:text-text-secondary',
              ].join(' ')}
              aria-label={isPinned ? 'Unpin project' : 'Pin project'}
            >
              {isPinned ? (
                <PinRegular style={{ fontSize: 13 }} />
              ) : (
                <PinOffRegular style={{ fontSize: 13 }} />
              )}
            </button>

            {/* Project identity */}
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 rounded bg-bg-tertiary border border-border flex items-center justify-center flex-shrink-0">
                <span className="text-[9px] font-bold font-mono text-text-secondary">
                  {project.key.slice(0, 3)}
                </span>
              </div>
              <span className="text-sm font-medium text-text-primary truncate">
                {project.name}
              </span>
            </div>

            {project.description && (
              <p className="text-xs text-text-secondary mb-3 line-clamp-2">
                {project.description}
              </p>
            )}

            {/* View links */}
            <div className="flex items-center gap-1 mt-3">
              <Link
                to={`/teams/${teamId}/projects/${project.key}/kanban`}
                className="inline-flex items-center gap-1 h-6 px-2 rounded text-xs text-text-tertiary hover:text-text-primary hover:bg-bg-hover transition-colors duration-75"
                title="Kanban"
              >
                <BoardRegular style={{ fontSize: 12 }} />
                Kanban
              </Link>
              <Link
                to={`/teams/${teamId}/projects/${project.key}/table`}
                className="inline-flex items-center gap-1 h-6 px-2 rounded text-xs text-text-tertiary hover:text-text-primary hover:bg-bg-hover transition-colors duration-75"
                title="Table"
              >
                <TableRegular style={{ fontSize: 12 }} />
                Table
              </Link>
              <Link
                to={`/teams/${teamId}/projects/${project.key}/gantt`}
                className="inline-flex items-center gap-1 h-6 px-2 rounded text-xs text-text-tertiary hover:text-text-primary hover:bg-bg-hover transition-colors duration-75"
                title="Gantt"
              >
                <ChartMultipleRegular style={{ fontSize: 12 }} />
                Gantt
              </Link>
            </div>
          </div>
        )
      })}
    </div>
  )
}
