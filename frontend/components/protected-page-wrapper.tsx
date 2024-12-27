"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth-context"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

interface ProtectedPageWrapperProps {
  children: React.ReactNode
  requireSuper?: boolean
}

export function ProtectedPageWrapper({ children, requireSuper = false }: ProtectedPageWrapperProps) {
  const { token, isSuper, isLoading } = useAuth()
  const router = useRouter()
  const [isAuthorized, setIsAuthorized] = useState(false)

  useEffect(() => {
    if (!isLoading) {
      if (!token) {
        router.replace("/login")
      } else if (requireSuper && !isSuper) {
        router.replace("/dashboard")
      } else {
        setIsAuthorized(true)
      }
    }
  }, [isLoading, token, isSuper, requireSuper, router])

  if (isLoading || !isAuthorized) {
    return <LoadingSpinner />
  }

  return <>{children}</>
}
