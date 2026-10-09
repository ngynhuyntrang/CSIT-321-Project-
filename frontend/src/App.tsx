import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { useAuth } from './auth/useAuth'
import { homePath } from './auth/homePath'
import { RequireRole } from './auth/RequireRole'
import { AppShell } from './layouts/AppShell'
import { BookingFormPage } from './pages/admin/BookingFormPage'
import { AdminFeedbackPage } from './pages/admin/FeedbackPage'
import { BookingsPage } from './pages/admin/BookingsPage'
import { IngestPage } from './pages/admin/IngestPage'
import { UsersPage } from './pages/admin/UsersPage'
import { LoginPage } from './pages/auth/LoginPage'
import { SignupPage } from './pages/auth/SignupPage'
import { AvailabilityPage } from './pages/student/AvailabilityPage'
import { ChooseClassesPage } from './pages/student/ChooseClassesPage'
import { FeedbackPage } from './pages/student/FeedbackPage'
import { TimetablePage } from './pages/student/TimetablePage'

function HomeRedirect() {
  const { user, loading } = useAuth()
  if (loading) return <div className="empty">Loading…</div>
  return <Navigate to={user ? homePath(user) : '/login'} replace />
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          <Route
            path="/admin"
            element={
              <RequireRole roles={['admin', 'staff']}>
                <AppShell />
              </RequireRole>
            }
          >
            <Route path="upload" element={<IngestPage />} />
            <Route path="bookings" element={<BookingsPage />} />
            <Route
              path="bookings/new"
              element={
                <RequireRole roles={['admin']}>
                  <BookingFormPage key="new" />
                </RequireRole>
              }
            />
            <Route path="bookings/:id" element={<BookingFormPage />} />
            <Route path="availability" element={<AvailabilityPage />} />
            <Route path="feedback" element={<AdminFeedbackPage />} />
            <Route
              path="users"
              element={
                <RequireRole roles={['admin']}>
                  <UsersPage />
                </RequireRole>
              }
            />
          </Route>

          <Route
            path="/student"
            element={
              <RequireRole roles={['student']}>
                <AppShell />
              </RequireRole>
            }
          >
            <Route path="timetable" element={<TimetablePage />} />
            <Route path="classes" element={<ChooseClassesPage />} />
            <Route path="availability" element={<AvailabilityPage />} />
            <Route path="feedback" element={<FeedbackPage />} />
          </Route>

          <Route path="*" element={<HomeRedirect />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
