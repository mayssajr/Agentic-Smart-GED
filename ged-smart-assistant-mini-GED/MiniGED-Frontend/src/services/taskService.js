import apiClient from "./api";

export async function getTasks() {
  try {
    const response = await apiClient.get("/task");
    return response.data;
  } catch (error) {
    console.error("Erreur lors du chargement des tâches :", error);
    throw error;
  }
}

export async function getTasksByDocument(documentId) {
  try {
    const response = await apiClient.get(`/task/document/${documentId}`);
    return response.data;
  } catch (error) {
    console.error("Erreur lors du chargement des tâches :", error);
    throw error;
  }
}

export async function createTask(taskData) {
  try {
    const response = await apiClient.post("/task", taskData);
    return response.data;
  } catch (error) {
    console.error("Erreur lors de la création de la tâche :", error);
    throw error;
  }
}

export async function updateTask(taskId, taskData) {
  try {
    const response = await apiClient.put(`/task/${taskId}`, taskData);
    return response.data;
  } catch (error) {
    console.error("Erreur lors de la modification de la tâche :", error);
    throw error;
  }
}

export async function deleteTask(taskId) {
  try {
    const response = await apiClient.delete(`/task/${taskId}`);
    return response.data;
  } catch (error) {
    console.error("Erreur lors de la suppression de la tâche :", error);
    throw error;
  }
}

export async function updateTaskStatus(taskId, status) {
  try {
    const response = await apiClient.patch(`/task/${taskId}/status`, { status });
    return response.data;
  } catch (error) {
    console.error("Erreur lors de la mise à jour du statut de la tâche :", error);
    throw error;
  }
}

export async function getTaskById(taskId) {
  try {
    const response = await apiClient.get(`/task/${taskId}`);
    return response.data;
  } catch (error) {
    console.error("Erreur lors du chargement de la tâche :", error);
    throw error;
  }
}
