import type { ReactNode } from 'react'

export function AuthLayout({ pitch, children }: { pitch: ReactNode; children: ReactNode }) {
  return (
    <div className="auth-screen">
      <aside className="auth-brand">
        <div className="brand">
          <div className="brand-title">SCIT Lab Scheduling</div>
          <div className="brand-sub">School of Computing &amp; IT, UOW</div>
        </div>
        <div className="pitch">{pitch}</div>
      </aside>
      <main className="auth-main">
        <div className="auth-card">{children}</div>
      </main>
    </div>
  )
}
