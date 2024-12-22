"use client"

import { createContext, useContext, useState, useEffect } from "react"
import { AuthContextType, LoginCredentials, Token } from "@/types/auth"
import { getApiUrl } from "@/utils/api"

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    try {
      const savedToken = localStorage.getItem("token")
      if (savedToken) {
        setToken(savedToken)
      }
    } catch (error) {
      console.error("Error loading auth state:", error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = async (credentials: LoginCredentials) => {
    try {
      const formData = new URLSearchParams()
      formData.append("username", credentials.username)
      formData.append("password", credentials.password)
      formData.append("grant_type", "password")

      const res = await fetch(getApiUrl("/api/v1/auth/login"), {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
        credentials: "include", // Add this to handle cookies if your API uses them
      })

      if (!res.ok) {
        const error = await res.text()
        throw new Error(error || "Login failed")
      }

      const data: Token = await res.json()
      const fullToken = `${data.token_type} ${data.access_token}`
      localStorage.setItem("token", fullToken)
      setToken(fullToken)
    } catch (error) {
      console.error("Login error:", error)
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem("token")
    setToken(null)
  }

  if (isLoading) {
    return null
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

