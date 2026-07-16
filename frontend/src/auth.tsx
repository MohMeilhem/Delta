/* Demo auth layer: client-side session only (hackathon build, no auth backend).
 * Any credentials are accepted; the session persists in localStorage. */

import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useIsPresent } from 'motion/react'

export interface User {
  email: string
}

const STORAGE_KEY = 'delta-user'

interface AuthCtx {
  user: User | null
  login: (email: string) => void
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    } catch {
      return null
    }
  })

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      login: (email) => {
        const u: User = { email }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(u))
        setUser(u)
      },
      logout: () => {
        localStorage.removeItem(STORAGE_KEY)
        setUser(null)
      },
    }),
    [user],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}

/** Layout route: renders children only when signed in, else redirects to /login. */
export function RequireAuth() {
  const { user } = useAuth()
  const location = useLocation()
  // AnimatePresence keeps the previous page mounted (with its stale location)
  // while it animates out; redirecting from that dying copy loops forever.
  const isPresent = useIsPresent()
  if (!user && isPresent) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <Outlet />
}
