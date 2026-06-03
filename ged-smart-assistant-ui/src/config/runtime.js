const getRequiredEnv = (key, fallback) => {
  const value = import.meta.env[key] ?? fallback

  if (!value) {
    throw new Error(`Missing ${key} in assistant frontend environment`)
  }

  return value
}

const normalizeUrl = (value) => value.replace(/\/$/, '')

const parseOrigins = (value) =>
  value
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean)

export const ASSISTANT_API_BASE_URL = normalizeUrl(
  getRequiredEnv('VITE_ASSISTANT_API_BASE_URL', 'https://localhost:53581')
)

export const ALLOWED_PARENT_ORIGINS = parseOrigins(
  getRequiredEnv('VITE_ALLOWED_PARENT_ORIGINS', 'http://localhost:5173')
)

export const SOURCE_SYSTEM = getRequiredEnv('VITE_SOURCE_SYSTEM', 'mini-ged')
