import { useEffect, useState } from 'react'
import './App.css'
import LoginForm from './components/LoginForm'
import PaymentForm from './components/PaymentForm'
import { getAccountMe } from './api/account'

function App() {
  const [authed, setAuthed] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // try to fetch profile on load (cookie-based auth)
    (async () => {
      try {
        await getAccountMe()
        setAuthed(true)
      } catch {
        setAuthed(false)
      } finally {
        setChecking(false)
      }
    })()
  }, [])

  if (checking) return <div className="center">Loading...</div>

  return (
    <div className="container">
      {authed ? (
        <PaymentForm onLoggedOut={() => setAuthed(false)} />
      ) : (
        <LoginForm onLoggedIn={() => setAuthed(true)} />
      )}
    </div>
  )
}

export default App
