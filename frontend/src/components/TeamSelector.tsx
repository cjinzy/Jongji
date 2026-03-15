import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronDownRegular,
  PeopleTeamRegular,
  AddRegular,
} from '@fluentui/react-icons'
import { teamsApi } from '../api/teams'
import { useTeamStore } from '../stores/team'

export function TeamSelector() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const { selectedTeam, setSelectedTeam } = useTeamStore()

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: teamsApi.list,
  })

  useEffect(() => {
    if (teams && !selectedTeam && teams.length > 0) {
      setSelectedTeam(teams[0])
    }
  }, [teams, selectedTeam, setSelectedTeam])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const initials = (name: string) =>
    name
      .split(' ')
      .map((w) => w[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-md hover:bg-bg-hover transition-colors duration-150 group"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {selectedTeam ? (
          <>
            <span className="w-6 h-6 rounded bg-accent/20 text-accent text-xs font-bold flex items-center justify-center shrink-0 leading-none">
              {initials(selectedTeam.name)}
            </span>
            <span className="flex-1 text-sm font-medium text-text-primary truncate text-left">
              {selectedTeam.name}
            </span>
          </>
        ) : (
          <>
            <PeopleTeamRegular className="w-5 h-5 text-text-tertiary shrink-0" />
            <span className="flex-1 text-sm text-text-secondary text-left">
              {t('nav.noTeam')}
            </span>
          </>
        )}
        <ChevronDownRegular
          className={`w-3.5 h-3.5 text-text-tertiary shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 top-full mt-1 z-50 bg-bg-tertiary border border-border rounded-lg shadow-2xl overflow-hidden"
          role="listbox"
        >
          {(teams ?? []).map((team) => (
            <button
              key={team.id}
              role="option"
              aria-selected={selectedTeam?.id === team.id}
              onClick={() => {
                setSelectedTeam(team)
                setOpen(false)
              }}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-bg-hover transition-colors duration-100 ${
                selectedTeam?.id === team.id
                  ? 'text-text-primary'
                  : 'text-text-secondary'
              }`}
            >
              <span className="w-5 h-5 rounded bg-accent/20 text-accent text-xs font-bold flex items-center justify-center shrink-0 leading-none">
                {initials(team.name)}
              </span>
              <span className="truncate">{team.name}</span>
              {selectedTeam?.id === team.id && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
              )}
            </button>
          ))}

          <div className="border-t border-border mt-0.5 pt-0.5">
            <button className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-text-tertiary hover:text-text-secondary hover:bg-bg-hover transition-colors duration-100">
              <AddRegular className="w-4 h-4 shrink-0" />
              <span>{t('sidebar.createTeam')}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
