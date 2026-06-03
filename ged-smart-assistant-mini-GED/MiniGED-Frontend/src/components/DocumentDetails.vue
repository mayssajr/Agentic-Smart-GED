<template>
  <div class="document-details-container">
    <header class="documents-header">
      <div class="breadcrumb">
        <span class="breadcrumb-link" @click="navigateToHome"></span>
        <span class="breadcrumb-link" @click="navigateToHome">Accueil</span>
        <span>></span>
        <span class="breadcrumb-link" @click="navigateToDocuments">Gestionnaire de documents</span>
        <span>></span>
        <span class="breadcrumb-link" @click="navigateToDocuments">Mes documents</span>
        <span>></span>
        <span class="breadcrumb-current">{{ document.title || "Document" }}</span>
      </div>
    </header>

    <div class="document-content">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        Chargement du document...
      </div>

      <div v-else-if="error" class="error">{{ error }}</div>

      <div v-else class="document-layout"
        :class="{
          'with-panel': selectedFile && showPreviewPanel,
          'without-panel': !selectedFile || !showPreviewPanel,
        }">

        <!-- Left Panel -->
        <div class="left-panel">
          <div class="search-section">
            <div class="search-input-container">
              <span class="search-icon"><i class="fas fa-magnifying-glass size-6"></i></span>
              <input type="text" placeholder="Rechercher des fichiers et des dossiers..."
                class="search-files-input" v-model="searchQuery" />
            </div>
          </div>

          <!-- nav-tabs -->
          <div class="nav-tabs">
            <button class="nav-tab" :class="{ active: activeTab === 'details' }" @click="activeTab = 'details'">Détails</button>
            <button class="nav-tab" :class="{ active: activeTab === 'files' }"   @click="activeTab = 'files'">
              Fichiers ({{ document.files ? document.files.length : "" }})
            </button>
            <button class="nav-tab" :class="{ active: activeTab === 'tasks' }"  @click="activeTab = 'tasks'">Tâches</button>
            <button class="nav-tab" :class="{ active: activeTab === 'trace' }"  @click="activeTab = 'trace'">
              <i class="fas fa-microchip" style="font-size:11px; margin-right:4px;"></i>Trace IA
              <span v-if="lastReactTrace.length" class="trace-count-badge">{{ lastReactTrace.length }}</span>
            </button>
          </div>

          <!-- Onglet Détails -->
          <div v-if="activeTab === 'details'" class="details-section">
            <div class="flex gap-2 flex-wrap">
              <button class="action-btn primary" @click="AddFiles">
                <span class="btn-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                  </svg>
                </span>
                Ajouter des fichiers
              </button>
              <button class="action-btn secondary">
                <span class="btn-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                  </svg>
                </span>
                Modifier le document
              </button>
              <button class="action-btn danger" @click="deleteDocument">
                <span class="btn-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                  </svg>
                </span>
                Supprimer le document
              </button>
            </div>

            <!-- Analyse IA -->
            <DocumentSummary v-if="document.id" :documentId="document.id" @analyzed="onAnalyzed" />

            <!--
              ScoreValidationBanner et CandidateStatusBadge ne s'affichent
              QU'APRÈS la fin de l'analyse IA (analysisComplete = true).
              Cela évite qu'ils apparaissent pendant que l'orchestrateur
              place le candidat en "ATraiter" au début du pipeline.
            -->
            <template v-if="analysisComplete">
              <!--
                ScoreValidationBanner expose ses boutons d'action RH intégrés.
                CandidateStatusBadge masque ses propres boutons tant que la
                bannière affiche une pendingAction (bannerActive = true),
                pour éviter la duplication des actions.
              -->
              <ScoreValidationBanner
                :key="scoreBannerKey"
                :documentId="document.id"
                @validated="onEmailValidated"
                @rejected="loadCandidate"
                @has-pending="bannerActive = $event"
              />
              
              <CandidateStatusBadge
                v-if="candidate"
                :status="candidate.status"
                :notes="candidate.notes"
                :show-actions="!bannerActive"
                :loading="statusLoading"
                @update-status="handleStatusUpdate"
                class="mt-3"
              />
            </template>
            <SignatureBanner
                v-if="document.id"
                :documentId="document.id"
                :documentType="aiDocumentType"
                @signed="onDocumentSigned"
              />

            <div class="detail-field">
              <label class="detail-label">Titre</label>
              <input type="text" :value="document.title" class="detail-input" readonly />
            </div>

            <div class="detail-field">
              <label class="detail-label">Description</label>
              <textarea :value="document.description || 'Aucune description'"
                class="detail-textarea" readonly rows="4"></textarea>
            </div>
          </div>

          <!-- Onglet Fichiers -->
          <div v-if="activeTab === 'files'" class="files-section">
            <button class="my-2 action-btn primary" @click="AddFiles">
              <span class="btn-icon"><i class="fas fa-plus size-6"></i></span>
              Ajouter des fichiers
            </button>
            <h3 class="mx-1 section-title">Fichiers ({{ filteredFiles.length }})</h3>
            <div v-if="filteredFiles.length === 0"
              class="flex flex-col items-center justify-center p-8 text-gray-500 text-center rounded-lg border border-dashed border-gray-300 bg-gray-50 mb-4">
              <i class="fas fa-file w-12 h-12 mb-3 text-gray-400"></i>
              <p class="font-medium">Aucun fichier trouvé.</p>
              <p class="text-sm mt-1">Ajoutez des fichiers ou modifiez votre recherche.</p>
            </div>
            <div class="files-list">
              <div v-for="file in filteredFiles" :key="file.id" class="file-item" @click="selectFile(file)">
                <div class="file-icon" v-html="getFileIcon(file.fileName)"></div>
                <div class="file-info">
                  <div class="file-name">{{ file.fileName }}</div>
                  <div class="file-meta">{{ getFileType(file.fileName) }} • {{ formatFileSize(file.fileSize) }}</div>
                </div>
                <div class="file-actions">
                  <button class="file-action-btn download-btn" @click.stop="downloadFile(file)" title="Télécharger">
                    <i class="fas fa-download w-4 h-4"></i>
                  </button>
                  <button class="file-action-btn delete-btn" @click.stop="deleteFile(file)" title="Supprimer">
                    <i class="fas fa-trash-can w-4 h-4"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Onglet Tâches -->
          <div v-if="activeTab === 'tasks'" class="flex flex-1 flex-col overflow-hidden">
            <TasksTab
              :tasks="documentTasks"
              @new-task="showTaskModal()"
              @status-change="handleTaskStatusChange"
              @edit="editTask"
              @delete="deleteTask"
            />
          </div>

          <!-- Onglet Trace IA -->
          <div v-if="activeTab === 'trace'" class="flex flex-1 flex-col overflow-hidden overflow-y-auto">
            <div v-if="!lastReactTrace.length" class="trace-fetch-hint">
              <div class="trace-hint-content">
                <div>
                  <p class="trace-hint-title">Trace non disponible en mémoire</p>
                  <p class="trace-hint-sub">La trace est générée lors de l'analyse. Relancez une analyse pour la voir.</p>
                </div>
                <button class="trace-reload-btn" @click="fetchTraceFromBackend" :disabled="traceLoading">
                  <i :class="traceLoading ? 'fas fa-spinner fa-spin' : 'fas fa-rotate-right'"></i>
                  {{ traceLoading ? 'Chargement...' : 'Charger la trace' }}
                </button>
              </div>
            </div>
            <AiTracePanel
              v-else
              :document-id="document.id"
              :react-trace="lastReactTrace"
            />
          </div>
        </div>

        <!-- Right Panel — aperçu fichier -->
        <div v-if="selectedFile && showPreviewPanel" class="right-panel" :class="{ closing: isClosing }">
          <div class="document-preview">
            <div class="preview-header">
              <div class="breadcrumb-path">
                <span>Documents Personnels</span><span>/</span>
                <span class="current-file">{{ selectedFile.fileName }}</span>
              </div>
              <button class="close-panel-btn" @click="togglePreviewPanel" title="Fermer l'aperçu">
                <span class="close-icon">✕</span>
              </button>
            </div>
            <div class="preview-container">
              <FileView :selected="selectedFile.id" :pageNumber="RoutePageNumber" :highlight-text="highlightText" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <DeleteDocumentModal :visible="showDeleteModal" :deleting="deleting" @close="cancelDelete" @confirm="confirmDelete" />
    <TaskModal :visible="isTaskModalVisible" :task="editingTask" :documentId="document.id"
      @close="closeTaskModal" @added="handleTaskSaved" @updated="handleTaskSaved" />
  </div>

  <AddFileModal v-if="showAddFileModal" :documentId="document.id" :visible="showAddFileModal"
    @close="closeAddFileModal" @added="FilesAdded" />
  <DeleteTaskModal :visible="isDeleteTaskModalVisible" :deleting="deletingTask"
    @close="closeDeleteTaskModal" @confirm="confirmDeleteTask" />
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import AddFileModal from "./AddFileModal.vue"
import DeleteTaskModal from "./DeleteTaskModal.vue"
import TasksTab from "./TasksTab.vue"
import AiTracePanel from "./AiTracePanel.vue"
import { useAuthStore } from "../stores/auth"

import { getDocumentById, deleteDocument as deleteDocumentService } from "../services/documentService"
import { getTasksByDocument, updateTaskStatus, deleteTask as deleteTaskService } from "../services/taskService"
import DeleteDocumentModal from "./DeleteDocumentModal.vue"
import DocumentSummary from "./DocumentSummary.vue"
import TaskModal from "./TaskModal.vue"
import CandidateStatusBadge from './CandidateStatusBadge.vue'
import ScoreValidationBanner from './ScoreValidationBanner.vue'
import SignatureBanner from './SignatureBanner.vue'
import { getCandidateByDocument, updateCandidateStatus, sendRecruitmentDecision } from '../services/recruitmentService.js'
import BaseApiService from "../services/ApiService"
import FileView from "./FileView.vue"
import { toast } from "vue3-toastify"
import "vue3-toastify/dist/index.css"

const AI_BASE = import.meta.env.VITE_AI_BACKEND_URL || 'http://localhost:8000'

const showAddFileModal = ref(false)
const closeAddFileModal = () => { showAddFileModal.value = false }

const route      = useRoute()
const router     = useRouter()
const authStore  = useAuthStore()

const document       = ref({})
const loading        = ref(false)
const error          = ref(null)
const activeTab      = ref("details")
const searchQuery    = ref("")
const selectedFile   = ref(null)
const candidate      = ref(null)
const statusLoading  = ref(false)
const scoreBannerKey = ref(0)

// ── Clé de contrôle : ScoreValidationBanner et CandidateStatusBadge
// ne s'affichent QUE quand l'analyse est terminée.
// "ATraiter" est posé AU DÉBUT de l'analyse — il n'est pas un indicateur de fin.
const analysisComplete = ref(false)

// True tant que ScoreValidationBanner a une pendingAction active.
// Quand c'est le cas, on masque les boutons d'action de CandidateStatusBadge
// pour éviter la duplication des actions RH.
const bannerActive = ref(false)

const documentTasks            = ref([])
const isTaskModalVisible       = ref(false)
const editingTask              = ref(null)
const taskToDelete             = ref(null)
const isDeleteTaskModalVisible = ref(false)
const deletingTask             = ref(false)
const showPreviewPanel         = ref(route.query.FileId ? true : false)
const highlightText            = ref(route.query.highlight || "")
const isClosing                = ref(false)
const showDeleteModal          = ref(false)
const deleting                 = ref(false)
const RoutePageNumber          = ref(parseInt(route.query.page, 10) || 1)
const traceLoading             = ref(false)

// ── Trace ReAct — source de vérité pour AiTracePanel ─────────────────────────
const lastReactTrace = ref([])
const aiDocumentType = ref('')  
/**
 * Charge la trace depuis le backend (/trace/{id}) qui l'a persistée sur disque.
 * Appelé au montage ET depuis le bouton "Charger la trace".
 */
const fetchTraceFromBackend = async () => {
  if (!document.value.id) return
  traceLoading.value = true
  try {
    const res  = await fetch(`${AI_BASE}/trace/${document.value.id}`)
    const data = await res.json()
    if (data.found && Array.isArray(data.trace) && data.trace.length) {
      lastReactTrace.value = data.trace
    }
  } catch (e) {
    console.warn('[DocumentDetails] fetchTraceFromBackend failed:', e)
  } finally {
    traceLoading.value = false
  }
}

const fetchAiDocumentType = async () => {
  if (!document.value.id) return
  try {
    const headers = authStore.token
      ? { Authorization: `Bearer ${authStore.token}` } : {}
    const res  = await fetch(`${AI_BASE}/document/${document.value.id}/ai`, { headers })
    if (!res.ok) return
    const data = await res.json()
    if (data.document_type) aiDocumentType.value = data.document_type
  } catch { /* non-bloquant */ }
}
const onDocumentSigned = (result) => {
  toast.success(`Document signé par ${result.signer_name || 'Signataire'}`)
  if (result.auto_enabled) {
    toast.info('Mode automatique activé — les prochains documents seront signés automatiquement')
  }
}

const filteredFiles = computed(() => {
  if (!document.value.files) return []
  if (!searchQuery.value) return document.value.files
  return document.value.files.filter(f =>
    f.fileName.toLowerCase().includes(searchQuery.value.toLowerCase()))
})

const loadDocument = async () => {
  loading.value = true
  error.value   = null
  try {
    const documentId = route.params.id
    const response   = await getDocumentById(documentId)
    document.value   = response
    const FileIdRoute = parseInt(route.query.FileId, 10)
    RoutePageNumber.value = parseInt(route.query.page, 10) || 1
    if (FileIdRoute) {
      selectedFile.value = document.value.files?.find(f => f.id === FileIdRoute) || null
    }
    await loadTasks()
    await loadCandidate()
    await _checkAnalysisAlreadyDone(documentId)
    await fetchAiDocumentType() 
    await fetchTraceFromBackend()
    sendDocContext()
  } catch (err) {
    error.value = "Erreur lors du chargement du document"
    console.error(err)
  } finally {
    loading.value = false
  }
}

/**
 * Vérifie si l'analyse est vraiment terminée en se basant UNIQUEMENT
 * sur le flag isAnalyzed de la DB (posé après la fin du pipeline complet).
 *
 * On N'utilise PAS le statut candidat ici : "ATraiter" est posé au début
 * de l'analyse par l'orchestrateur, donc il ne peut pas servir d'indicateur
 * de fin. Seuls les statuts post-décision (Entretien, Accepte, Refuse,
 * ListeAttente) peuvent indiquer qu'une analyse a eu lieu dans le passé.
 */
const _checkAnalysisAlreadyDone = async (documentId) => {
  // Statuts qui prouvent qu'une analyse + décision RH ont eu lieu.
  // ATraiter est EXCLU : c'est le statut initial posé en DÉBUT d'analyse,
  // pas à la fin. L'utiliser ici ferait apparaître les boutons trop tôt.
  const POST_DECISION_STATUSES = ['Entretien', 'Accepte', 'Refuse', 'ListeAttente']

  try {
    const MINIGED_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5092/api')
      .replace('/api', '')
    const _headers = authStore.token
      ? { Authorization: `Bearer ${authStore.token}` } : {}
    const res  = await fetch(
      `${MINIGED_BASE}/api/dashboard/document/${documentId}`,
      { headers: _headers }
    )
    if (!res.ok) return
    const data = await res.json()

    // Critère 1 : flag DB explicite — posé par orchestrateur à la FIN du pipeline
    if (data?.ai?.isAnalyzed && data?.ai?.summary) {
      analysisComplete.value = true
      return
    }
  } catch (e) {
    console.warn('[DocumentDetails] _checkAnalysisAlreadyDone failed:', e)
  }

  // Critère 2 : statut post-décision RH (analyse + action humaine dans le passé)
  if (candidate.value && POST_DECISION_STATUSES.includes(candidate.value.status)) {
    analysisComplete.value = true
  }
  // Si aucun critère n'est rempli, analysisComplete reste false :
  // les boutons n'apparaîtront qu'après onAnalyzed() émis par DocumentSummary.
}

const loadCandidate = async () => {
  candidate.value = await getCandidateByDocument(route.params.id, authStore.token)
}

/**
 * Appelé par DocumentSummary après chaque analyse (manuelle ou auto).
 *
 * analyzeResult contient la réponse brute de l'orchestrateur, notamment :
 *   - react_trace  : trace ReAct du pipeline
 *   - consolidated : résumé global
 *   - score_result : résultat du scoring
 *
 * C'est ici qu'on active analysisComplete et qu'on stocke la trace.
 */
const onAnalyzed = async (analyzeResult) => {
  // 1. Marquer l'analyse comme terminée → affiche bannière + badge
  analysisComplete.value = true
  scoreBannerKey.value++
  await fetchAiDocumentType()
  sendDocContext(analyzeResult?.document_type || aiDocumentType.value)
  // 2. Extraire la trace ReAct de la réponse directe
  const incomingTrace = analyzeResult?.react_trace
  if (Array.isArray(incomingTrace) && incomingTrace.length > 0) {
    lastReactTrace.value = [...incomingTrace]
  } else {
    // Pas de trace dans la réponse directe (analyse auto / polling) →
    // essayer de la charger depuis le backend (persistée sur disque par l'orchestrateur)
    await fetchTraceFromBackend()
  }

  // 3. Recharger candidat et tâches
  await loadCandidate()
  await loadTasks()
}

const onEmailValidated = async () => {
  // Recharger le candidat pour que CandidateStatusBadge affiche le bon statut
  await loadCandidate()
  // Incrémenter la clé pour forcer le remontage de ScoreValidationBanner
  // → elle refera un loadPendingAction() et trouvera null (action consommée)
  scoreBannerKey.value++
  toast.success('Action confirmée — statut candidat mis à jour')
}

const handleStatusUpdate = async (newStatus) => {
  if (!candidate.value) return
  statusLoading.value = true
  try {
    if ((newStatus === 'Accepte' || newStatus === 'Refuse')
        && candidate.value.status === 'Entretien') {
      const result = await sendRecruitmentDecision(
        candidate.value.candidateId, route.params.id, newStatus, authStore.token)
      candidate.value = { ...candidate.value, status: newStatus }
      if (result.email_sent) {
        toast.success(`Statut → ${newStatus} · Email envoyé à ${result.email_to}`)
      } else {
        toast.warning(`Statut → ${newStatus} · Email non envoyé : ${result.email_error || 'erreur inconnue'}`)
      }
    } else {
      await updateCandidateStatus(candidate.value.candidateId, newStatus, authStore.token)
      candidate.value = { ...candidate.value, status: newStatus }
      toast.success(`Statut mis à jour : ${newStatus}`)
    }
  } catch {
    toast.error('Erreur lors de la mise à jour du statut')
  } finally {
    statusLoading.value = false
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return "0 Bytes"
  const k = 1024, sizes = ["Bytes","KB","MB","GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
}

const getFileIcon = (fileName) => {
  const ext = fileName.split(".").pop().toLowerCase()
  const icons = {
    pdf:  '<i class="fas fa-file-pdf text-red-500"></i>',
    doc:  '<i class="far fa-file-word text-blue-500"></i>',
    docx: '<i class="far fa-file-word text-blue-500"></i>',
    xls:  '<i class="far fa-file-excel text-green-500"></i>',
    xlsx: '<i class="far fa-file-excel text-green-500"></i>',
    jpg:  '<i class="far fa-file-image text-purple-500"></i>',
    jpeg: '<i class="far fa-file-image text-purple-500"></i>',
    png:  '<i class="far fa-file-image text-purple-500"></i>',
    zip:  '<i class="far fa-file-archive text-gray-500"></i>',
  }
  return icons[ext] || '<i class="far fa-file text-gray-500"></i>'
}

const getFileType = (fileName) => {
  const ext = fileName.split(".").pop().toLowerCase()
  const types = { pdf:"PDF Document", doc:"Word Document", docx:"Word Document",
    xls:"Excel Spreadsheet", xlsx:"Excel Spreadsheet", jpg:"JPEG Image",
    jpeg:"JPEG Image", png:"PNG Image", mp4:"MP4 Video", mp3:"MP3 Audio", zip:"ZIP Archive" }
  return types[ext] || ext.toUpperCase() + " File"
}

// downloadFile : ouvrir ou télécharger via l'API MiniGED
const downloadFile = (file) => {
  const MINIGED_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5092/api')
    .replace('/api', '')
  window.open(`${MINIGED_BASE}/api/document/download/${file.id}`, '_blank')
}

const selectFile = (file) => {
  selectedFile.value     = file
  showPreviewPanel.value = true
}

const togglePreviewPanel = () => {
  if (showPreviewPanel.value) {
    isClosing.value = true
    setTimeout(() => { showPreviewPanel.value = false; isClosing.value = false }, 400)
  } else {
    showPreviewPanel.value = true
  }
}

const AddFiles   = () => { showAddFileModal.value = true }
const FilesAdded = () => { loadDocument(); activeTab.value = "files" }

const deleteFile = async (file) => {
  const response = await BaseApiService(`document/delete`).remove(file.id)
  if (response.data.success) {
    toast.success("Fichier supprimé", { autoclose: 3000 })
    loadDocument()
  } else {
    toast.error(response.data.message || "Erreur suppression", { autoclose: 3000 })
  }
}

const deleteDocument = () => { showDeleteModal.value = true }
const cancelDelete   = () => { showDeleteModal.value = false; deleting.value = false }

const confirmDelete = async () => {
  if (!document.value.id) return
  deleting.value = true
  try {
    await deleteDocumentService(document.value.id)
    router.push("/documents")
  } catch (err) {
    error.value = "Erreur lors de la suppression"
    deleting.value = false
  }
}

const navigateToHome      = () => { router.push("") }
const navigateToDocuments = () => { router.push("/documents") }

const loadTasks = async () => {
  if (!document.value.id) return
  try {
    documentTasks.value = await getTasksByDocument(document.value.id)
  } catch (err) {
    console.error("Erreur tâches:", err)
  }
}

const showTaskModal  = (task = null) => { editingTask.value = task; isTaskModalVisible.value = true }
const closeTaskModal = () => { isTaskModalVisible.value = false; editingTask.value = null }

const handleTaskSaved = (savedTask) => {
  if (editingTask.value) {
    const idx = documentTasks.value.findIndex(t => t.id === savedTask.id)
    if (idx !== -1) documentTasks.value.splice(idx, 1, savedTask)
    toast.success("Tâche modifiée", { autoclose: 2000 })
  } else {
    documentTasks.value.push(savedTask)
    toast.success("Tâche ajoutée", { autoclose: 2000 })
  }
  closeTaskModal()
  setTimeout(loadTasks, 100)
}

const handleTaskStatusChange = async (taskId, newStatus) => {
  try {
    await updateTaskStatus(taskId, newStatus)
    const task = documentTasks.value.find(t => t.id === taskId)
    if (task) task.status = newStatus
    toast.success("Statut tâche mis à jour", { autoclose: 2000 })
  } catch {
    toast.error("Erreur mise à jour statut", { autoclose: 3000 })
  }
}

const editTask   = (task)   => { showTaskModal(task) }
const deleteTask = (taskId) => { taskToDelete.value = taskId; isDeleteTaskModalVisible.value = true }

const confirmDeleteTask = async () => {
  if (!taskToDelete.value) return
  try {
    deletingTask.value = true
    await deleteTaskService(taskToDelete.value)
    documentTasks.value = documentTasks.value.filter(t => t.id !== taskToDelete.value)
    toast.success("Tâche supprimée", { autoclose: 2000 })
    closeDeleteTaskModal()
  } catch {
    toast.error("Erreur suppression tâche", { autoclose: 3000 })
  } finally {
    deletingTask.value = false
  }
}

const closeDeleteTaskModal = () => { isDeleteTaskModalVisible.value = false; taskToDelete.value = null }

// ── Transmet le contexte du document ouvert à l'assistant ─────────────────────
const sendDocContext = (overrideType = '') => {
  const ctx = {
    documentId:   String(document.value.id || ''),
    documentType: overrideType || aiDocumentType.value || '',
    filename:     document.value.title || '',
  }
  const payload = { type: 'DOC_CONTEXT', payload: ctx }

  // Envoyer au parent (DashboardView dans son iframe)
  if (window.parent !== window) {
    window.parent.postMessage(payload, '*')
  }

  // Cas où DocumentDetails est dans le window courant (pas d'iframe)
  window.postMessage(payload, window.location.origin)

  console.log('[DocumentDetails] DOC_CONTEXT envoyé:', ctx)
}

onMounted(() => {
  loadDocument()
  activeTab.value = "details"
})
</script>

<style scoped>
html, body { height: 100%; margin: 0; }

.document-details-container { display: flex; flex-direction: column; height: 100vh; }
.documents-header { flex-shrink: 0; }
.document-content { flex: 1; display: flex; flex-direction: column; min-height: 0; padding: 1rem; }
.nav-tabs { flex-shrink: 0; }

.breadcrumb { display: flex; align-items: center; gap: 0.5rem; font-size: 14px; color: #718096; }
.breadcrumb-current { color: #2d3748; font-weight: 500; }
.breadcrumb-link { cursor: pointer; transition: color 0.2s; }
.breadcrumb-link:hover { color: #667eea; text-decoration: underline; }

.loading { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #718096; gap: 1rem; }
.spinner { width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.error { text-align: center; color: #e53e3e; padding: 2rem; }

.document-layout { display: grid; gap: 2rem; height: 100%; transition: grid-template-columns 0.4s cubic-bezier(0.4,0,0.2,1); }
.document-layout.with-panel    { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.document-layout.without-panel { grid-template-columns: 1fr; }

.left-panel { grid-column: 1; background-color: white; border-radius: 12px; border: 1px solid #e9ecef; display: flex; flex-direction: column; overflow: hidden; }

.search-section { padding: 1.5rem; border-bottom: 1px solid #e9ecef; }
.search-input-container { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 12px; color: #718096; font-size: 14px; }
.search-files-input { flex: 1; padding: 0.75rem 2.5rem; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; background-color: #f7fafc; }

.nav-tabs { display: flex; align-items: center; justify-content: flex-start; border-bottom: 1px solid #e9ecef; gap: 0.5rem; }
.nav-tab { padding: 1rem 1.5rem; border: none; background: none; font-size: 14px; cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; flex: 0 0 auto; display: flex; align-items: center; gap: 4px; }
.nav-tab:hover { background-color: #f7fafc; }
.nav-tab.active { color: #667eea; border-bottom-color: #667eea; background-color: #f7fafc; }

.trace-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  background: #6366f1; color: white;
  font-size: 9px; font-weight: 800; min-width: 16px; height: 16px;
  border-radius: 8px; padding: 0 4px; margin-left: 2px;
}

.details-section, .files-section { flex: 1; padding: 1.5rem; overflow-y: auto; }
.section-title { font-size: 12px; font-weight: 400; color: #2d3748; margin: 0 0 0.5rem 0; }

.detail-field { margin-bottom: 1.5rem; }
.detail-label { display: block; font-size: 14px; font-weight: 500; color: #4a5568; margin-bottom: 0.5rem; }
.detail-input, .detail-textarea { width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 14px; background-color: #f7fafc; }
.detail-textarea { resize: vertical; min-height: 80px; }

.files-list { display: flex; flex-direction: column; gap: 0.75rem; }
.file-item { display: flex; align-items: center; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
.file-item:hover { border-color: #667eea; background-color: #f7fafc; }
.file-icon { font-size: 24px; margin-right: 0.75rem; }
.file-info { flex: 1; }
.file-name { font-size: 14px; font-weight: 500; color: #2d3748; margin-bottom: 0.25rem; }
.file-meta { font-size: 12px; color: #718096; }
.file-actions { display: flex; gap: 0.5rem; }
.file-action-btn { display: flex; align-items: center; justify-content: center; width: 27px; height: 27px; border: none; background-color: #f7fafc; border-radius: 6px; cursor: pointer; transition: background-color 0.2s; }
.file-action-btn:hover { background-color: #edf2f7; color: #4a5568; border: 1px solid #2d3748; }
.delete-btn:hover { background-color: #fed7d7; color: #e53e3e; border: 1px solid #feb2b2; }
.download-btn:hover { background-color: #e6f0ff; color: #2563eb; border: 1px solid #93c5fd; }

.action-btn { display: flex; align-items: center; gap: 0.5rem; max-width: 300px; padding: 0.75rem 1rem; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; flex: 0 0 auto; }
.action-btn.primary   { border-radius: 25px; color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.action-btn.secondary { background-color: #f7fafc; color: #4a5568; border-radius: 25px; border: 1px solid #e2e8f0; }
.action-btn.danger    { border-radius: 25px; background-color: #fed7d7; color: #e53e3e; border: 1px solid #feb2b2; }
.action-btn:hover { transform: translateY(-1px); }

/* Trace hint */
.trace-fetch-hint { padding: 24px 16px; }
.trace-hint-content {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  text-align: center; padding: 32px 20px;
  background: linear-gradient(135deg, #f5f3ff, #eff6ff);
  border: 1px solid #c4b5fd; border-radius: 14px;
}
.trace-hint-title { font-size: 14px; font-weight: 700; color: #1e293b; margin: 0 0 4px; }
.trace-hint-sub { font-size: 12px; color: #64748b; margin: 0; }
.trace-reload-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 20px; border-radius: 10px; border: none;
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
  margin-top: 4px;
}
.trace-reload-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99,102,241,0.35); }
.trace-reload-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.right-panel { background-color: white; border-radius: 12px; border: 1px solid #e9ecef; display: flex; flex-direction: column; transform: translateX(0); opacity: 1; transition: all 0.4s cubic-bezier(0.4,0,0.2,1); animation: slideInRight 0.4s cubic-bezier(0.4,0,0.2,1); }
.right-panel.closing { transform: translateX(100%); opacity: 0; }
@keyframes slideInRight { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

.document-preview { flex: 1; display: flex; flex-direction: column; }
.preview-header { display: flex; justify-content: space-between; align-items: center; padding: 1.5rem 1.5rem 0 1.5rem; margin-bottom: 1.5rem; }
.breadcrumb-path { font-size: 14px; color: #718096; display: flex; align-items: center; gap: 0.5rem; flex: 1; }
.close-panel-btn { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; background-color: #f7fafc; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; color: #718096; font-size: 14px; }
.close-panel-btn:hover { background-color: #e2e8f0; color: #4a5568; }
.close-icon { font-weight: bold; }
.current-file { color: #2d3748; font-weight: 500; }
.preview-container { flex: 1; display: flex; align-items: center; justify-content: center; background: white; border-radius: 12px; padding: 0; margin: 0 1.5rem 1.5rem 1.5rem; }

@media (max-width: 768px) { .document-content { padding: 0.75rem; } }
</style>