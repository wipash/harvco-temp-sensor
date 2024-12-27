"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth-context"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

interface AuthGuardProps {
  children: React.ReactNode
  requireSuper?: boolean
}

export function AuthGuard({ children, requireSuper = false }: AuthGuardProps) {
  const { token, isSuper, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !token) {
      router.push("/login")
    } else if (!isLoading && requireSuper && !isSuper) {
      router.push("/dashboard")
    }
  }, [token, isSuper, requireSuper, router, isLoading])

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (!token || (requireSuper && !isSuper)) {
    return null
  }

  return <>{children}</>
}
