export interface Token {
  access_token: string
  token_type: string
}

export interface LoginCredentials {
  username: string
  password: string
  grant_type?: "password"
  scope?: string
  client_id?: string
  client_secret?: string
}

export interface AuthContextType {
  token: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  fetchWithToken: (url: string, options?: RequestInit) => Promise<Response>
}

