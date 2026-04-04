import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import ChatPanel from './components/ChatPanel'
import LandingPage from './components/LandingPage'
import GoogleCallback from './pages/GoogleCallback'
import { useAuth } from './contexts/AuthContext'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/" replace />
  return <>{children}</>
}

function App() {
  const { user, loading } = useAuth()

  if (loading) return null

  return (
    <Routes>
      <Route path="/" element={
        user ? <Navigate to="/dashboard" replace /> : <LandingPage />
      } />
      <Route path="/auth/google/callback" element={<GoogleCallback />} />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Layout><Dashboard /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/invoice/:invoiceId" element={
        <ProtectedRoute>
          <Layout><ChatPanel /></Layout>
        </ProtectedRoute>
      } />
    </Routes>
  )
}

export default App
