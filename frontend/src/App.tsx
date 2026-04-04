import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import ChatPanel from './components/ChatPanel'
import LandingPage from './components/LandingPage'

function isAuthenticated() {
  const user = localStorage.getItem('invoicechaser_user')
  return !!user
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* Landing page — public */}
      <Route path="/" element={
        isAuthenticated() ? <Navigate to="/dashboard" replace /> : <LandingPage />
      } />

      {/* App routes — protected */}
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Layout>
            <Dashboard />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/invoice/:invoiceId" element={
        <ProtectedRoute>
          <Layout>
            <ChatPanel />
          </Layout>
        </ProtectedRoute>
      } />
    </Routes>
  )
}

export default App
