import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { handleGoogleCallback } from '../contexts/AuthContext'

export default function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  useEffect(() => {
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
        setError(err.message)
      })
  }, [searchParams, navigate])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-white">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-4">Sign-in failed: {error}</p>
          <a href="/" className="text-blue-400 underline">Back to home</a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-white">
      <p className="text-lg">Signing you in...</p>
    </div>
  )
}
