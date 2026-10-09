import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/useAuth'
import { homePath } from '../../auth/homePath'
import { AuthLayout } from './AuthLayout'

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const notice = (location.state as { notice?: string } | null)?.notice
  const from = (location.state as { from?: string } | null)?.from

  if (user) return <Navigate to={homePath(user)} replace />

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const signedIn = await login(email, password, rememberMe)
      navigate(from ?? homePath(signedIn), { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      pitch={
        <>
          <h2>Lab utilisation and scheduling, in one place.</h2>
          <p>
            Validate Enterprise exports, spot bottlenecked rooms and model timetable changes
            before they happen.
          </p>
          <div className="feature">
            <strong>Operations staff</strong> — upload timetables, manage bookings, run scenarios
          </div>
          <div className="feature">
            <strong>Students</strong> — choose lab classes, check room availability, share feedback
          </div>
        </>
      }
    >
      <h1>Sign in</h1>
      <div className="subtitle">Staff and students use their UOW account.</div>
      {notice && <div className="alert ok">{notice}</div>}
      {error && <div className="alert error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="login-email">UOW email</label>
          <input
            id="login-email"
            className="input"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            className="input"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="auth-row">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            Remember me
          </label>
        </div>
        <button type="submit" className="btn block" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <div className="auth-foot">
        New to the tool? <Link to="/signup">Create an account</Link>
      </div>
    </AuthLayout>
  )
}
