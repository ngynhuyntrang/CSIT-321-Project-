import { useEffect, useState } from 'react'
import { getHealth, type HealthStatus } from './api/client'
import { IngestPage } from './pages/IngestPage'
import './index.css'

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((err) => setHealthError(err instanceof Error ? err.message : 'Unknown error'))
  }, [])

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>SCIT Computing Lab Scheduling</h1>
        <span className={`health-badge ${health ? 'ok' : healthError ? 'error' : 'pending'}`}>
          {health ? `Backend: ${health.status}, DB: ${health.db}` : healthError ? `Backend: ${healthError}` : 'Đang kiểm tra backend…'}
        </span>
      </header>
      <main>
        <IngestPage />
      </main>
    </div>
  )
}

export default App
