"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth-context"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

interface AuthGuardProps {
  children: React.ReactNode
  requireSuper?: boolean
}

export function AuthGuard({ children, requireSuper = false }: AuthGuardProps) {
  const { token, isSuper } = useAuth()
  const router = useRouter()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    if (!token) {
      router.push("/login")
    } else if (requireSuper && !isSuper) {
      router.push("/dashboard")
    }
    setIsChecking(false)
  }, [token, isSuper, requireSuper, router])

  if (isChecking) {
    return <LoadingSpinner />
  }

  if (!token || (requireSuper && !isSuper)) {
    return null
  }

  return <>{children}</>
}
