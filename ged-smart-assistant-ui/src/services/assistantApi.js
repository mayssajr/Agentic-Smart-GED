import axios from 'axios'
import {
  ASSISTANT_API_BASE_URL,
  SOURCE_SYSTEM,
} from '../config/runtime'

const ACCESS_TOKEN_STORAGE_KEY = 'assistant_access_token'
const REFRESH_TOKEN_STORAGE_KEY = 'assistant_refresh_token'

const api = axios.create({
  baseURL: ASSISTANT_API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

const storeSessionTokens = ({ accessToken, refreshToken }) => {
  if (accessToken) {
    sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken)
  }

  if (refreshToken) {
    sessionStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken)
  }
}

const clearSessionTokens = () => {
  sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
}

const getStoredSessionTokens = () => ({
  accessToken: sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY),
  refreshToken: sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY),
})

api.interceptors.request.use((config) => {
  const { accessToken, refreshToken } = getStoredSessionTokens()

  if (accessToken) {
    config.headers['X-Ged-Access-Token'] = accessToken
  }

  if (refreshToken) {
    config.headers['X-Ged-Refresh-Token'] = refreshToken
  }

  return config
})

api.interceptors.response.use(
  (response) => {
    const accessToken = response.headers['x-ged-access-token']
    const refreshToken = response.headers['x-ged-refresh-token']

    if (accessToken || refreshToken) {
      storeSessionTokens({ accessToken, refreshToken })
    }

    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      clearSessionTokens()
    }

    return Promise.reject(error)
  }
)

export const assistantAuthService = {
  async getSession() {
    const response = await api.get('/api/Auth/me')
    return response.data
  },

  async bootstrap({ accessToken, refreshToken, user }) {
    storeSessionTokens({ accessToken, refreshToken })

    const response = await api.post('/api/Auth/bootstrap', {
      accessToken,
      refreshToken,
      user,
      sourceSystem: SOURCE_SYSTEM,
    })

    return response.data
  },

  async logout() {
    await api.post('/api/Auth/logout')
    clearSessionTokens()
  },
}

// Contexte document courant (mis à jour depuis DocumentDetails)
let _currentDocContext = { documentId: '', documentType: '', filename: '' }

export const assistantChatService = {
  setDocumentContext(ctx) {
    _currentDocContext = { ..._currentDocContext, ...ctx }
  },

  clearDocumentContext() {
    _currentDocContext = { documentId: '', documentType: '', filename: '' }
  },

  async sendMessage(message) {
    const response = await api.post('/api/Chat', {
      message,
      documentId:   _currentDocContext.documentId   || undefined,
      documentType: _currentDocContext.documentType || undefined,
      filename:     _currentDocContext.filename     || undefined,
    })
    return response.data
  },
}

// Écoute les messages DOC_CONTEXT depuis MiniGED-Frontend
window.addEventListener('message', (e) => {
  console.log('[assistantApi] message reçu depuis', e.origin, '| type:', e.data?.type)

  // Accepte uniquement depuis l'origine MiniGED connue
  const allowedOrigins = [
    import.meta.env.VITE_MINIGED_ORIGIN || 'http://localhost:3000',
    'http://localhost:3000',
    'https://localhost:3000',
  ]
  if (!allowedOrigins.includes(e.origin)) return
  if (e.data?.type !== 'DOC_CONTEXT') return
  const ctx = e.data.payload || {}
  assistantChatService.setDocumentContext(ctx)
})

export default api
