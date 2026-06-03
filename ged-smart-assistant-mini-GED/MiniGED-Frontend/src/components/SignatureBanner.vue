<template>
  <div v-if="show" class="sig-banner" :class="bannerClass">

    <!-- Header -->
    <div class="sig-banner-header">
      <div class="sig-banner-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
      </div>
      <div class="sig-banner-info">
        <div class="sig-banner-title">
          <strong v-if="alreadySigned">✅ Document signé</strong>
          <strong v-else>Ce document nécessite une signature</strong>
        </div>
        <div class="sig-banner-sub" v-if="alreadySigned">
          Signé par {{ signedBy }} — {{ signedAt }}
        </div>
        <div class="sig-banner-sub" v-else-if="profile.auto_enabled">
          ⚡ Mode automatique actif — signature appliquée automatiquement
        </div>
        <div class="sig-banner-sub" v-else>
          {{ profile.confirmations || 0 }} / 2 confirmations —
          encore {{ Math.max(0, 2 - (profile.confirmations || 0)) }}
          pour activer le mode automatique
        </div>
      </div>
      <button v-if="!alreadySigned" class="sig-toggle-btn" @click="showDetails = !showDetails">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline v-if="showDetails" points="18 15 12 9 6 15"/>
          <polyline v-else            points="6 9 12 15 18 9"/>
        </svg>
      </button>
    </div>

    <!-- Expandable body -->
    <transition name="slide-down">
      <div v-if="showDetails && !alreadySigned" class="sig-banner-body">

        <!-- Detected zones -->
        <div v-if="detectedZones.length" class="sig-zones">
          <div class="sig-zones-title">Zones de signature détectées :</div>
          <div v-for="(zone, i) in detectedZones" :key="i" class="sig-zone-item">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ zone }}</span>
          </div>
        </div>

        <!-- Learning progress -->
        <div class="sig-progress-wrap">
          <div class="sig-progress-label">
            Apprentissage signature
            <span class="sig-progress-count">{{ profile.confirmations || 0 }}/2</span>
          </div>
          <div class="sig-progress-track">
            <div class="sig-progress-fill" :style="{ width: progressPct + '%' }"/>
          </div>
        </div>

        <!-- Actions -->
        <div class="sig-banner-actions">
          <button
            class="sig-action-btn sig-action-btn--primary"
            :disabled="loadingPdf"
            @click="openPad"
          >
            <svg v-if="!loadingPdf" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"/>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            <svg v-else class="sig-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            {{ loadingPdf ? 'Chargement du PDF…' : 'Signer maintenant' }}
          </button>
          <button class="sig-action-btn sig-action-btn--ghost" @click="dismiss">Ignorer</button>
        </div>

        <!-- PDF load error -->
        <div v-if="loadError" class="sig-error">{{ loadError }}</div>
      </div>
    </transition>

    <!-- Signature pad modal -->
    <SignaturePad
      v-if="showPad"
      :pdfBase64="pdfBase64"
      :filename="pdfFilename"
      :documentType="resolvedDocType"
      :profile="profile"
      @close="showPad = false"
      @signed="onSigned"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import SignaturePad from './SignaturePad.vue'
import { useAuthStore } from '../stores/auth'
import apiClient from '../services/api'   // axios instance with auto-auth headers

const props = defineProps({
  documentId:   { type: [String, Number], required: true },
  /** Pre-resolved document type from DocumentDetails (avoids extra fetch) */
  documentType: { type: String, default: '' },
})
const emit = defineEmits(['signed'])

const PYTHON_API = import.meta.env.VITE_AI_BACKEND_URL || 'http://localhost:8000'

const authStore = useAuthStore()

// ── State ─────────────────────────────────────────────────────────────────────
const show           = ref(false)
const showDetails    = ref(true)
const showPad        = ref(false)
const dismissed      = ref(false)
const loadingPdf     = ref(false)
const loadError      = ref('')

const detectedZones  = ref([])
const alreadySigned  = ref(false)
const signedBy       = ref('')
const signedAt       = ref('')

const profile        = ref({ confirmations: 0, auto_enabled: false, signer_name: '' })
const pdfBase64      = ref('')
const pdfFilename    = ref('')
const resolvedDocType = ref(props.documentType || '')

const currentFileId  = ref(null)

// ── Types that require a signature ───────────────────────────────────────────
const SIGNABLE_TYPES = new Set([
  'Contrat de travail', 'Juridique', 'Contrat',
  'Accord', 'Convention', 'Avenant', 'NDA', 'Autre',
])

const progressPct = computed(() =>
  profile.value.auto_enabled ? 100
    : Math.min(100, ((profile.value.confirmations || 0) / 2) * 100)
)

const bannerClass = computed(() => ({
  'sig-banner--done':   alreadySigned.value,
  'sig-banner--needed': !alreadySigned.value,
}))

// ── Init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    loadSignatureProfile(),
    detectSignatureNeeded(),
  ])
})

/**
 * Load user signature profile from the Python backend.
 * No auth required (profile is keyed by user_id from STM).
 */
const loadSignatureProfile = async () => {
  try {
    const res = await fetch(`${PYTHON_API}/signature/profile`)
    if (res.ok) profile.value = await res.json()
  } catch { /* non-blocking */ }
}

/**
 * Determine if this document needs a signature.
 *
 * Priority order:
 *   1. documentType prop already set (from DocumentDetails after analysis) → instant
 *   2. Fetch /api/dashboard/document/{id} via apiClient (JWT auto-attached)
 *
 * This fixes the 401 error: apiClient sends the stored JWT automatically.
 */
const detectSignatureNeeded = async () => {
  // 1. Use prop if already resolved
  if (props.documentType) {
    resolvedDocType.value = props.documentType
    if (SIGNABLE_TYPES.has(props.documentType)) {
      show.value = !dismissed.value
    }
    return
  }

  // 2. Fetch from MiniGED via apiClient (auth header injected automatically)
  try {
    const { data } = await apiClient.get(`/dashboard/document/${props.documentId}`)
    const docType = data?.ai?.documentType || data?.aiDocumentType || ''
    resolvedDocType.value = docType

    if (SIGNABLE_TYPES.has(docType)) {
      show.value = !dismissed.value
    }
  } catch (e) {
    // 401 or network error — silently skip; banner simply won't show
    console.warn('[SignatureBanner] Could not detect document type:', e?.response?.status || e.message)
  }
}

const dismiss = () => {
  dismissed.value = true
  show.value = false
}

/**
 * Fetch the PDF bytes via apiClient (auth header injected) and open the pad.
 */
const openPad = async () => {
  loadingPdf.value = true
  loadError.value  = ''
  try {
    // Get file list
    const { data: doc } = await apiClient.get(`/document/${props.documentId}`)
    const files = doc?.Files || doc?.files || []

    if (!files.length) {
      loadError.value = 'Aucun fichier PDF disponible pour ce document.'
      return
    }

    // Pick first PDF (or first file)
    const file = files.find(f => (f.FileName || f.fileName || '').toLowerCase().endsWith('.pdf'))
               || files[0]
    const fileId  = file.Id   || file.id
    const fname   = file.FileName || file.fileName || 'document.pdf'
    pdfFilename.value = fname
    

    // Download PDF bytes — use axios responseType blob
    const { data: blob } = await apiClient.get(
      `/document/pdf/${fileId}`,
      { responseType: 'blob' }
    )

    // Convert blob to base64
    pdfBase64.value = await blobToBase64(blob)
    showPad.value   = true
  } catch (e) {
    loadError.value = `Impossible de charger le PDF : ${e?.response?.status ? 'HTTP ' + e.response.status : e.message}`
    console.error('[SignatureBanner] openPad error:', e)
  } finally {
    loadingPdf.value = false
  }
}

const blobToBase64 = (blob) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload  = () => resolve(reader.result.split(',')[1])
  reader.onerror = reject
  reader.readAsDataURL(blob)
})

const onSigned = async (result) => {
  showPad.value       = false
  alreadySigned.value = true
  signedBy.value      = result.signer_name || ''
  signedAt.value      = new Date().toLocaleDateString('fr-FR')
  await loadSignatureProfile()   // refresh learning profile counters
  emit('signed', result)
}
</script>

<style scoped>
.sig-banner {
  border-radius: 12px;
  border: 1px solid;
  padding: 14px 16px;
  margin: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.sig-banner--needed { border-color: #c7d2fe; background: #eef2ff; }
.sig-banner--done   { border-color: #bbf7d0; background: #f0fdf4; }

/* Header */
.sig-banner-header { display: flex; align-items: center; gap: 12px; }
.sig-banner-icon {
  flex-shrink: 0; width: 36px; height: 36px; border-radius: 8px;
  background: #e0e7ff;
  display: flex; align-items: center; justify-content: center; color: #6366f1;
}
.sig-banner--done .sig-banner-icon { background: #dcfce7; color: #16a34a; }
.sig-banner-info { flex: 1; }
.sig-banner-title { font-weight: 600; color: #1e1b4b; margin-bottom: 2px; }
.sig-banner--done .sig-banner-title { color: #14532d; }
.sig-banner-sub { font-size: 12px; color: #6b7280; }
.sig-toggle-btn {
  background: none; border: none; cursor: pointer;
  color: #6b7280; padding: 4px; border-radius: 6px; transition: background .15s;
}
.sig-toggle-btn:hover { background: #e0e7ff; }

/* Body */
.sig-banner-body { display: flex; flex-direction: column; gap: 12px; }

/* Zones */
.sig-zones { display: flex; flex-direction: column; gap: 4px; }
.sig-zones-title { font-size: 12px; font-weight: 500; color: #374151; margin-bottom: 4px; }
.sig-zone-item {
  display: flex; align-items: flex-start; gap: 6px;
  font-size: 12px; color: #4b5563;
  background: white; border: 1px solid #e0e7ff; border-radius: 6px; padding: 6px 10px;
}

/* Progress */
.sig-progress-wrap { display: flex; flex-direction: column; gap: 4px; }
.sig-progress-label { display: flex; justify-content: space-between; font-size: 12px; color: #6b7280; }
.sig-progress-count { font-weight: 600; color: #6366f1; }
.sig-progress-track { height: 5px; background: #e0e7ff; border-radius: 99px; overflow: hidden; }
.sig-progress-fill  { height: 100%; background: #6366f1; border-radius: 99px; transition: width .4s ease; }

/* Actions */
.sig-banner-actions { display: flex; gap: 8px; }
.sig-action-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all .15s;
}
.sig-action-btn:disabled { opacity: .5; cursor: not-allowed; }
.sig-action-btn--primary { background: #6366f1; color: white; }
.sig-action-btn--primary:hover:not(:disabled) { background: #4f46e5; }
.sig-action-btn--ghost { background: transparent; color: #6b7280; border: 1px solid #d1d5db; }
.sig-action-btn--ghost:hover { background: #f3f4f6; }

.sig-spin { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg) } }

/* Error */
.sig-error {
  background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 8px; padding: 8px 12px;
  font-size: 12px; color: #dc2626;
}

/* Transition */
.slide-down-enter-active, .slide-down-leave-active { transition: all .2s ease; overflow: hidden; }
.slide-down-enter-from, .slide-down-leave-to { max-height: 0; opacity: 0; }
.slide-down-enter-to, .slide-down-leave-from { max-height: 500px; opacity: 1; }
</style>