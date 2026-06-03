<template>
  <div class="ai-summary-section">

    <div class="btn-row">
      <!-- Le bouton manuel reste disponible si l'analyse n'a pas encore démarré
           et qu'il n'y a pas de fichiers avec texte (PDF non encore traité par Hangfire) -->
      <button
        v-if="!summary && !isLoading && showManualBtn"
        class="action-btn ai-btn"
        @click="computeAnalysis"
      >
        <span class="btn-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
               stroke-width="1.5" stroke="currentColor" class="size-6">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12
                 l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0
                 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
          </svg>
        </span>
        Analyser le document
      </button>

      <template v-if="summary && !isLoading">
        <button class="action-btn show-btn" @click="showCard = !showCard">
          <i :class="showCard ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
          {{ showCard ? 'Masquer' : "Afficher l'analyse" }}
        </button>
        <button class="action-btn regen-btn" @click="computeAnalysis" :disabled="isLoading">
          <i class="fas fa-rotate-right"></i>
          Regénérer
        </button>
      </template>
    </div>

    <!-- Indicateur d'analyse automatique en cours -->
    <transition name="fade-slide">
      <div v-if="isLoading" class="summary-card">
        <div class="summary-header">
          <div class="summary-title-row">
            <span class="summary-label">✦ ANALYSE IA EN COURS...</span>
            <span class="auto-badge" v-if="isAutoTriggered">
              <i class="fas fa-bolt"></i> Automatique
            </span>
          </div>
        </div>
        <div class="skeleton-lines">
          <div class="skeleton-line" style="width:100%"></div>
          <div class="skeleton-line" style="width:83%"></div>
          <div class="skeleton-line" style="width:66%"></div>
          <div class="skeleton-line" style="width:83%"></div>
        </div>
      </div>
    </transition>

    <!-- Résultat de l'analyse -->
    <transition name="fade-slide">
      <div v-if="summary && showCard && !isLoading" class="summary-card">
        <div class="summary-header">
          <div class="summary-title-row">
            <span class="summary-label">✦ ANALYSE IA</span>
            <div class="summary-badges">
              <span v-if="fromCache" class="cache-badge">
                <i class="fas fa-database"></i> Depuis la mémoire
              </span>
              <span v-if="docType && docType !== 'Non analysé'"
                    class="doc-type-badge" :class="docTypeBadgeClass">
                {{ docType }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="fileSummaries.length > 1" class="file-types-row">
          <span class="file-types-label">Fichiers détectés :</span>
          <span v-for="fs in fileSummaries" :key="fs.filename"
                class="file-type-chip" :class="getFileTypeBadgeClass(fs.document_type)">
            <i class="fas fa-file-alt"></i>
            {{ fs.filename }} → {{ fs.document_type }}
          </span>
        </div>

        <div class="summary-section">
          <div class="section-title">Synthèse globale</div>
          <p class="summary-text">{{ summary }}</p>
        </div>

        <div v-if="fileSummaries.length > 1" class="file-summaries">
          <div class="section-title">Détail par fichier</div>
          <div v-for="fs in fileSummaries" :key="fs.filename" class="file-summary-item">
            <div class="file-summary-header">
              <span class="file-type-tag" :class="getFileTypeBadgeClass(fs.document_type)">
                {{ fs.document_type }}
              </span>
              <span class="file-name">{{ fs.filename }}</span>
            </div>
            <p class="file-summary-text">{{ fs.summary }}</p>
          </div>
        </div>

        <div v-if="analyzedAt" class="summary-footer">
          Analysé le {{ formatDate(analyzedAt) }}
        </div>
      </div>
    </transition>

    <transition name="fade-slide">
      <div v-if="errorMsg" class="summary-error">
        <i class="fas fa-triangle-exclamation"></i> {{ errorMsg }}
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import AuthService from '../services/auth'

const props = defineProps({
  documentId: { type: [Number, String], required: true },
})

const emit = defineEmits(['analyzed'])

const AI_BASE      = import.meta.env.VITE_AI_BACKEND_URL || 'http://localhost:8000'
const MINIGED_BASE = (import.meta.env.VITE_API_BASE_URL  || 'http://localhost:5092/api')
                       .replace('/api', '')

const isLoading       = ref(false)
const isAutoTriggered = ref(false)  // distingue auto vs manuel dans l'UI
const showManualBtn   = ref(false)  // affiché seulement si pas de texte extrait
const summary         = ref('')
const docType         = ref('')
const fileSummaries   = ref([])
const analyzedAt      = ref(null)
const fromCache       = ref(false)
const showCard        = ref(false)
const errorMsg        = ref('')

const docTypeBadgeClass = computed(() => ({
  'badge-candidature': docType.value === 'Candidature',
  'badge-dossier-rh':  docType.value?.includes('Dossier RH'),
  'badge-contrat':     docType.value === 'Contrat de travail',
  'badge-offre':       docType.value === "Offre d'emploi",
  'badge-juridique':   docType.value === 'Juridique',
  'badge-technique':   docType.value === 'Technique',
  'badge-autre':       !['Candidature','Dossier RH','Dossier RH complet',
                         'Contrat de travail',"Offre d'emploi",
                         'Juridique','Technique'].includes(docType.value),
}))

const getFileTypeBadgeClass = (type) => ({
  'badge-cv':      type === 'CV',
  'badge-lettre':  type === 'Lettre de motivation',
  'badge-offre':   type === "Offre d'emploi",
  'badge-contrat': type === 'Contrat de travail',
  'badge-autre':   !['CV','Lettre de motivation',
                     "Offre d'emploi",'Contrat de travail'].includes(type),
})

const authHeader = () => {
  const token = AuthService.getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ── Mount : vérification + auto-déclenchement ─────────────────────────────────
onMounted(async () => {
  if (!props.documentId) return
  try {
    const { data } = await axios.get(
      `${MINIGED_BASE}/api/dashboard/document/${props.documentId}`,
      { headers: authHeader() }
    )

    if (data?.ai?.summary) {
      // ── Déjà analysé → afficher depuis le cache ──────────────────────────
      summary.value    = data.ai.summary
      docType.value    = data.ai.documentType || ''
      analyzedAt.value = data.ai.analyzedAt
      fromCache.value  = true
      showCard.value   = true   // afficher directement les boutons
      if (data.files) {
        fileSummaries.value = data.files
          .filter(f => f.isAnalyzed && f.aiSummary)
          .map(f => ({
            file_id:       f.id,
            filename:      f.filename,
            document_type: f.aiFileType || '',
            summary:       f.aiSummary  || '',
          }))
      }
      emit('analyzed', { react_trace: [] })  // notifier DocumentDetails
      return
    }

    // ── Pas encore analysé ────────────────────────────────────────────────
    const allFiles      = data?.files || []
    const filesWithText = allFiles.filter(
      f => f.extractedText || f.hasText || f.pageCount > 0
        || f.fileSize > 0  // fichier uploadé même si texte pas encore extrait
    )

    if (allFiles.length > 0) {
      // Des fichiers existent → lancer l'analyse automatiquement
      // (le backend récupère le texte via MCP MiniGED, pas besoin d'extraction côté front)
      isAutoTriggered.value = true
      computeAnalysis()
    } else {
      // Aucun fichier → afficher le bouton manuel
      showManualBtn.value = true
    }

  } catch (_) {
    // Silencieux — le bouton manuel reste disponible
    showManualBtn.value = true
  }
})

// ── Analyse ──────────────────────────────────────────────────────────────────
const computeAnalysis = async () => {
  isLoading.value = true
  errorMsg.value  = ''
  fromCache.value = false
  showCard.value  = false
  showManualBtn.value = false

  try {
    const { data } = await axios.post(
      `${AI_BASE}/analyze-document/${props.documentId}`,
      {
        miniged_token: AuthService.getToken() || '',
        force:         true,
        user_id:       (() => { try { const t = AuthService.getToken() || ''; return JSON.parse(atob(t.split('.')[1]))?.sub || 'ged_user' } catch { return 'ged_user' } })(),
      },
      { timeout: 320000 }
    )

    const rawSummary = data.consolidated || ''
    if (!rawSummary || rawSummary === 'Aucun fichier disponible.') {
      errorMsg.value      = "L'analyse n'a retourné aucun résumé. Vérifiez les fichiers du document."
      showManualBtn.value = !isAutoTriggered.value
      return
    }

    summary.value       = rawSummary
    docType.value       = data.document_type || ''
    fileSummaries.value = data.summaries?.filter(s => !s.skipped) || []
    analyzedAt.value    = new Date().toISOString()
    showCard.value      = true

    await saveToPostgres()

    // Émettre toutes les données utiles pour DocumentDetails
    emit('analyzed', {
      react_trace:    data.react_trace    || [],
      consolidated:   data.consolidated   || '',
      document_type:  data.document_type  || '',
      score_result:   data.score_result   || {},
      ace_suggestion: data.ace_suggestion || null,
    })

  } catch (err) {
    console.error('[DocumentSummary] Analyse échouée :', err)
    if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
      errorMsg.value = "L'analyse prend plus de temps que prévu. Vérifiez l'onglet Tâches."
      emit('analyzed', {})
    } else if (isAutoTriggered.value) {
      // Analyse auto échouée → montrer le bouton manuel en fallback
      errorMsg.value = "L'analyse automatique a échoué. Cliquez sur le bouton pour relancer."
      showManualBtn.value = true
    } else {
      errorMsg.value = "L'analyse a échoué. Vérifiez que le backend IA est démarré."
    }
  } finally {
    isLoading.value       = false
    isAutoTriggered.value = false
  }
}

// ── Sauvegarde PostgreSQL ────────────────────────────────────────────────────
const saveToPostgres = async () => {
  try {
    await axios.patch(
      `${MINIGED_BASE}/api/dashboard/document/${props.documentId}/ai`,
      {
        summary:      summary.value,
        documentType: docType.value,
        fileSummaries: fileSummaries.value
          .filter(s => s.file_id)
          .map(s => ({
            fileId:     s.file_id,
            filename:   s.filename,
            aiFileType: s.document_type,
            aiSummary:  s.summary,
          })),
      },
      { headers: authHeader() }
    )
  } catch (err) {
    console.warn('[DocumentSummary] Stockage PostgreSQL échoué (non bloquant):', err)
  }
}

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ── API publique exposée au parent (DocumentDetails.vue) ──────────────────────
// Utilisation : <DocumentSummary ref="summaryRef" /> → summaryRef.value.triggerAnalysis()
// Appelé par DocumentDetails.vue après un FilesAdded()
defineExpose({ triggerAnalysis: computeAnalysis })
</script>

<style scoped>
.ai-summary-section { margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }

.btn-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }

.action-btn {
  display: inline-flex; align-items: center; gap: 0.5rem;
  padding: 0.65rem 1.2rem; border: none; border-radius: 25px;
  font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s;
}

.ai-btn { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; }
.ai-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99,102,241,.35); }
.ai-btn:disabled { opacity: .7; cursor: not-allowed; }

.show-btn { background: #f0f9ff; color: #0369a1; border: 1px solid #bae6fd; }
.show-btn:hover { background: #e0f2fe; transform: translateY(-1px); }

.regen-btn { background: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe; }
.regen-btn:hover:not(:disabled) { background: #ede9fe; transform: translateY(-1px); }

.auto-badge {
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
  background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe;
  display: flex; align-items: center; gap: 4px;
}

.summary-card {
  background: #f8f7ff; border: 1px solid #e0e7ff; border-left: 4px solid #6366f1;
  border-radius: 10px; padding: 1rem 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;
}

.summary-header { border-bottom: 1px solid #e0e7ff; padding-bottom: .6rem; }
.summary-title-row { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
.summary-label { font-size: 12px; font-weight: 600; color: #6366f1; text-transform: uppercase; letter-spacing: .05em; }
.summary-badges { display: flex; align-items: center; gap: .4rem; }

.file-types-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem;
  padding: 0.5rem 0; border-bottom: 1px solid #e0e7ff;
}
.file-types-label { font-size: 11px; color: #6b7280; font-weight: 500; }
.file-type-chip {
  font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 12px;
  display: inline-flex; align-items: center; gap: 4px;
}

.summary-section { display: flex; flex-direction: column; gap: .4rem; }
.section-title { font-size: 11px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: .05em; }
.summary-text { font-size: 13.5px; line-height: 1.7; color: #374151; margin: 0; white-space: pre-wrap; }

.file-summaries { display: flex; flex-direction: column; gap: .75rem; }
.file-summary-item { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: .75rem 1rem; }
.file-summary-header { display: flex; align-items: center; gap: .5rem; margin-bottom: .5rem; }
.file-type-tag { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 12px; }
.file-name { font-size: 12px; color: #6b7280; }
.file-summary-text { font-size: 13px; line-height: 1.6; color: #374151; margin: 0; }

.cache-badge { font-size: 10px; font-weight: 500; padding: 2px 8px; border-radius: 20px; background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.doc-type-badge { font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 20px; }
.badge-candidature { background: #ede9fe; color: #7c3aed; }
.badge-dossier-rh  { background: #fef3c7; color: #d97706; }
.badge-contrat     { background: #dcfce7; color: #16a34a; }
.badge-offre       { background: #dbeafe; color: #2563eb; }
.badge-juridique   { background: #fef3c7; color: #d97706; }
.badge-technique   { background: #dbeafe; color: #2563eb; }
.badge-autre       { background: #f3f4f6; color: #6b7280; }

.badge-cv      { background: #ede9fe; color: #7c3aed; }
.badge-lettre  { background: #fef9c3; color: #a16207; }
.badge-offre   { background: #dbeafe; color: #1d4ed8; }
.badge-contrat { background: #dcfce7; color: #15803d; }
.badge-autre   { background: #f3f4f6; color: #6b7280; }

.summary-footer { font-size: 11px; color: #9ca3af; border-top: 1px solid #e0e7ff; padding-top: .5rem; }
.summary-error { font-size: 13px; color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: .6rem 1rem; }

.skeleton-lines { display: flex; flex-direction: column; gap: .5rem; }
.skeleton-line {
  height: 12px; background: linear-gradient(90deg,#e0e7ff 25%,#c7d2fe 50%,#e0e7ff 75%);
  background-size: 200% 100%; border-radius: 6px; animation: shimmer 1.5s infinite;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

.fade-slide-enter-active { transition: all .35s ease; }
.fade-slide-leave-active { transition: all .2s ease; }
.fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>