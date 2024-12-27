"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth-context"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

export default function HomePage() {
  const { token, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading) {
      if (token) {
        router.replace("/dashboard")
      } else {
        router.replace("/login")
      }
    }
  }, [token, isLoading, router])

  return <LoadingSpinner />
}

