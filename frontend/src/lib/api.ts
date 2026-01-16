import axios from 'axios'

const API_BASE_URL = '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
            params: { refresh_token: refreshToken },
          })
          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }

    return Promise.reject(error)
  }
)

// API functions
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (email: string, password: string, fullName?: string) =>
    api.post('/auth/register', { email, password, full_name: fullName }),
  getMe: () => api.get('/auth/me'),
}

export const toursApi = {
  list: (params?: {
    page?: number
    page_size?: number
    destination?: string
    category?: string
    search?: string
    min_price?: number
    max_price?: number
  }) => api.get('/tours', { params }),
  get: (id: number) => api.get(`/tours/${id}`),
  getDestinations: () => api.get('/tours/destinations'),
  getCategories: () => api.get('/tours/categories'),
  getPriceHistory: (tourId: number, days?: number) =>
    api.get(`/tours/${tourId}/prices`, { params: { days } }),
  getPriceStats: (tourId: number) => api.get(`/tours/${tourId}/prices/stats`),
}

export const alertsApi = {
  list: () => api.get('/alerts'),
  listWithTours: () => api.get('/alerts/with-tours'),
  create: (data: {
    tour_id: number
    alert_type: string
    threshold_price?: number
    threshold_percentage?: number
  }) => api.post('/alerts', data),
  update: (id: number, data: { threshold_price?: number; status?: string }) =>
    api.patch(`/alerts/${id}`, data),
  delete: (id: number) => api.delete(`/alerts/${id}`),
  pause: (id: number) => api.post(`/alerts/${id}/pause`),
  resume: (id: number) => api.post(`/alerts/${id}/resume`),
}

export const notificationsApi = {
  list: (params?: { page?: number; unread_only?: boolean }) =>
    api.get('/notifications', { params }),
  listWithTours: () => api.get('/notifications/with-tours'),
  markAsRead: (id: number) => api.post(`/notifications/${id}/read`),
  markAllAsRead: () => api.post('/notifications/read-all'),
  delete: (id: number) => api.delete(`/notifications/${id}`),
}
