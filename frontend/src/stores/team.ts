import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Team } from '../api/teams'

/**
 * UI-only state for team selection and pinned projects.
 * Server data (teams list, projects list) is managed by TanStack Query — not stored here.
 */
interface TeamStore {
  /** Currently selected team (persisted for session continuity) */
  selectedTeam: Team | null
  /** IDs of pinned (favorite) projects (persisted user preference) */
  pinnedProjectIds: string[]

  setSelectedTeam: (team: Team) => void
  togglePinnedProject: (projectId: string) => void
}

export const useTeamStore = create<TeamStore>()(
  persist(
    (set, get) => ({
      selectedTeam: null,
      pinnedProjectIds: [],

      setSelectedTeam: (team) => set({ selectedTeam: team }),

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
