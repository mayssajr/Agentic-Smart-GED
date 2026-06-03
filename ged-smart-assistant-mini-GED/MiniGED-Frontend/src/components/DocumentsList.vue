<template>
  <div class="documents-list-container">
    <!-- Header -->
    <header class="documents-header">
      <div class="breadcrumb">
        <span></span>
        <span>Accueil</span>
        <span>></span>
        <span>Gestionnaire de documents</span>
        <span>></span>
        <span class="breadcrumb-current">Mes documents</span>
      </div>
    </header>

    <!-- Page Content -->
    <div class="page-content">
      <div class="page-title-section">
        <h1 class="page-title">Mes Documents</h1>
        <button class="add-document-btn" @click="addDocument">
          <span>Ajouter un document</span>
          <i class="fas fa-plus btn-icon"></i>
        </button>
        <AddDocumentModal
          :visible="isAddDocumentModalVisible || isEditDocumentModalVisible"
          :document="editingDocument"
          @close="closeAddDocumentModal"
          @added="handleDocumentAdded"
          @updated="handleUpdateDocument"
        />
      </div>

      <!-- Document View Toggle -->
      <div class="view-controls">
        <div class="flex gap-2 bg-slate-100 p-1 rounded-lg w-fit">
          <!-- Tabs View -->
          <div class="relative group">
            <button
              @click="setView('tabs')"
              class="p-2 rounded-md transition"
              :class="
                currentView === 'tabs'
                  ? 'bg-white shadow text-slate-800'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200'
              "
            >
              <i class="fa-solid fa-table-columns"></i>
            </button>

            <span
              class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-xs text-white bg-slate-800 px-2 py-1 rounded shadow whitespace-nowrap pointer-events-none"
            >
              Vue par onglets
            </span>
          </div>

          <!-- Grid View -->
          <div class="relative group">
            <button
              @click="setView('grid')"
              class="p-2 rounded-md transition"
              :class="
                currentView === 'grid'
                  ? 'bg-white shadow text-slate-800'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200'
              "
            >
              <i class="fa-solid fa-grip"></i>
            </button>

            <span
              class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-xs text-white bg-slate-800 px-2 py-1 rounded shadow whitespace-nowrap pointer-events-none"
            >
              Vue en grille
            </span>
          </div>
        </div>
        <div class="relative max-w-sm">
          <input
            id="search-input"
            type="text"
            placeholder="Recherche..."
            class="w-64 pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            v-model="searchQuery"
          />
          <span
            class="absolute left-3 inset-y-0 flex items-center pointer-events-none"
          >
            <i class="fas fa-magnifying-glass text-gray-400"></i>
          </span>
        </div>
      </div>

      <!-- Documents Views -->
      <!-- Table View (Vue par onglets) -->
      <div v-if="currentView === 'tabs'" class="documents-table-container">
        <div v-if="loading" class="loading">Chargement des documents...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="filteredDocuments.length === 0" class="empty-state">
          <div class="empty-state-icon">
            <i class="text-slate-600 fa-solid fa-border-none"></i>
          </div>
          <p class="empty-state-title">
            {{
              searchQuery
                ? "Aucun document ne correspond à votre recherche"
                : "Aucun document pour le moment"
            }}
          </p>
          <p class="empty-state-subtitle" v-if="!searchQuery">
            Cliquez sur « Ajouter un document » pour commencer.
          </p>
        </div>
        <table v-else class="documents-table">
          <thead>
            <tr>
              <th>
                <input type="checkbox" class="select-all" />
                Nom du document
              </th>
              <th>Description</th>
              <th>Accès utilisateur</th>
              <th>Dernière modification</th>
              <th width="25px">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="document in filteredDocuments"
              :key="document.id"
              class="document-row"
            >
              <td class="document-name-cell">
                <input type="checkbox" class="row-select" />
                <div class="document-icon">
                  <i class="text-slate-600 fas fa-file-lines"></i>
                </div>
                <span class="document-name">{{ document.title }}</span>

                <!-- ← AJOUTER : badge compact si c'est une candidature -->
                <CandidateStatusBadge
                  v-if="getCandidateStatus(document.id)"
                  :status="getCandidateStatus(document.id)"
                  compact
                />
              </td>
              <td class="document-description">
                <div class="description-content">
                  {{ document.description || "Aucune description" }}
                </div>
              </td>
              <td class="document-users">
                <div class="user-avatars">
                  <div class="user-avatar-small">
                    {{ authStore.user?.username[0].toUpperCase() }}
                  </div>
                </div>
              </td>
              <td class="document-date">
                {{ formatDate(document.uploadedAt) }}
              </td>
              <td class="document-actions">
                <button
                  class="action-btn view"
                  @click="viewDocument(document.id)"
                >
                  Voir
                </button>
                <button class="action-btn edit" @click="editDocument(document)">
                  Modifier
                </button>
                <button
                  class="action-btn delete"
                  @click="confirmDeleteDocument(document.id)"
                >
                  Supprimer
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Grid View (Vue en grille) -->
      <div v-if="currentView === 'grid'" class="documents-grid-wrapper">
        <div v-if="loading" class="loading">Chargement des documents...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="filteredDocuments.length === 0" class="empty-state">
          <i class="text-slate-600 fa-solid fa-border-none"></i>
          <p class="empty-state-title">
            {{
              searchQuery
                ? "Aucun document ne correspond à votre recherche"
                : "Aucun document pour le moment"
            }}
          </p>
          <p class="empty-state-subtitle" v-if="!searchQuery">
            Cliquez sur « Ajouter un document » pour commencer.
          </p>
        </div>
        <div v-else class="documents-grid">
          <div
            v-for="document in filteredDocuments"
            :key="document.id"
            class="document-card"
          >
            <div class="card-header">
              <input type="checkbox" class="card-select" />
              <div class="card-menu">
                <i class="text-slate-600 fas fa-ellipsis-vertical"></i>
              </div>
            </div>
            <div class="card-icon">
              <i class="text-slate-600 fas fa-file-lines"></i>
            </div>
            <div class="card-content">
              <h3 class="card-title">{{ document.title }}</h3>
              <p class="card-description">
                {{ document.description || "Aucune description" }}
              </p>
              <div class="card-users">
                <div class="user-avatars">
                  <div class="user-avatar-small">
                    {{ authStore.user?.username[0].toUpperCase() }}
                  </div>
                </div>
              </div>
              <p class="card-date">{{ formatDate(document.uploadedAt) }}</p>
            </div>
            <div class="card-actions">
              <button
                class="action-btn view"
                @click="viewDocument(document.id)"
              >
                Voir
              </button>
              <button class="action-btn edit" @click="editDocument(document)">
                Modifier
              </button>
              <button
                class="action-btn delete"
                @click="confirmDeleteDocument(document.id)"
              >
                Supprimer
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de confirmation de suppression -->
    <DeleteDocumentModal
      :visible="showDeleteModal"
      :deleting="deleting"
      @close="cancelDelete"
      @confirm="confirmDelete"
    />

    <!-- Modal pour les tâches -->
    <TaskModal
      :visible="isTaskModalVisible"
      :task="editingTask"
      :documentId="currentDocumentId"
      @close="closeTaskModal"
      @added="handleTaskAdded"
      @updated="handleTaskUpdated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  getUserDocuments,
  deleteDocument as deleteDocumentService,
  updateDocument as updateDocumentService,
} from "../services/documentService";
import {
  getTasks,
  getTasksByDocument,
  deleteTask as deleteTaskService,
  updateTaskStatus as updateTaskStatusService,
} from "../services/taskService";
import { useAuthStore } from "../stores/auth";
import AddDocumentModal from "./AddDocumentModal.vue";
import DeleteDocumentModal from "./DeleteDocumentModal.vue";
import TaskModal from "./TaskModal.vue";
import CandidateStatusBadge from './CandidateStatusBadge.vue'
import { getCandidateStatuses } from '../services/recruitmentService.js'


const isAddDocumentModalVisible = ref(false);
const isEditDocumentModalVisible = ref(false);
const editingDocument = ref(null);

// Variables pour les tâches
const isTaskModalVisible = ref(false);
const editingTask = ref(null);
const currentDocumentId = ref(null);
const documentTasks = ref({}); // Pour stocker les tâches par document ID
const allTasks = ref([]); // Pour stocker toutes les tâches

// Map documentId → statut candidature
const candidateStatuses = ref({})

const showAddDocumentModal = () => {
  isAddDocumentModalVisible.value = true;
};
const closeAddDocumentModal = () => {
  isAddDocumentModalVisible.value = false;
  isEditDocumentModalVisible.value = false;
  editingDocument.value = null;
};
const authStore = useAuthStore();
const router = useRouter();
const currentView = ref("tabs");
const documents = ref([]);
const loading = ref(false);
const error = ref(null);
const searchQuery = ref("");
const showDeleteModal = ref(false);
const documentToDelete = ref(null);
const deleting = ref(false);

const setView = (view) => {
  currentView.value = view;
};

const filteredDocuments = computed(() => {
  if (!searchQuery.value) return documents.value;
  const q = searchQuery.value.toLowerCase();
  return documents.value.filter(
    (doc) =>
      doc.title?.toLowerCase().includes(q) ||
      doc.description?.toLowerCase().includes(q),
  );
});

const loadDocuments = async () => {
  loading.value = true;
  error.value = null;
  try {
    const docs = await getUserDocuments();
    documents.value = docs;
    // Charger automatiquement toutes les tâches après avoir chargé les documents
    await loadAllTasks();
    await loadCandidateStatuses()  // ← ajouter
  } catch (err) {
    error.value = "Erreur lors du chargement des documents";
    console.error("Erreur:", err);
  } finally {
    loading.value = false;
  }
};

const formatDate = (dateString) => {
  if (!dateString) return "—";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("fr-FR");
};

const addDocument = () => {
  showAddDocumentModal();
};

const editDocument = (document) => {
  try {
    editingDocument.value = document;
    isEditDocumentModalVisible.value = true;
  } catch (err) {
    error.value = "Erreur lors du chargement du document";
    console.error("Erreur:", err);
  }
};

const confirmDeleteDocument = (id) => {
  documentToDelete.value = id;
  showDeleteModal.value = true;
};

const cancelDelete = () => {
  showDeleteModal.value = false;
  documentToDelete.value = null;
  deleting.value = false;
};

const confirmDelete = async () => {
  if (!documentToDelete.value) return;

  deleting.value = true;
  try {
    await deleteDocumentService(documentToDelete.value);
    documents.value = documents.value.filter(
      (doc) => doc.id !== documentToDelete.value,
    );
    showDeleteModal.value = false;
    documentToDelete.value = null;

    // Rafraîchir automatiquement la page après suppression
    setTimeout(() => {
      window.location.reload();
    }, 500);
  } catch (err) {
    error.value = "Erreur lors de la suppression du document";
    console.error("Erreur:", err);
  } finally {
    deleting.value = false;
  }
};

const handleDocumentAdded = async () => {
  try {
    await loadDocuments();
    // Rafraîchir automatiquement la page après ajout
    setTimeout(() => {
      window.location.reload();
    }, 500);
  } catch (err) {
    error.value = "Erreur lors de l'ajout du document";
    console.error("Erreur:", err);
  }
};

const handleUpdateDocument = async (documentData) => {
  try {
    if (editingDocument.value && editingDocument.value.id) {
      const documentId = editingDocument.value.id;
      await updateDocumentService(documentId, documentData);

      // Mettre à jour le document dans la liste locale
      const index = documents.value.findIndex((doc) => doc.id === documentId);
      if (index !== -1) {
        documents.value[index] = { ...documents.value[index], ...documentData };
      }

      isEditDocumentModalVisible.value = false;
      editingDocument.value = null;

      // Rafraîchir automatiquement la page après modification
      setTimeout(() => {
        window.location.reload();
      }, 500);
    }
  } catch (err) {
    error.value = "Erreur lors de la modification du document";
    console.error("Erreur:", err);
  }
};

const viewDocument = (id) => {
  router.push(`/document/${id}`);
};

// Fonctions pour les tâches
const loadTasksForDocument = async (documentId) => {
  try {
    const tasks = await getTasksByDocument(documentId);
    documentTasks.value[documentId] = tasks;
  } catch (err) {
    console.error("Erreur lors du chargement des tâches:", err);
  }
};

// Charger toutes les tâches au chargement des documents
const loadAllTasks = async () => {
  try {
    // Charger toutes les tâches globales
    const tasks = await getTasks();
    allTasks.value = tasks;

    // Charger aussi les tâches par document pour la vue table
    const tasksPromises = documents.value.map(async (document) => {
      try {
        const documentTasksList = await getTasksByDocument(document.id);
        documentTasks.value[document.id] = documentTasksList;
      } catch (err) {
        console.error(
          `Erreur lors du chargement des tâches pour le document ${document.id}:`,
          err,
        );
        documentTasks.value[document.id] = [];
      }
    });
    await Promise.all(tasksPromises);
  } catch (err) {
    console.error("Erreur lors du chargement global des tâches:", err);
  }
};

const loadCandidateStatuses = async () => {
  candidateStatuses.value = await getCandidateStatuses(authStore.token)
}

const getCandidateStatus = (documentId) =>
  candidateStatuses.value[documentId] || null

const showTaskModal = (documentId = null, task = null) => {
  currentDocumentId.value = documentId;
  editingTask.value = task;
  isTaskModalVisible.value = true;
};

const closeTaskModal = () => {
  isTaskModalVisible.value = false;
  editingTask.value = null;
  currentDocumentId.value = null;
};

const handleTaskAdded = (newTask) => {
  if (currentDocumentId.value) {
    if (!documentTasks.value[currentDocumentId.value]) {
      documentTasks.value[currentDocumentId.value] = [];
    }
    documentTasks.value[currentDocumentId.value].push(newTask);
  }
  // Ajouter aussi à la liste globale
  allTasks.value.push(newTask);
  closeTaskModal();
};

const handleTaskUpdated = (updatedTask) => {
  if (currentDocumentId.value && documentTasks.value[currentDocumentId.value]) {
    const index = documentTasks.value[currentDocumentId.value].findIndex(
      (t) => t.id === updatedTask.id,
    );
    if (index !== -1) {
      documentTasks.value[currentDocumentId.value][index] = updatedTask;
    }
  }
  // Mettre à jour aussi dans la liste globale
  const globalIndex = allTasks.value.findIndex((t) => t.id === updatedTask.id);
  if (globalIndex !== -1) {
    allTasks.value[globalIndex] = updatedTask;
  }
  closeTaskModal();
};

const handleTaskStatusChange = async (taskId, newStatus) => {
  try {
    await updateTaskStatusService(taskId, newStatus);
    // Mettre à jour la tâche dans la liste locale
    Object.keys(documentTasks.value).forEach((documentId) => {
      const taskIndex = documentTasks.value[documentId].findIndex(
        (t) => t.id === taskId,
      );
      if (taskIndex !== -1) {
        documentTasks.value[documentId][taskIndex].status = newStatus;
      }
    });
    // Mettre à jour aussi dans la liste globale
    const globalIndex = allTasks.value.findIndex((t) => t.id === taskId);
    if (globalIndex !== -1) {
      allTasks.value[globalIndex].status = newStatus;
    }
  } catch (err) {
    error.value = "Erreur lors de la mise à jour du statut de la tâche";
    console.error("Erreur:", err);
  }
};

const deleteTask = async (taskId) => {
  try {
    await deleteTaskService(taskId);
    // Supprimer la tâche de la liste locale
    Object.keys(documentTasks.value).forEach((documentId) => {
      documentTasks.value[documentId] = documentTasks.value[documentId].filter(
        (t) => t.id !== taskId,
      );
    });
    // Supprimer aussi de la liste globale
    allTasks.value = allTasks.value.filter((t) => t.id !== taskId);
  } catch (err) {
    error.value = "Erreur lors de la suppression de la tâche";
    console.error("Erreur:", err);
  }
};

const getTasksForDocument = (documentId) => {
  return documentTasks.value[documentId] || [];
};

// Fonctions utilitaires pour la vue tâches
const getTaskPriorityClass = (priority) => {
  const classes = {
    0: "low",
    1: "medium",
    2: "high",
  };
  return classes[priority] || "medium";
};

const getTaskStatusClass = (status) => {
  const classes = {
    0: "pending",
    1: "in-progress",
    2: "completed",
    3: "cancelled",
  };
  return classes[status] || "pending";
};

const editTask = (task) => {
  showTaskModal(task.documentId, task);
};

const getTaskPriorityLabel = (priority) => {
  const labels = {
    0: "Basse",
    1: "Moyenne",
    2: "Haute",
    3: "Urgente",
  };
  return labels[priority] || "Moyenne";
};

const getTaskStatusLabel = (status) => {
  const labels = {
    0: "En attente",
    1: "En cours",
    2: "Terminée",
    3: "Annulée",
  };
  return labels[status] || "En attente";
};

const getTaskPriorityColor = (priority) => {
  const colors = {
    0: "bg-gray-100 text-gray-800",
    1: "bg-blue-100 text-blue-800",
    2: "bg-orange-100 text-orange-800",
    3: "bg-red-100 text-red-800",
  };
  return colors[priority] || colors[1];
};

const getTaskStatusColor = (status) => {
  const colors = {
    0: "bg-gray-100 text-gray-800",
    1: "bg-yellow-100 text-yellow-800",
    2: "bg-green-100 text-green-800",
    3: "bg-red-100 text-red-800",
  };
  return colors[status] || colors[0];
};

onMounted(() => {
  loadDocuments();
});
</script>

<style scoped>
.documents-list-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.documents-header {
  padding: 1rem 2rem;
  background-color: white;
  border-bottom: 1px solid #e9ecef;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 14px;
  color: #718096;
}

.breadcrumb-current {
  color: #2d3748;
  font-weight: 500;
}

.page-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

.page-title-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: bold;
  color: #2d3748;
  margin: 0;
}

.add-document-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.2s;
}

.add-document-btn:hover {
  transform: translateY(-1px);
}

.view-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.view-tabs {
  display: flex;
  gap: 0.5rem;
}

.view-tab {
  padding: 0.5rem 1rem;
  border: 1px solid #e2e8f0;
  background-color: white;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.view-tab:hover {
  border-color: #cbd5e0;
}

.view-tab.active {
  background-color: #667eea;
  color: white;
  border-color: #667eea;
}

.loading,
.error {
  text-align: center;
  padding: 2rem;
  color: #718096;
}

.error {
  color: #e53e3e;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: #718096;
  text-align: center;
}

.empty-state-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state-title {
  font-size: 1rem;
  font-weight: 500;
  color: #4a5568;
  margin: 0 0 0.5rem 0;
}

.empty-state-subtitle {
  font-size: 14px;
  margin: 0;
}

/* Table View Styles */
.documents-table-container {
  background-color: white;
  border-radius: 12px;
  border: 1px solid #e9ecef;
  overflow: hidden;
}

.documents-table {
  width: 100%;
  border-collapse: collapse;
}

.documents-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 500;
  color: #4a5568;
  border-bottom: 1px solid #e9ecef;
  background-color: #f8f9fa;
  font-size: 14px;
}

.documents-table td {
  padding: 1rem;
  border-bottom: 1px solid #f1f3f4;
}

.document-row:hover {
  background-color: #f8f9fa;
}

.document-name-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.document-icon {
  font-size: 18px;
}

.document-name {
  font-weight: 500;
  color: #2d3748;
}

.document-description {
  color: #718096;
  font-size: 14px;
  max-width: 200px;
}

.description-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-avatars {
  display: flex;
  align-items: center;
}

.user-avatar-small {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: bold;
  border: 2px solid white;
}

.document-date {
  color: #718096;
  font-size: 14px;
}

.document-actions {
  display: flex;
  align-items: center;
  justify-content: end;
  gap: 0.5rem;
}

.action-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.delete {
  color: #e53e3e;
  background-color: white;
}

.action-btn.delete:hover {
  background-color: #fed7d7;
  border-color: #feb2b2;
}

.action-btn.edit {
  color: #667eea;
  background-color: white;
}

.action-btn.edit:hover {
  background-color: #e6fffa;
  border-color: #b2f5ea;
}

.action-btn.view {
  color: #38a169;
  background-color: white;
}

.action-btn.view:hover {
  background-color: #f0fff4;
  border-color: #9ae6b4;
}

/* Grid View Styles */
.documents-grid-wrapper {
  width: 100%;
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.document-card {
  background-color: white;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
  cursor: pointer;
}

.document-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #667eea;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-menu {
  color: #cbd5e0;
  cursor: pointer;
  padding: 0.25rem;
}

.card-icon {
  font-size: 48px;
  text-align: center;
  margin-bottom: 1rem;
}

.card-content {
  text-align: center;
}

.card-title {
  font-size: 16px;
  font-weight: 500;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.card-description {
  color: #718096;
  font-size: 14px;
  margin: 0 0 0.75rem 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-users {
  margin-bottom: 0.75rem;
  display: flex;
  justify-content: center;
}

.card-date {
  color: #718096;
  font-size: 13px;
  margin: 0 0 1rem 0;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

@media (max-width: 768px) {
  .page-content {
    padding: 1rem;
  }

  .page-title-section {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .view-controls {
    flex-direction: column;
    gap: 1rem;
  }

  .documents-grid {
    grid-template-columns: 1fr;
  }

  .documents-table-container {
    overflow-x: auto;
  }

  .documents-table {
    min-width: 600px;
  }
}

/* Styles pour les tâches - Version améliorée */
.tasks-section {
  margin-top: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.tasks-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tasks-title::before {
  content: "📋";
  font-size: 16px;
}

.add-task-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border: none;
  border-radius: 8px;
  width: 28px;
  height: 28px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

.add-task-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
}

.add-task-btn:active {
  transform: translateY(0);
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.2s ease;
  position: relative;
}

.task-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.task-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
  word-wrap: break-word;
  transition: color 0.2s ease;
  min-width: 150px;
}

.task-title.completed {
  text-decoration: line-through;
  color: #94a3b8;
  opacity: 0.7;
}

.task-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.priority-badge,
.status-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 20px;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

/* Priorité colors */
.priority-badge {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #475569;
  border: 1px solid #cbd5e1;
}

.priority-badge:nth-child(1) {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  color: #64748b;
  border-color: #e2e8f0;
}

.priority-badge:nth-child(2) {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  border-color: #93c5fd;
}

.priority-badge:nth-child(3) {
  background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%);
  color: #c2410c;
  border-color: #fb923c;
}

.priority-badge:nth-child(4) {
  background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
  color: #b91c1c;
  border-color: #f87171;
}

/* Status colors */
.status-badge {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #475569;
  border: 1px solid #cbd5e1;
}

.status-badge:nth-child(2) {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  border-color: #fbbf24;
}

.status-badge:nth-child(3) {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #059669;
  border-color: #34d399;
}

.status-badge:nth-child(4) {
  background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
  color: #b91c1c;
  border-color: #f87171;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-status-select {
  font-size: 11px;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.task-status-select:hover {
  border-color: #94a3b8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.task-status-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.task-delete-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 6px;
  width: 24px;
  height: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
}

.task-delete-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

.task-delete-btn:active {
  transform: scale(0.95);
}

.no-tasks-message {
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
  padding: 12px;
  font-style: italic;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 6px;
  border: 1px dashed #e2e8f0;
}

/* Animations supplémentaires */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.task-item {
  animation: slideIn 0.3s ease;
}

/* Styles pour la vue tâches séparée */
.tasks-view-container {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 16px;
  padding: 2rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e2e8f0;
}

.tasks-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.add-task-btn-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.add-task-btn-main:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
}

.add-task-btn-main svg {
  width: 1.25rem;
  height: 1.25rem;
}

.all-tasks-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-item-main {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.task-item-main::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  opacity: 0.8;
}

.task-item-main:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
  border-color: #cbd5e1;
}

.task-content-main {
  margin-left: 1rem;
}

.task-header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.task-title-main {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  line-height: 1.4;
  flex: 1;
}

.task-badges-main {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.priority-badge-main,
.status-badge-main {
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.priority-badge-main.low {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
  border: 1px solid #34d399;
}

.priority-badge-main.medium {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  border: 1px solid #fbbf24;
}

.priority-badge-main.high {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: #b91c1c;
  border: 1px solid #f87171;
}

.status-badge-main.pending {
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  color: #374151;
  border: 1px solid #d1d5db;
}

.status-badge-main.in-progress {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1d4ed8;
  border: 1px solid #93c5fd;
}

.status-badge-main.completed {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
  border: 1px solid #34d399;
}

.status-badge-main.cancelled {
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  color: #6b7280;
  border: 1px solid #9ca3af;
}

.task-description-main {
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
}

.task-footer-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.task-info-main {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.task-document-main,
.task-date-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.task-document-main svg,
.task-date-main svg {
  width: 1rem;
  height: 1rem;
  color: #9ca3af;
}

.task-actions-main {
  display: flex;
  gap: 0.5rem;
}

.action-btn-main {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn-main svg {
  width: 1.125rem;
  height: 1.125rem;
}

.action-btn-main.edit {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.action-btn-main.edit:hover {
  background: #e5e7eb;
  color: #374151;
  border-color: #d1d5db;
}

.action-btn-main.delete {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.action-btn-main.delete:hover {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fecaca;
}

/* Responsive design */
/* Tablettes (768px - 1024px) */
@media (max-width: 1024px) {
  .page-content {
    padding: 1.5rem;
  }

  .page-title-section {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .view-controls {
    flex-direction: column;
    gap: 1rem;
    width: 100%;
  }

  .view-tabs {
    width: 100%;
    justify-content: space-between;
  }

  .documents-table {
    font-size: 14px;
  }

  .documents-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }

  .document-card {
    padding: 1.5rem;
  }

  .action-btn {
    padding: 0.4rem 0.8rem;
    font-size: 12px;
  }
}

/* Mobiles (max-width: 768px) */
@media (max-width: 768px) {
  .page-content {
    padding: 1rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .page-title-section {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .view-controls {
    flex-direction: column;
    gap: 1rem;
  }

  .view-tabs {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .view-tab {
    flex: 1;
    min-width: 100px;
    padding: 0.5rem 0.75rem;
    font-size: 13px;
  }

  .search-filter {
    width: 100%;
  }

  /* Table view */
  .documents-table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .documents-table {
    min-width: 600px;
    font-size: 13px;
  }

  .document-row td {
    padding: 0.75rem 0.5rem;
  }

  .document-name-cell {
    min-width: 200px;
  }

  .document-actions {
    flex-direction: column;
    gap: 0.25rem;
  }

  .action-btn {
    width: 100%;
    padding: 0.4rem 0.6rem;
    font-size: 11px;
  }

  /* Grid view */
  .documents-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .document-card {
    padding: 1rem;
  }

  .card-title {
    font-size: 1rem;
  }

  .card-description {
    font-size: 0.875rem;
  }

  .card-actions {
    flex-direction: column;
    gap: 0.5rem;
  }

  .card-actions .action-btn {
    width: 100%;
  }

  /* List view */
  .document-list-item {
    padding: 1rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .list-item-content {
    width: 100%;
  }

  .list-users {
    align-self: flex-end;
  }

  .list-actions {
    width: 100%;
    justify-content: space-between;
  }

  .list-actions .action-btn {
    flex: 1;
  }

  /* Tasks section */
  .tasks-section {
    padding: 12px;
    margin-top: 12px;
  }

  .task-item {
    padding: 10px 12px;
  }

  .task-actions {
    flex-direction: column;
    gap: 6px;
    margin-left: 8px;
  }

  .task-status-select {
    font-size: 10px;
    padding: 4px 6px;
  }

  .task-delete-btn {
    width: 20px;
    height: 20px;
    font-size: 12px;
  }

  .tasks-view-container {
    padding: 1rem;
  }

  .tasks-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .task-header-main {
    flex-direction: column;
    align-items: flex-start;
  }

  .task-footer-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .task-info-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}

/* Petits mobiles (max-width: 480px) */
@media (max-width: 480px) {
  .page-content {
    padding: 0.75rem;
  }

  .page-title {
    font-size: 1.25rem;
  }

  .view-tab {
    font-size: 12px;
    padding: 0.4rem 0.6rem;
  }

  .documents-table {
    font-size: 12px;
    min-width: 500px;
  }

  .document-row td {
    padding: 0.5rem 0.25rem;
  }

  .document-name {
    font-size: 13px;
  }

  .document-description {
    font-size: 11px;
  }

  .action-btn {
    padding: 0.3rem 0.5rem;
    font-size: 10px;
  }

  .document-card {
    padding: 0.75rem;
  }

  .card-title {
    font-size: 0.875rem;
  }

  .card-description {
    font-size: 0.75rem;
  }

  .document-list-item {
    padding: 0.75rem;
  }

  .list-title {
    font-size: 0.875rem;
  }

  .list-meta {
    font-size: 11px;
  }

  .tasks-view-container {
    padding: 0.75rem;
  }

  .task-title-main {
    font-size: 1rem;
  }

  .priority-badge-main,
  .status-badge-main {
    font-size: 0.625rem;
    padding: 0.25rem 0.5rem;
  }

  .task-date-main,
  .task-document-main {
    font-size: 0.75rem;
  }

  .action-btn-main {
    width: 1.75rem;
    height: 1.75rem;
  }

  .action-btn-main svg {
    width: 0.875rem;
    height: 0.875rem;
  }
}

/* Styles pour les tâches - Version améliorée */
.tasks-section {
  margin-top: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.tasks-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tasks-title::before {
  content: "📋";
  font-size: 16px;
}

.add-task-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border: none;
  border-radius: 8px;
  width: 28px;
  height: 28px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

.add-task-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
}

.add-task-btn:active {
  transform: translateY(0);
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.2s ease;
  position: relative;
}

.task-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.task-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
  word-wrap: break-word;
  transition: color 0.2s ease;
  min-width: 150px;
}

.task-title.completed {
  text-decoration: line-through;
  color: #94a3b8;
  opacity: 0.7;
}

.task-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.priority-badge,
.status-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 20px;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

/* Priorité colors */
.priority-badge {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #475569;
  border: 1px solid #cbd5e1;
}

.priority-badge:nth-child(1) {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  color: #64748b;
  border-color: #e2e8f0;
}

.priority-badge:nth-child(2) {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  border-color: #93c5fd;
}

.priority-badge:nth-child(3) {
  background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%);
  color: #c2410c;
  border-color: #fb923c;
}

.priority-badge:nth-child(4) {
  background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
  color: #b91c1c;
  border-color: #f87171;
}

/* Status colors */
.status-badge {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #475569;
  border: 1px solid #cbd5e1;
}

.status-badge:nth-child(2) {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  border-color: #fbbf24;
}

.status-badge:nth-child(3) {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #059669;
  border-color: #34d399;
}

.status-badge:nth-child(4) {
  background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
  color: #b91c1c;
  border-color: #f87171;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-status-select {
  font-size: 11px;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.task-status-select:hover {
  border-color: #94a3b8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.task-status-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.task-delete-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 6px;
  width: 24px;
  height: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
}

.task-delete-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

.task-delete-btn:active {
  transform: scale(0.95);
}

.no-tasks-message {
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
  padding: 12px;
  font-style: italic;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 6px;
  border: 1px dashed #e2e8f0;
}

/* Animations supplémentaires */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.task-item {
  animation: slideIn 0.3s ease;
}

/* Styles pour la vue tâches séparée */
.tasks-view-container {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 16px;
  padding: 2rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e2e8f0;
}

.tasks-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.add-task-btn-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.add-task-btn-main:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
}

.add-task-btn-main svg {
  width: 1.25rem;
  height: 1.25rem;
}

.all-tasks-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-item-main {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.task-item-main::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  opacity: 0.8;
}

.task-item-main:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
  border-color: #cbd5e1;
}

.task-content-main {
  margin-left: 1rem;
}

.task-header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.task-title-main {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  line-height: 1.4;
  flex: 1;
}

.task-badges-main {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.priority-badge-main,
.status-badge-main {
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.priority-badge-main.low {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
  border: 1px solid #34d399;
}

.priority-badge-main.medium {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  border: 1px solid #fbbf24;
}

.priority-badge-main.high {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: #b91c1c;
  border: 1px solid #f87171;
}

.status-badge-main.pending {
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  color: #374151;
  border: 1px solid #d1d5db;
}

.status-badge-main.in-progress {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1d4ed8;
  border: 1px solid #93c5fd;
}

.status-badge-main.completed {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
  border: 1px solid #34d399;
}

.status-badge-main.cancelled {
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  color: #6b7280;
  border: 1px solid #9ca3af;
}

.task-description-main {
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
}

.task-footer-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.task-info-main {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.task-document-main,
.task-date-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.task-document-main svg,
.task-date-main svg {
  width: 1rem;
  height: 1rem;
  color: #9ca3af;
}

.task-actions-main {
  display: flex;
  gap: 0.5rem;
}

.action-btn-main {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn-main svg {
  width: 1.125rem;
  height: 1.125rem;
}

.action-btn-main.edit {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.action-btn-main.edit:hover {
  background: #e5e7eb;
  color: #374151;
  border-color: #d1d5db;
}

.action-btn-main.delete {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.action-btn-main.delete:hover {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fecaca;
}

/* Responsive design */
/* Tablettes (768px - 1024px) */
@media (max-width: 1024px) {
  .page-content {
    padding: 1.5rem;
  }

  .page-title-section {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .view-controls {
    flex-direction: column;
    gap: 1rem;
    width: 100%;
  }

  .view-tabs {
    width: 100%;
    justify-content: space-between;
  }

  .documents-table {
    font-size: 14px;
  }

  .documents-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }

  .document-card {
    padding: 1.5rem;
  }

  .action-btn {
    padding: 0.4rem 0.8rem;
    font-size: 12px;
  }
}

/* Mobiles (max-width: 768px) */
@media (max-width: 768px) {
  .page-content {
    padding: 1rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .page-title-section {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .view-controls {
    flex-direction: column;
    gap: 1rem;
  }

  .view-tabs {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .view-tab {
    flex: 1;
    min-width: 100px;
    padding: 0.5rem 0.75rem;
    font-size: 13px;
  }

  .search-filter {
    width: 100%;
  }

  /* Table view */
  .documents-table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .documents-table {
    min-width: 600px;
    font-size: 13px;
  }

  .document-row td {
    padding: 0.75rem 0.5rem;
  }

  .document-name-cell {
    min-width: 200px;
  }

  .document-actions {
    flex-direction: column;
    gap: 0.25rem;
  }

  .action-btn {
    width: 100%;
    padding: 0.4rem 0.6rem;
    font-size: 11px;
  }

  /* Grid view */
  .documents-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .document-card {
    padding: 1rem;
  }

  .card-title {
    font-size: 1rem;
  }

  .card-description {
    font-size: 0.875rem;
  }

  .card-actions {
    flex-direction: column;
    gap: 0.5rem;
  }

  .card-actions .action-btn {
    width: 100%;
  }

  /* List view */
  .document-list-item {
    padding: 1rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .list-item-content {
    width: 100%;
  }

  .list-users {
    align-self: flex-end;
  }

  .list-actions {
    width: 100%;
    justify-content: space-between;
  }

  .list-actions .action-btn {
    flex: 1;
  }

  /* Tasks section */
  .tasks-section {
    padding: 12px;
    margin-top: 12px;
  }

  .task-item {
    padding: 10px 12px;
  }

  .task-actions {
    flex-direction: column;
    gap: 6px;
    margin-left: 8px;
  }

  .task-status-select {
    font-size: 10px;
    padding: 4px 6px;
  }

  .task-delete-btn {
    width: 20px;
    height: 20px;
    font-size: 12px;
  }

  .tasks-view-container {
    padding: 1rem;
  }

  .tasks-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .task-header-main {
    flex-direction: column;
    align-items: flex-start;
  }

  .task-footer-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .task-info-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}

/* Petits mobiles (max-width: 480px) */
@media (max-width: 480px) {
  .page-content {
    padding: 0.75rem;
  }

  .page-title {
    font-size: 1.25rem;
  }

  .view-tab {
    font-size: 12px;
    padding: 0.4rem 0.6rem;
  }

  .documents-table {
    font-size: 12px;
    min-width: 500px;
  }

  .document-row td {
    padding: 0.5rem 0.25rem;
  }

  .document-name {
    font-size: 13px;
  }

  .document-description {
    font-size: 11px;
  }

  .action-btn {
    padding: 0.3rem 0.5rem;
    font-size: 10px;
  }

  .document-card {
    padding: 0.75rem;
  }

  .card-title {
    font-size: 0.875rem;
  }

  .card-description {
    font-size: 0.75rem;
  }

  .document-list-item {
    padding: 0.75rem;
  }

  .list-title {
    font-size: 0.875rem;
  }

  .list-meta {
    font-size: 11px;
  }

  .tasks-view-container {
    padding: 0.75rem;
  }

  .task-title-main {
    font-size: 1rem;
  }

  .priority-badge-main,
  .status-badge-main {
    font-size: 0.625rem;
    padding: 0.25rem 0.5rem;
  }

  .task-date-main,
  .task-document-main {
    font-size: 0.75rem;
  }

  .action-btn-main {
    width: 1.75rem;
    height: 1.75rem;
  }

  .action-btn-main svg {
    width: 0.875rem;
    height: 0.875rem;
  }
}
</style>