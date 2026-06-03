<template>
  <div class="tasks-container">
    <div class="tasks-header">
      <h1>Gestion des Tâches</h1>
      <div class="header-actions">
        <div class="search-bar">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Rechercher des tâches..." 
            class="search-input"
            @input="filterTasks"
          />
          <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
        </div>
        <button class="add-task-btn" @click="openAddTaskModal">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Nouvelle tâche
        </button>
      </div>
    </div>

    <!-- Filtres et statistiques -->
    <div class="tasks-filters">
      <div class="filter-tabs">
        <button 
          v-for="filter in filters" 
          :key="filter.key"
          :class="['filter-tab', { active: activeFilter === filter.key }]"
          @click="setActiveFilter(filter.key)"
        >
          {{ filter.label }}
          <span class="filter-count">{{ getTaskCount(filter.key) }}</span>
        </button>
      </div>
      
      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-number">{{ totalTasks }}</div>
          <div class="stat-label">Total</div>
        </div>
        <div class="stat-card pending">
          <div class="stat-number">{{ pendingTasks }}</div>
          <div class="stat-label">En attente</div>
        </div>
        <div class="stat-card in-progress">
          <div class="stat-number">{{ inProgressTasks }}</div>
          <div class="stat-label">En cours</div>
        </div>
        <div class="stat-card completed">
          <div class="stat-number">{{ completedTasks }}</div>
          <div class="stat-label">Terminées</div>
        </div>
      </div>
    </div>

    <!-- Liste des tâches -->
    <div class="tasks-content">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Chargement des tâches...</p>
      </div>

      <div v-else-if="filteredTasks.length === 0" class="empty-state">
        <svg class="empty-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.669 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
        </svg>
        <h3>Aucune tâche trouvée</h3>
        <p>{{ activeFilter === 'all' ? 'Commencez par créer votre première tâche' : 'Aucune tâche ne correspond à ce filtre' }}</p>
      </div>

      <div v-else class="tasks-list">
        <div 
          v-for="task in filteredTasks" 
          :key="task.id" 
          class="task-item"
          :class="[`priority-${task.priority}`, { completed: task.status === 'Completed' }]"
        >
          <div class="task-checkbox">
            <input 
              type="checkbox" 
              :checked="task.status === 'Completed'"
              @change="toggleTaskStatus(task)"
            />
          </div>
          
          <div class="task-content">
            <div class="task-header">
              <h3 class="task-title">{{ task.title }}</h3>
              <div class="task-meta">
                <span :class="['status-badge', task.status.toLowerCase().replace(' ', '-')]">
                  {{ getStatusText(task.status) }}
                </span>
                <span :class="['priority-badge', task.priority.toLowerCase()]">
                  {{ getPriorityText(task.priority) }}
                </span>
              </div>
            </div>
            
            <p class="task-description">{{ task.description || 'Aucune description' }}</p>
            
            <div class="task-footer">
              <div class="task-info">
                <div class="task-document" v-if="task.document">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                  </svg>
                  {{ task.document.title }}

                  <CandidateStatusBadge
                    v-if="task.document.candidateStatus"
                    :status="task.document.candidateStatus"
                    compact
                  />

                </div>
                <div class="task-date">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0h18M12 12.75h.008v.008H12v-.008Z" />
                  </svg>
                  {{ formatDate(task.createdAt) }}
                </div>
              </div>
              
              <div class="task-actions">
                <button class="action-btn edit" @click="editTask(task)">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                  </svg>
                </button>
                <button class="action-btn delete" @click="confirmDeleteTask(task)">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal pour ajouter/éditer une tâche -->
    <TaskModal 
      v-if="showTaskModal" 
      :task="selectedTask"
      :documents="documents"
      @close="closeTaskModal"
      @saved="handleTaskSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import TaskModal from '../components/TaskModal.vue';
import { getTasks, createTask, updateTask, deleteTask, updateTaskStatus } from '../services/taskService';
import { getUserDocuments } from '../services/documentService';

const router = useRouter();

const tasks = ref([]);
const documents = ref([]);
const loading = ref(false);
const searchQuery = ref('');
const activeFilter = ref('all');
const showTaskModal = ref(false);
const selectedTask = ref(null);

const filters = [
  { key: 'all', label: 'Toutes' },
  { key: 'pending', label: 'En attente' },
  { key: 'in-progress', label: 'En cours' },
  { key: 'completed', label: 'Terminées' }
];

// Statistiques calculées
const totalTasks = computed(() => tasks.value.length);
const pendingTasks = computed(() => tasks.value.filter(t => t.status === 'Pending').length);
const inProgressTasks = computed(() => tasks.value.filter(t => t.status === 'InProgress').length);
const completedTasks = computed(() => tasks.value.filter(t => t.status === 'Completed').length);

// Tâches filtrées
const filteredTasks = computed(() => {
  let filtered = tasks.value;
  
  // Filtrer par statut
  if (activeFilter.value !== 'all') {
    filtered = filtered.filter(task => {
      if (activeFilter.value === 'pending') return task.status === 'Pending';
      if (activeFilter.value === 'in-progress') return task.status === 'InProgress';
      if (activeFilter.value === 'completed') return task.status === 'Completed';
      return true;
    });
  }
  
  // Filtrer par recherche
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(task => 
      task.title.toLowerCase().includes(query) ||
      (task.description && task.description.toLowerCase().includes(query))
    );
  }
  
  return filtered.sort((a, b) => {
    // Trier par priorité puis par date
    const priorityOrder = { 'High': 0, 'Medium': 1, 'Low': 2 };
    const aPriority = priorityOrder[a.priority] || 999;
    const bPriority = priorityOrder[b.priority] || 999;
    
    if (aPriority !== bPriority) {
      return aPriority - bPriority;
    }
    
    return new Date(b.createdAt) - new Date(a.createdAt);
  });
});

const getTaskCount = (filterKey) => {
  if (filterKey === 'all') return totalTasks.value;
  if (filterKey === 'pending') return pendingTasks.value;
  if (filterKey === 'in-progress') return inProgressTasks.value;
  if (filterKey === 'completed') return completedTasks.value;
  return 0;
};

const setActiveFilter = (filter) => {
  activeFilter.value = filter;
};

const filterTasks = () => {
  // La réactivité gère le filtrage automatiquement
};

const openAddTaskModal = () => {
  selectedTask.value = null;
  showTaskModal.value = true;
};

const editTask = (task) => {
  selectedTask.value = { ...task };
  showTaskModal.value = true;
};

const closeTaskModal = () => {
  showTaskModal.value = false;
  selectedTask.value = null;
};

const handleTaskSaved = async (taskData) => {
  try {
    if (selectedTask.value) {
      // Mise à jour
      const updatedTask = await updateTask(selectedTask.value.id, taskData);
      const index = tasks.value.findIndex(t => t.id === selectedTask.value.id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
    } else {
      // Création
      const newTask = await createTask(taskData);
      tasks.value.unshift(newTask);
    }
    closeTaskModal();
  } catch (error) {
    console.error('Erreur lors de la sauvegarde de la tâche:', error);
    alert('Erreur lors de la sauvegarde de la tâche');
  }
};

const toggleTaskStatus = async (task) => {
  try {
    const newStatus = task.status === 'Completed' ? 'Pending' : 'Completed';
    await updateTaskStatus(task.id, newStatus);
    task.status = newStatus;
  } catch (error) {
    console.error('Erreur lors de la mise à jour du statut:', error);
    alert('Erreur lors de la mise à jour du statut');
  }
};

const confirmDeleteTask = (task) => {
  if (confirm(`Êtes-vous sûr de vouloir supprimer la tâche "${task.title}"?`)) {
    deleteTaskItem(task);
  }
};

const deleteTaskItem = async (task) => {
  try {
    await deleteTask(task.id);
    tasks.value = tasks.value.filter(t => t.id !== task.id);
  } catch (error) {
    console.error('Erreur lors de la suppression de la tâche:', error);
    alert('Erreur lors de la suppression de la tâche');
  }
};

const getStatusText = (status) => {
  const statusMap = {
    'Pending': 'En attente',
    'InProgress': 'En cours',
    'Completed': 'Terminée'
  };
  return statusMap[status] || status;
};

const getPriorityText = (priority) => {
  const priorityMap = {
    'High': 'Haute',
    'Medium': 'Moyenne',
    'Low': 'Basse'
  };
  return priorityMap[priority] || priority;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('fr-FR', { 
    day: 'numeric', 
    month: 'short', 
    year: 'numeric' 
  });
};

const loadData = async () => {
  loading.value = true;
  try {
    const [tasksData, documentsData] = await Promise.all([
      getTasks(),
      getUserDocuments()
    ]);
    tasks.value = tasksData;
    documents.value = documentsData;
  } catch (error) {
    console.error('Erreur lors du chargement des données:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.tasks-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  gap: 1rem;
}

.tasks-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.search-bar {
  position: relative;
  width: 300px;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.25rem;
  height: 1.25rem;
  color: #6b7280;
}

.add-task-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.add-task-btn:hover {
  background: #2563eb;
}

.add-task-btn svg {
  width: 1.25rem;
  height: 1.25rem;
}

.tasks-filters {
  margin-bottom: 2rem;
}

.filter-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.filter-tab:hover {
  color: #374151;
}

.filter-tab.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}

.filter-count {
  background: #f3f4f6;
  color: #374151;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.filter-tab.active .filter-count {
  background: #dbeafe;
  color: #1d4ed8;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.stat-card.pending .stat-number {
  color: #f59e0b;
}

.stat-card.in-progress .stat-number {
  color: #3b82f6;
}

.stat-card.completed .stat-number {
  color: #10b981;
}

.tasks-content {
  min-height: 400px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: #6b7280;
}

.spinner {
  width: 2rem;
  height: 2rem;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  text-align: center;
  color: #6b7280;
}

.empty-icon {
  width: 4rem;
  height: 4rem;
  margin-bottom: 1rem;
  color: #d1d5db;
}

.empty-state h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
  display: flex;
  gap: 1rem;
}

.task-item:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.task-item.completed {
  opacity: 0.7;
  background: #f9fafb;
}

.task-item.priority-high {
  border-left: 4px solid #ef4444;
}

.task-item.priority-medium {
  border-left: 4px solid #f59e0b;
}

.task-item.priority-low {
  border-left: 4px solid #10b981;
}

.task-checkbox {
  display: flex;
  align-items: flex-start;
  padding-top: 0.25rem;
}

.task-checkbox input[type="checkbox"] {
  width: 1.25rem;
  height: 1.25rem;
  cursor: pointer;
}

.task-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.task-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
  line-height: 1.4;
}

.task-item.completed .task-title {
  text-decoration: line-through;
  color: #6b7280;
}

.task-meta {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.status-badge, .priority-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.pending {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.in-progress {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-badge.completed {
  background: #d1fae5;
  color: #065f46;
}

.priority-badge.high {
  background: #fee2e2;
  color: #991b1b;
}

.priority-badge.medium {
  background: #fef3c7;
  color: #92400e;
}

.priority-badge.low {
  background: #d1fae5;
  color: #065f46;
}

.task-description {
  color: #6b7280;
  line-height: 1.5;
  margin: 0;
}

.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.task-info {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.task-document, .task-date {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.task-document svg, .task-date svg {
  width: 1rem;
  height: 1rem;
}

.task-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.action-btn svg {
  width: 1rem;
  height: 1rem;
}

.action-btn.edit {
  background: #f3f4f6;
  color: #6b7280;
}

.action-btn.edit:hover {
  background: #e5e7eb;
  color: #374151;
}

.action-btn.delete {
  background: #fef2f2;
  color: #dc2626;
}

.action-btn.delete:hover {
  background: #fee2e2;
  color: #b91c1c;
}

@media (max-width: 768px) {
  .tasks-container {
    padding: 1rem;
  }
  
  .tasks-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }
  
  .header-actions {
    flex-direction: column;
    gap: 1rem;
  }
  
  .search-bar {
    width: 100%;
  }
  
  .filter-tabs {
    overflow-x: auto;
    white-space: nowrap;
  }
  
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .task-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .task-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
  
  .task-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
