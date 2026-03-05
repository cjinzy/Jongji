import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Team, Project } from '../api/teams'

interface TeamStore {
  /** All teams the user belongs to */
  teams: Team[]
  /** Currently selected team */
  selectedTeam: Team | null
  /** Projects of the selected team */
  projects: Project[]
  /** IDs of pinned (favorite) projects */
  pinnedProjectIds: string[]

  setTeams: (teams: Team[]) => void
  setSelectedTeam: (team: Team) => void
  setProjects: (projects: Project[]) => void
  togglePinnedProject: (projectId: string) => void
}

export const useTeamStore = create<TeamStore>()(
  persist(
    (set, get) => ({
      teams: [],
      selectedTeam: null,
      projects: [],
      pinnedProjectIds: [],

      setTeams: (teams) => set({ teams }),

      setSelectedTeam: (team) => set({ selectedTeam: team, projects: [] }),

      setProjects: (projects) => set({ projects }),

      togglePinnedProject: (projectId) => {
        const { pinnedProjectIds } = get()
        const next = pinnedProjectIds.includes(projectId)
          ? pinnedProjectIds.filter((id) => id !== projectId)
          : [...pinnedProjectIds, projectId]
        set({ pinnedProjectIds: next })
      },
    }),
    {
      name: 'jongji-team-store',
      partialize: (state) => ({
        selectedTeam: state.selectedTeam,
        pinnedProjectIds: state.pinnedProjectIds,
      }),
    }
  )
)
