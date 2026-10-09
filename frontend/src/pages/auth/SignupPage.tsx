import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { signup } from '../../api/auth'
import { AuthLayout } from './AuthLayout'

const UOW_DOMAINS = ['@uow.edu.au', '@uowmail.edu.au']

export function SignupPage() {
  const navigate = useNavigate()
  const [role, setRole] = useState<'student' | 'staff'>('student')
  const [fullName, setFullName] = useState('')
  const [studentNumber, setStudentNumber] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [touched, setTouched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const emailError =
    email && !UOW_DOMAINS.some((d) => email.trim().toLowerCase().endsWith(d))
      ? 'Use your @uowmail.edu.au or @uow.edu.au address'
      : null
  const passwordError =
    password && (password.length < 10 || !/\d/.test(password))
      ? 'At least 10 characters, including a number.'
      : null
  const confirmError = confirm && confirm !== password ? "Passwords don't match." : null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (emailError || passwordError || confirmError || !agreed) return
    setSubmitting(true)
    setError(null)
    try {
      const user = await signup({
        email,
        full_name: fullName,
        student_number: role === 'student' ? studentNumber || null : null,
        role,
        password,
      })
      const notice =
        user.status === 'pending'
          ? 'Account created. SCIT Operations will approve your staff access — you can sign in once approved.'
          : 'Account created. Sign in to continue.'
      navigate('/login', { replace: true, state: { notice } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign up failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      pitch={
        <>
          <h2>Create your account.</h2>
          <p>
            Access is role-based. Student accounts are active immediately; staff accounts are
            approved by SCIT Operations before timetable data is visible.
          </p>
        </>
      }
    >
      <h1>Sign up</h1>
      <div className="subtitle">Use your UOW email address.</div>
      {error && <div className="alert error">{error}</div>}
      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <span className="field-label">I am a</span>
          <div className="role-switch" role="radiogroup">
            <button
              type="button"
              role="radio"
              aria-checked={role === 'student'}
              className={`role-option${role === 'student' ? ' active' : ''}`}
              onClick={() => setRole('student')}
            >
              <strong>Student</strong>Choose classes &amp; give feedback
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={role === 'staff'}
              className={`role-option${role === 'staff' ? ' active' : ''}`}
              onClick={() => setRole('staff')}
            >
              <strong>SCIT Staff</strong>Requires Operations approval
            </button>
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <label htmlFor="su-name">Full name</label>
            <input
              id="su-name"
              className="input"
              required
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          {role === 'student' && (
            <div className="field">
              <label htmlFor="su-number">Student number</label>
              <input
                id="su-number"
                className="input"
                inputMode="numeric"
                value={studentNumber}
                onChange={(e) => setStudentNumber(e.target.value)}
              />
            </div>
          )}
        </div>
        <div className="field">
          <label htmlFor="su-email">UOW email</label>
          <input
            id="su-email"
            className={`input${emailError ? ' invalid' : ''}`}
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {emailError && <div className="field-error">{emailError}</div>}
        </div>
        <div className="field-row">
          <div className="field">
            <label htmlFor="su-password">Password</label>
            <input
              id="su-password"
              className={`input${touched && passwordError ? ' invalid' : ''}`}
              type="password"
              required
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="su-confirm">Confirm password</label>
            <input
              id="su-confirm"
              className={`input${confirmError ? ' invalid' : ''}`}
              type="password"
              required
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>
        </div>
        <div className={touched && passwordError ? 'field-error' : 'field-hint'} style={{ margin: '-6px 0 14px' }}>
          {confirmError ?? 'At least 10 characters, including a number.'}
        </div>
        <label className="checkbox" style={{ marginBottom: 12 }}>
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
          I agree to the UOW acceptable use policy
        </label>
        {touched && !agreed && <div className="field-error">Please accept the policy to continue.</div>}
        <button type="submit" className="btn block" disabled={submitting} style={{ marginTop: 10 }}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <div className="auth-foot">
        Already have an account? <Link to="/login">Sign in</Link>
      </div>
    </AuthLayout>
  )
}
