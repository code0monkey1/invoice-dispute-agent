import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { handleGoogleCallback } from '../contexts/AuthContext'

export default function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const calledRef = useRef(false)

  useEffect(() => {
    // Prevent double-fire from React strict mode (auth codes are single-use)
    if (calledRef.current) return
    calledRef.current = true

    const code = searchParams.get('code')
    if (!code) {
      setError('No authorization code received')
      return
    }

    api.googleCallback(code)
      .then(({ token, user }) => {
        handleGoogleCallback(token, user)
        navigate('/dashboard', { replace: true })
        window.location.reload()
      })
      .catch((err) => {
        // If already signed in (e.g. code was used), just redirect
        const token = localStorage.getItem('invoicechaser_token')
        if (token) {
          navigate('/dashboard', { replace: true })
          return
        }
        setError(err.message)
      })
  }, [searchParams, navigate])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-mesh noise">
        <div className="text-center">
          <p className="text-red-500 text-lg mb-4">Sign-in failed: {error}</p>
          <a href="/" className="text-[#FF6B35] hover:underline">Back to home</a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-mesh noise">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-[#FF6B35] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-lg text-gray-600 font-medium">Signing you in...</p>
      </div>
    </div>
  )
}
