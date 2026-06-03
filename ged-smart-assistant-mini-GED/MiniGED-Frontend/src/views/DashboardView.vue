<template>
  <div class="dashboard-container">
    <!-- Sidebar -->
    <div class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <img
            src="../assets/images/logo1.png"
            alt="MINIGED Logo"
            class="logo-icon"
          />
          <span class="logo-text" v-show="!sidebarCollapsed"
            >Mini<span class="logo-text-highlight">GED</span></span
          >
        </div>
      </div>

      <nav class="sidebar-nav">
        <ul class="nav-list">
          <li
            class="nav-item"
            :class="{ active: $route.path === '' }"
            @click="navigateToHome"
          >
            <span class="nav-icon">
              <i class="fas fa-house"></i>
            </span>
            <span class="nav-text" v-show="!sidebarCollapsed">Accueil</span>
          </li>
          <li
            class="nav-item"
            :class="{ active: $route.path === '/documents' }"
            @click="navigateToDocuments"
          >
            <span class="nav-icon">
              <i class="fas fa-folder-open"></i>
            </span>
            <span class="nav-text" v-show="!sidebarCollapsed"
              >Mes documents</span
            >
            <span class="nav-badge" v-show="!sidebarCollapsed">{{
              documents.length
            }}</span>
          </li>
          <li
            class="nav-item"
            :class="{ active: $route.path === '/recruitment' }"
            @click="router.push('/recruitment')"
          >
            <span class="nav-icon"><i class="fas fa-briefcase"></i></span>
            <span class="nav-text" v-show="!sidebarCollapsed">Recrutement</span>
          </li>
          
          <li
            class="nav-item"
            :class="{ active: $route.path === '/users' }"
            @click="navigateToUsers"
          >
            <span class="nav-icon">
              <i class="fas fa-users"></i>
            </span>
            <span class="nav-text" v-show="!sidebarCollapsed"
              >Utilisateurs</span
            >
          </li>
        </ul>
      </nav>

      <div class="sidebar-footer">
        <div class="user-profile">
          <div class="user-avatar">
            {{ "U" }}
          </div>
          <div class="user-info" v-show="!sidebarCollapsed">
            <div class="user-name">
              {{ CurrentUser?.fullName || "Utilisateur" }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <header class="content-header">
        <div class="flex">
          <button class="sidebar-toggle" @click="toggleSidebar">
            <span v-if="sidebarCollapsed"
              ><i class="fas fa-angles-right"></i>
            </span>
            <span v-else><i class="fas fa-angles-left"></i> </span>
          </button>
          <!-- <nav class="breadcrumb">
            <span class="breadcrumb-item">Tableau de bord</span>
            <span class="breadcrumb-item">Documents</span>
          </nav> -->
        </div>
        <div class="header-actions">
          <div class="relative flex items-center">
            <div
              class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"
            >
              <i class="fas fa-magnifying-glass text-slate-400"></i>
            </div>
            <input
              type="text"
              placeholder="Recherche..."
              @click="openSearchModal"
              class="w-64 py-2.5 pl-10 pr-4 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm text-slate-700 placeholder:text-slate-400 transition"
            />
          </div>
          <SearchModal v-if="isSearchOpen" @close="isSearchOpen = false" />
          <button class="settings-btn">
            <i class="fas fa-sliders"></i>
          </button>
          <button class="notifications-btn" @click="toggleAssistant">
            <SparkleIcon class="text-slate-700" />
          </button>
          <button class="assistant-launch-btn" @click="openAssistantStandalone">
            <i class="fa-solid fa-arrow-up-right-from-square"></i>
          </button>

          <DropdownComponent
            button-text="Custom Button"
            :items="customItems"
            @item-clicked="handleItemClick"
          />
        </div>
      </header>

      <router-view />
    </div>
    <div
      v-if="isAssistantEnabled"
      class="assistant-panel"
    >
      <iframe
        ref="assistantFrame"
        :src="ASSISTANT_URL"
        data-assistant
        allow="microphone"
        class="w-full h-screen border-none rounded-lg shadow-lg bg-white"
        title="GED Smart Assistant"
        @load="handleAssistantFrameLoad"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, toRaw } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { getUserDocuments } from "../services/documentService";
import { getTasks } from "../services/taskService";
import SearchModal from "../components/SearchFeature/SearchModal.vue";
import DropdownComponent from "../components/DropdownComponent.vue";
import SparkleIcon from "../components/icons/SparkleIcon.vue";
import { ASSISTANT_ORIGIN, ASSISTANT_SOURCE_SYSTEM, ASSISTANT_URL } from "../config/assistant";

const authStore = useAuthStore();

const handleLogout = () => {
  authStore.logout();
  window.location.href = "/login";
};
const customItems = [
  { text: "Profile", href: "#", action: "profile" },
  { text: "Messages", href: "#", action: "messages" },
  { text: "Logout", href: "#", action: "logout" },
];

const handleItemClick = (action) => {
  if (action.action == "logout") {
    handleLogout();
  } else if (action.action === "profile") {
    router.push("/profile");
  } else if (action.action === "messages") {
    // TODO: Implémenter la messagerie
  }
};
const router = useRouter();
const sidebarCollapsed = ref(false);
const isSearchOpen = ref(false);
const isAssistantEnabled = ref(false);
const assistantFrame = ref(null);
const assistantWindow = ref(null);

const currentDocId   = ref('')
const currentDocType = ref('')
const currentFilename = ref('')

// Computed URL avec contexte
const assistantUrl = computed(() => {
  const base = ASSISTANT_URL
  if (!currentDocId.value) return base
  const params = new URLSearchParams({
    doc_id:   currentDocId.value,
    doc_type: currentDocType.value,
    filename: currentFilename.value,
  })
  return `${base}?${params.toString()}`
})
const CurrentUser = computed(() => authStore.user);
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
};

const openSearchModal = () => {
  isSearchOpen.value = true;

  event.target.blur();
};

const navigateToDocuments = () => {
  router.push("/documents");
};
const navigateToUsers = () => {
  router.push("/users");
};
const navigateToHome = () => {
  router.push("/");
};

const toggleAssistant = () => {
  isAssistantEnabled.value = !isAssistantEnabled.value;
};

const getSerializableUser = () => {
  const storeUser = authStore.user ? toRaw(authStore.user) : null;
  const fallbackUser = JSON.parse(localStorage.getItem("user") || "null");
  const user = storeUser || fallbackUser;

  if (!user) {
    return null;
  }

  return JSON.parse(JSON.stringify(user));
};

const getAssistantBootstrapPayload = () => ({
  accessToken: localStorage.getItem("token"),
  refreshToken: localStorage.getItem("refreshToken"),
  user: getSerializableUser(),
  sourceSystem: ASSISTANT_SOURCE_SYSTEM,
});

const postBootstrapPayload = (targetWindow) => {
  if (!targetWindow) {
    return;
  }

  targetWindow.postMessage(
    {
      type: "assistant:bootstrap",
      payload: getAssistantBootstrapPayload(),
    },
    ASSISTANT_ORIGIN
  );
};

const handleAssistantFrameLoad = () => {
  postBootstrapPayload(assistantFrame.value?.contentWindow);
};

const openAssistantStandalone = () => {
  assistantWindow.value = window.open(
    ASSISTANT_URL,
    "ged-smart-assistant",
    "width=1280,height=900,resizable=yes,scrollbars=yes"
  );

  assistantWindow.value?.focus();
};

const handleAssistantMessage = (event) => {
  // ── Relay DOC_CONTEXT : accepter depuis la même app (MiniGED)
  if (event.data?.type === 'DOC_CONTEXT') {
    const ctx = event.data.payload || {}
    currentDocId.value    = ctx.documentId   || ''
    currentDocType.value  = ctx.documentType || ''
    currentFilename.value = ctx.filename     || ''

    // Relayer à l'iframe assistant (localhost:5173)
    if (assistantFrame.value?.contentWindow) {
      assistantFrame.value.contentWindow.postMessage(
        { type: 'DOC_CONTEXT', payload: ctx },
        ASSISTANT_ORIGIN   // 'http://localhost:5173'
      )
      console.log('[DashboardView] DOC_CONTEXT relayé à l\'iframe:', ctx)
    }

    // Relayer aussi à la fenêtre standalone si ouverte
    if (assistantWindow.value && !assistantWindow.value.closed) {
      try {
        assistantWindow.value.postMessage(
          { type: 'DOC_CONTEXT', payload: ctx },
          ASSISTANT_ORIGIN
        )
      } catch { /* fenêtre fermée */ }
    }
    return
  }
  if (event.data?.type === 'NAVIGATE_DOCUMENT') {
    const { documentId } = event.data.payload || {}
    if (documentId) {
      router.push(`/document/${documentId}`)
    }
    return
  }

  // ── Bootstrap depuis l'iframe assistant
  if (event.origin !== ASSISTANT_ORIGIN) return
  if (event.data?.type !== 'assistant:ready') return
  postBootstrapPayload(event.source)
}

const documents = ref([]);
const tasks = ref([]);
const loading = ref(false);
const error = ref(null);

onMounted(async () => {
  window.addEventListener("message", handleAssistantMessage);

  loading.value = true;
  try {
    const [documentsResponse, tasksResponse] = await Promise.all([
      getUserDocuments(),
      getTasks(),
    ]);
    documents.value = documentsResponse;
    tasks.value = tasksResponse;
  } catch (err) {
    error.value = "Erreur lors du chargement des données";
    console.error(err);
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  window.removeEventListener("message", handleAssistantMessage);
});
</script>

<style scoped>
.dashboard-container {
  display: flex;
  height: 100vh;
  background-color: #f8fafc;
}

/* Sidebar Styles */
.sidebar {
  width: 280px;
  background-color: white;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: relative;
  border-right: 1px solid #e2e8f0;
}

.sidebar.collapsed {
  width: 80px;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    z-index: 1000;
    transform: translateX(0);
  }

  .sidebar.collapsed {
    transform: translateX(-100%);
    width: 280px;
  }
}

.sidebar-header {
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  height: 90px;
  justify-content: start;
  padding: 1rem 1.25rem;
  align-items: center;
}

.sidebar-toggle {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 15px;
  cursor: pointer;
  padding: 0.55rem 0.7rem;
  border-radius: 8px;
  transition: all 0.2s;
}

.sidebar-toggle:hover {
  background-color: #f1f5f9;
  color: #1e293b;
}

.sidebar.collapsed .sidebar-toggle {
  margin-left: auto;
  margin-right: auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.logo-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  object-fit: contain;
}

.logo-text {
  font-weight: 800;
  font-size: 19px;
  color: #0f172a;
  font-family: "Inter", sans-serif;
}

.logo-text-highlight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-family: "Inter", sans-serif;
  color: #667eea;
  /* Fallback color */
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  background-color: white;
}

.sidebar-nav {
  flex: 1;
  padding: 1rem 0.75rem;
}

.nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.8rem 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  border-radius: 8px;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.nav-item:hover {
  background-color: #f8fafc;
  color: #1e293b;
}

.nav-item.active {
  background-color: #eff6ff;
  color: #2563eb;
  box-shadow: inset 3px 0 0 #3b82f6;
}

.sidebar.collapsed .nav-item {
  padding: 0.75rem;
  justify-content: center;
}

.sidebar.collapsed .nav-icon {
  margin-right: 0;
}

.nav-icon {
  margin-right: 0.75rem;
  font-size: 16px;
  width: 1.25rem;
  display: flex;
  justify-content: center;
}

.nav-text {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: inherit;
}

.nav-badge {
  background-color: #dbeafe;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  min-width: 20px;
  text-align: center;
}

.sidebar-footer {
  padding: 1rem 1.25rem;
  border-top: 1px solid #e2e8f0;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgb(255, 255, 255);
  font-weight: bold;
  font-family: "Inter", "Segoe UI", system-ui, sans-serif;
  font-size: large;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.user-role {
  font-size: 12px;
  color: #718096;
}

/* Main Content Styles */
.main-content {
  flex: 7;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: margin-left 0.3s ease;
}

@media (max-width: 768px) {
  .main-content {
    margin-left: 0;
  }

  .dashboard-container:not(.sidebar-collapsed) .main-content {
    margin-left: 0;
  }
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1.5rem;
  background-color: white;
  border-bottom: 1px solid #e2e8f0;
  height: 90px;
}

@media (max-width: 768px) {
  .content-header {
    padding: 1rem;
    flex-direction: column;
    gap: 1rem;
  }

  .breadcrumb {
    font-size: 12px;
  }
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.search-container {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 256px;
  padding: 0.5rem 1rem 0.5rem 2.5rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  background-color: white;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.settings-btn,
.notifications-btn,
.assistant-launch-btn,
.user-menu {
  width: 40px;
  height: 40px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #475569;
  transition: all 0.2s;
}

.settings-btn:hover,
.notifications-btn:hover,
.assistant-launch-btn:hover,
.user-menu:hover {
  background-color: #f1f5f9;
  border-color: #cbd5e1;
  color: #1e293b;
}

.assistant-panel {
  width: min(38vw, 560px);
  border-left: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
  box-shadow: -12px 0 24px rgba(15, 23, 42, 0.08);
}

.page-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .page-content {
    padding: 1rem;
  }
}

.page-title-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

@media (max-width: 768px) {
  .page-title-section {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .page-title {
    font-size: 1.5rem;
  }
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

@media (max-width: 768px) {
  .view-controls {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .view-tabs {
    justify-content: center;
  }

  .filter-search {
    width: 100%;
  }
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

.filter-search {
  padding: 0.5rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  width: 200px;
}

.documents-table-container {
  background-color: white;
  border-radius: 12px;
  border: 1px solid #e9ecef;
  overflow: hidden;
}

@media (max-width: 768px) {
  .documents-table-container {
    overflow-x: auto;
  }

  .documents-table {
    min-width: 600px;
  }

  .documents-table th,
  .documents-table td {
    padding: 0.5rem;
    font-size: 12px;
  }
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

.document-size {
  color: #718096;
  font-size: 14px;
}

.user-avatars {
  display: flex;
  align-items: center;
  gap: -0.25rem;
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
  margin-left: -0.25rem;
}

.user-avatar-small:first-child {
  margin-left: 0;
}

.extra-users {
  width: 32px;
  height: 32px;
  background-color: #e2e8f0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #718096;
  font-size: 11px;
  font-weight: bold;
  border: 2px solid white;
  margin-left: -0.25rem;
}

.document-date {
  color: #718096;
  font-size: 14px;
}

.document-actions {
  display: flex;
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

.sort-icon {
  margin-left: 0.5rem;
  color: #cbd5e0;
}

.select-all,
.row-select {
  margin-right: 0.5rem;
}

/* Grid View Styles */
.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

@media (max-width: 768px) {
  .documents-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
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

.card-select {
  margin: 0;
}

.card-menu {
  color: #cbd5e0;
  cursor: pointer;
  padding: 0.25rem;
}

.card-menu:hover {
  color: #718096;
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

.card-size {
  color: #718096;
  font-size: 14px;
  margin: 0 0 0.75rem 0;
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

/* List View Styles */
.documents-list {
  background-color: white;
  border-radius: 12px;
  border: 1px solid #e9ecef;
  overflow: hidden;
}

@media (max-width: 768px) {
  .document-list-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .list-item-content {
    width: 100%;
  }

  .list-users {
    margin-right: 0;
    width: 100%;
  }

  .list-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

.document-list-item {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #f1f3f4;
  transition: background-color 0.2s;
}

.document-list-item:hover {
  background-color: #f8f9fa;
}

.document-list-item:last-child {
  border-bottom: none;
}

.list-item-content {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 1rem;
}

.list-select {
  margin: 0;
}

.list-icon {
  font-size: 24px;
}

.list-details {
  flex: 1;
}

.list-title {
  font-size: 16px;
  font-weight: 500;
  color: #2d3748;
  margin: 0 0 0.25rem 0;
}

.list-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 13px;
  color: #718096;
}

.list-separator {
  color: #cbd5e0;
}

.list-users {
  margin-right: 2rem;
}

.list-actions {
  display: flex;
  gap: 0.5rem;
}
</style>
