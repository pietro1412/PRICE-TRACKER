import { create } from 'zustand'
import { authApi } from '@/lib/api'

interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    const response = await authApi.login(email, password)
    const { access_token, refresh_token } = response.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)

    const userResponse = await authApi.getMe()
    set({ user: userResponse.data, isAuthenticated: true })
  },

  register: async (email: string, password: string, fullName?: string) => {
    await authApi.register(email, password, fullName)
    // Auto-login after registration
    const response = await authApi.login(email, password)
    const { access_token, refresh_token } = response.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)

    const userResponse = await authApi.getMe()
    set({ user: userResponse.data, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },

  checkAuth: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      set({ isLoading: false })
      return
    }

    try {
      const response = await authApi.getMe()
      set({ user: response.data, isAuthenticated: true, isLoading: false })
    } catch {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },
}))
