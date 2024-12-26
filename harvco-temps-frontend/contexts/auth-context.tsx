"use client"

import { createContext, useContext, useState, useEffect, useCallback } from "react"
import { AuthContextType, LoginCredentials, Token, User } from "@/types/auth"
import { getApiUrl } from "@/utils/api"

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const isSuper = currentUser?.is_superuser ?? false

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

  useEffect(() => {
    if (token) {
      fetchCurrentUser()
    } else {
      setCurrentUser(null)
    }
  }, [token, fetchCurrentUser])

  const refreshToken = async (): Promise<string> => {
    try {
      const res = await fetch(getApiUrl("/api/v1/auth/refresh"), {
        method: "POST",
        credentials: "include",
      })

      if (!res.ok) {
        throw new Error("Token refresh failed")
      }

      const data: Token = await res.json()
      const fullToken = `${data.token_type} ${data.access_token}`
      localStorage.setItem("token", fullToken)
      setToken(fullToken)
      return fullToken
    } catch (error) {
      console.error("Token refresh error:", error)
      logout() // Clear auth state if refresh fails
      throw error
    }
  }

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
        credentials: "include",
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
    setCurrentUser(null)
  }

  const fetchCurrentUser = useCallback(async () => {
    if (!token) return
    try {
      const response = await fetchWithToken(getApiUrl("/api/v1/users/me"))
      if (response.ok) {
        const userData = await response.json()
        setCurrentUser(userData)
      }
    } catch (error) {
      console.error("Error fetching current user:", error)
    }
  }, [token, fetchWithToken])

  const fetchWithToken = async (
    url: string,
    options: RequestInit = {}
  ): Promise<Response> => {
    const makeRequest = async (accessToken: string) => {
      const headers = new Headers(options.headers || {})
      headers.set("Authorization", accessToken)

      return fetch(url, {
        ...options,
        headers,
        credentials: "include",
      })
    }

    try {
      // Try the request with current token
      if (!token) throw new Error("No token available")

      let response = await makeRequest(token)

      // If unauthorized, try to refresh token and retry request
      if (response.status === 401) {
        const newToken = await refreshToken()
        response = await makeRequest(newToken)
      }

      return response
    } catch (error) {
      console.error("API request failed:", error)
      throw error
    }
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
        fetchWithToken,
        currentUser,
        isSuper,
        isLoading,
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
