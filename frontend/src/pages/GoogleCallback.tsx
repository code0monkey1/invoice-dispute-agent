import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { handleGoogleCallback, OAUTH_STATE_KEY } from '../contexts/auth'

// A callback this page refuses before contacting the server.
class SignInRejected extends Error {}

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
    const returnedState = searchParams.get('state')
    // The state is single-use: forget it whether or not this callback is valid.
    const expectedState = sessionStorage.getItem(OAUTH_STATE_KEY)
    sessionStorage.removeItem(OAUTH_STATE_KEY)

    const finishSignIn = async () => {
      if (!code) throw new SignInRejected('No authorization code received')
      // Only finish a sign-in this browser started (login CSRF protection).
      if (!expectedState || returnedState !== expectedState) {
        throw new SignInRejected("This sign-in link expired or didn't come from this browser. Please sign in again.")
      }
      return api.googleCallback(code)
    }

    finishSignIn()
      .then(({ token, user }) => {
        handleGoogleCallback(token, user)
        navigate('/dashboard', { replace: true })
        window.location.reload()
      })
      .catch((err) => {
        // If the exchange failed but we're already signed in (e.g. the code
        // was used), just redirect. A rejected callback always shows its error.
        if (!(err instanceof SignInRejected) && localStorage.getItem('invoicechaser_token')) {
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
