import { useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  PersonRegular,
  StarRegular,
  StarFilled,
  SettingsRegular,
  FolderRegular,
  AddRegular,
  BoardRegular,
} from '@fluentui/react-icons'
import { teamsApi } from '../api/teams'
import { useTeamStore } from '../stores/team'
import { TeamSelector } from './TeamSelector'

function NavItem({
  to,
  icon: Icon,
  label,
  end,
}: {
  to: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  end?: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `relative flex items-center gap-2.5 px-3 py-1.5 text-sm rounded-md transition-colors duration-150 group ${
          isActive
            ? 'text-text-primary bg-bg-hover before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-4 before:w-0.5 before:rounded-full before:bg-accent'
            : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
        }`
      }
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span className="truncate">{label}</span>
    </NavLink>
  )
}

function SectionLabel({ label }: { label: string }) {
  return (
    <p className="px-3 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-widest text-text-tertiary select-none">
      {label}
    </p>
  )
}

export function Sidebar() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { selectedTeam, projects, setProjects, pinnedProjectIds, togglePinnedProject } =
    useTeamStore()

  const { data: projectData } = useQuery({
    queryKey: ['projects', selectedTeam?.id],
    queryFn: () => teamsApi.listProjects(selectedTeam!.id),
    enabled: !!selectedTeam,
  })

  useEffect(() => {
    if (projectData) setProjects(projectData)
  }, [projectData, setProjects])

  const pinnedProjects = projects.filter((p) => pinnedProjectIds.includes(p.id))

  return (
    <aside className="h-full flex flex-col bg-bg-secondary border-r border-border overflow-hidden">
      {/* Team selector */}
      <div className="px-2 pt-3 pb-1">
        <TeamSelector />
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
        <NavItem
          to="/my-issues"
          icon={PersonRegular}
          label={t('nav.myIssues')}
        />

        {/* Favorites */}
        {pinnedProjects.length > 0 && (
          <>
            <SectionLabel label={t('nav.favorites')} />
            {pinnedProjects.map((project) => (
              <div key={project.id} className="relative group/item">
                <NavLink
                  to={`/project/${project.id}`}
                  className={({ isActive }) =>
                    `relative flex items-center gap-2.5 px-3 py-1.5 text-sm rounded-md transition-colors duration-150 ${
                      isActive
                        ? 'text-text-primary bg-bg-hover before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-4 before:w-0.5 before:rounded-full before:bg-accent'
                        : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                    }`
                  }
                >
                  <FolderRegular className="w-4 h-4 shrink-0" />
                  <span className="truncate flex-1">{project.name}</span>
                  <span className="text-[10px] text-text-tertiary font-mono shrink-0">
                    {project.key}
                  </span>
                </NavLink>
                <button
                  onClick={() => togglePinnedProject(project.id)}
                  aria-label="Unpin project"
                  className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover/item:opacity-100 transition-opacity duration-150 text-text-tertiary hover:text-warning"
                >
                  <StarFilled className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </>
        )}

        {/* Projects */}
        <SectionLabel label={t('nav.projects')} />
        {projects.length === 0 ? (
          <p className="px-3 py-1.5 text-xs text-text-tertiary italic">
            {t('sidebar.noProjects')}
          </p>
        ) : (
          projects.map((project) => (
            <div key={project.id} className="relative group/item">
              <NavLink
                to={`/project/${project.id}`}
                className={({ isActive }) =>
                  `relative flex items-center gap-2.5 px-3 py-1.5 text-sm rounded-md transition-colors duration-150 ${
                    isActive
                      ? 'text-text-primary bg-bg-hover before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-4 before:w-0.5 before:rounded-full before:bg-accent'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                  }`
                }
              >
                <BoardRegular className="w-4 h-4 shrink-0" />
                <span className="truncate flex-1">{project.name}</span>
                <span className="text-[10px] text-text-tertiary font-mono shrink-0">
                  {project.key}
                </span>
              </NavLink>
              <button
                onClick={() => togglePinnedProject(project.id)}
                aria-label={
                  pinnedProjectIds.includes(project.id)
                    ? 'Unpin project'
                    : 'Pin project'
                }
                className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover/item:opacity-100 transition-opacity duration-150 text-text-tertiary hover:text-warning"
              >
                {pinnedProjectIds.includes(project.id) ? (
                  <StarFilled className="w-3.5 h-3.5 text-warning" />
                ) : (
                  <StarRegular className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          ))
        )}

        <button
          onClick={() => navigate('/onboarding')}
          className="w-full flex items-center gap-2.5 px-3 py-1.5 text-sm text-text-tertiary hover:text-text-secondary hover:bg-bg-hover rounded-md transition-colors duration-150 mt-0.5"
        >
          <AddRegular className="w-4 h-4 shrink-0" />
          <span>{t('sidebar.addProject')}</span>
        </button>
      </nav>

      {/* Bottom: Settings + User */}
      <div className="px-2 py-3 border-t border-border space-y-0.5">
        <NavItem to="/settings" icon={SettingsRegular} label={t('nav.settings')} />
        <button className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md hover:bg-bg-hover transition-colors duration-150 group">
          <span className="w-5 h-5 rounded-full bg-accent/30 text-accent text-xs font-bold flex items-center justify-center shrink-0 leading-none">
            U
          </span>
          <span className="text-sm text-text-secondary group-hover:text-text-primary truncate transition-colors duration-150">
            User
          </span>
        </button>
      </div>
    </aside>
  )
}
