import { Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { Sidebar, type NavSection } from '../components/layout/Sidebar'

const ADMIN_NAV: NavSection[] = [
  {
    title: 'Workflow',
    items: [
      { label: 'Upload & Validate', to: '/admin/upload' },
      { label: 'Lab Utilisation', badge: 'Planned', planned: true },
      { label: 'Scenario Simulation', badge: 'Planned', planned: true },
      { label: 'Recommendations', badge: 'Planned', planned: true },
    ],
  },
  {
    title: 'Bookings',
    items: [
      { label: 'All Bookings', to: '/admin/bookings', activeUnder: '/admin/bookings/' },
      { label: 'New Booking', to: '/admin/bookings/new' },
    ],
  },
  {
    title: 'Insights',
    items: [
      { label: 'Room Availability', to: '/admin/availability' },
      { label: 'Student Feedback', to: '/admin/feedback' },
    ],
  },
  {
    title: 'Administration',
    items: [{ label: 'Users', to: '/admin/users' }],
  },
]

const STAFF_NAV: NavSection[] = [
  ADMIN_NAV[0]!,
  { title: 'Bookings', items: [{ label: 'All Bookings', to: '/admin/bookings', activeUnder: '/admin/bookings/' }] },
  ADMIN_NAV[2]!,
]

const STUDENT_NAV: NavSection[] = [
  {
    title: 'Student',
    items: [
      { label: 'My Timetable', to: '/student/timetable' },
      { label: 'Choose Classes', to: '/student/classes' },
      { label: 'Lab Availability', to: '/student/availability' },
      { label: 'Feedback', to: '/student/feedback' },
    ],
  },
]

export function AppShell() {
  const { user } = useAuth()
  const sections =
    user?.role === 'admin' ? ADMIN_NAV : user?.role === 'staff' ? STAFF_NAV : STUDENT_NAV

  return (
    <div className="shell">
      <Sidebar sections={sections} />
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
