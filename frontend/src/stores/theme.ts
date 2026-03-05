import { create } from 'zustand'

export type Theme = 'dark' | 'light' | 'system'

interface ThemeStore {
  theme: Theme
  setTheme: (theme: Theme) => void
  /** Resolved actual theme ('dark' | 'light') based on system preference when theme === 'system'. */
  resolvedTheme: () => 'dark' | 'light'
}

function getSystemTheme(): 'dark' | 'light' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme): void {
  const resolved = theme === 'system' ? getSystemTheme() : theme
  document.documentElement.setAttribute('data-theme', resolved)
}

const stored = (localStorage.getItem('jongji-theme') as Theme | null) ?? 'dark'

export const useThemeStore = create<ThemeStore>((set, get) => {
  // Apply on init
  applyTheme(stored)

  // Watch system preference changes
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  mq.addEventListener('change', () => {
    if (get().theme === 'system') {
      applyTheme('system')
    }
  })

  return {
    theme: stored,
    setTheme: (theme: Theme) => {
      localStorage.setItem('jongji-theme', theme)
      applyTheme(theme)
      set({ theme })
    },
    resolvedTheme: () => {
      const t = get().theme
      return t === 'system' ? getSystemTheme() : t
    },
  }
})
