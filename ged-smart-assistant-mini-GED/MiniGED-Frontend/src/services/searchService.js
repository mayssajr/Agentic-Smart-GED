import apiClient from "./api";

export async function searchDocuments(payload) {
  const response = await apiClient.post("/document/search", payload);
  return response.data;
}
