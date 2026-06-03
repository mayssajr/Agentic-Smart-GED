const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!rawApiBaseUrl) {
  throw new Error("Missing VITE_API_BASE_URL in frontend environment");
}

const API_BASE_URL = rawApiBaseUrl.replace(/\/$/, "");
const API_ORIGIN_URL = API_BASE_URL.replace(/\/api\/?$/, "");

const joinUrl = (baseUrl, path = "") => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
};

export const API_REFRESH_TOKEN_URL = joinUrl(API_ORIGIN_URL, "/users/refresh-token");
export const DOCUMENT_PDF_URL = (documentId) =>
  joinUrl(API_BASE_URL, `/document/pdf/${documentId}`);
export { API_BASE_URL, API_ORIGIN_URL, joinUrl };
