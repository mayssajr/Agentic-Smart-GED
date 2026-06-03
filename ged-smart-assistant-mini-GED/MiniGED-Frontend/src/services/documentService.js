import apiClient from "./api";

export async function getUserDocuments() {
  try {
    const response = await apiClient.get("/document");
    return response.data;
  } catch (error) {
    console.error("Erreur lors du chargement des documents :", error);
    throw error;
  }
}

export async function createDocument(documentData) {
  try {
    const response = await apiClient.post("/document/add", documentData);
    return response.data;
  } catch (error) {
    console.error("Erreur lors de la création du document :", error);
    throw error;
  }
}

export async function deleteDocument(documentId) {
  try {
    const response = await apiClient.delete(`/document/${documentId}`);
    return response.data;
  } catch (error) {
    console.error("Erreur lors de la suppression du document :", error);
    throw error;
  }
}

export async function updateDocument(documentId, documentData) {
  try {
    const response = await apiClient.put(`/document/${documentId}`, documentData);
    return response.data;
  } catch (error) {
    console.error("Erreur lors de la modification du document :", error);
    throw error;
  }
}

export async function getDocumentById(documentId) {
  try {
    const response = await apiClient.get(`/document/${documentId}`);
    return response.data;
  } catch (error) {
    console.error("Erreur lors du chargement du document :", error);
    throw error;
  }
}
