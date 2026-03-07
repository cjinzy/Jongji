import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7'
import './i18n'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ProtectedRoute } from './components/ProtectedRoute'

// ── Lazy pages ────────────────────────────────────────────────────────────────

// Public
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const SetupPage = lazy(() => import('./pages/SetupPage'))
const AuthCallbackPage = lazy(() => import('./pages/AuthCallbackPage'))

// Protected (rendered inside Layout)
const Layout = lazy(() => import('./components/Layout'))
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'))
const TeamPage = lazy(() => import('./pages/TeamPage'))
const KanbanPage = lazy(() => import('./pages/KanbanPage'))
const TablePage = lazy(() => import('./pages/TablePage'))
const GanttPage = lazy(() => import('./pages/GanttPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const TaskDetailPage = lazy(() => import('./pages/TaskDetailPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))

// ── Root redirect — persists the last visited path ───────────────────────────

function RootRedirect() {
  const raw = localStorage.getItem('jongji-last-view') ?? '/login'
  const safePath = raw.startsWith('/') && !raw.startsWith('//') ? raw : '/login'
  return <Navigate to={safePath} replace />
}

// ── Full-screen loading fallback ──────────────────────────────────────────────

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-screen bg-bg-primary">
      <span className="text-xs text-text-tertiary font-mono animate-pulse">
        loading…
      </span>
    </div>
  )
}

// ── QueryClient ───────────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
})

// ── App ───────────────────────────────────────────────────────────────────────

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <NuqsAdapter>
          <ErrorBoundary>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* ── Public routes (no layout, no auth guard) ──── */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/setup" element={<SetupPage />} />
              <Route path="/auth/callback" element={<AuthCallbackPage />} />

              {/* ── Protected routes (auth guard + layout shell) ── */}
              <Route element={<ProtectedRoute />}>
                <Route element={<Layout />}>
                  {/* Onboarding wizard */}
                  <Route path="/onboarding" element={<OnboardingPage />} />

                  {/* Team overview */}
                  <Route path="/teams/:teamId" element={<TeamPage />} />

                  {/* Project views */}
                  <Route
                    path="/teams/:teamId/projects/:projKey/kanban"
                    element={<KanbanPage />}
                  />
                  <Route
                    path="/teams/:teamId/projects/:projKey/table"
                    element={<TablePage />}
                  />
                  <Route
                    path="/teams/:teamId/projects/:projKey/gantt"
                    element={<GanttPage />}
                  />
                  <Route
                    path="/teams/:teamId/projects/:projKey/dashboard"
                    element={<DashboardPage />}
                  />

                  {/* Task full-page detail */}
                  <Route
                    path="/teams/:teamId/projects/:projKey/tasks/:number"
                    element={<TaskDetailPage />}
                  />

                  {/* Global settings */}
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="/admin" element={<AdminPage />} />
                </Route>
              </Route>

              {/* ── Root: redirect to last-visited page ──────────── */}
              <Route path="/" element={<RootRedirect />} />

              {/* ── 404 catch-all ─────────────────────────────────── */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
          </ErrorBoundary>
        </NuqsAdapter>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
