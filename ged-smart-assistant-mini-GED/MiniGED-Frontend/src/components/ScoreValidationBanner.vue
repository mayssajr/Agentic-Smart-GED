<template>
  <div v-if="pendingAction" class="score-banner" :class="bannerClass">

    <!-- ── En-tête : score + recommandation ────────────────────────────────── -->
    <div class="banner-header">
      <div class="score-circle" :class="circleClass">
        <span class="score-value">{{ pendingAction.payload.score }}</span>
        <span class="score-max">/100</span>
      </div>

      <div class="banner-info">
        <div class="banner-title">
          <component :is="recoIcon" class="reco-icon" />
          <strong>{{ recoLabel }}</strong>
          <span class="reco-chip" :class="chipClass">
            {{ pendingAction.payload.recommendation }}
          </span>
        </div>
        <div class="banner-sub">
          <UserIcon class="meta-icon" />
          {{ pendingAction.payload.candidate_name }}
          <span class="sep">·</span>
          <BriefcaseIcon class="meta-icon" />
          {{ pendingAction.payload.position }}
        </div>
      </div>

      <button class="toggle-btn" @click="showDetails = !showDetails"
              :title="showDetails ? 'Réduire' : 'Voir les détails'">
        <ChevronUpIcon   v-if="showDetails" class="btn-icon-sm" />
        <ChevronDownIcon v-else             class="btn-icon-sm" />
      </button>
    </div>

    <!-- ── Section ACE (phase + confiance + message) ───────────────────────── -->
    <div v-if="aceSuggestion" class="ace-section" :class="aceSectionClass">
      <div class="ace-header">
        <span class="ace-phase-badge" :class="acePhaseBadgeClass">
          {{ aceSuggestion.phase_label || 'ACE' }}
        </span>
        <span class="ace-confidence" v-if="aceSuggestion.confidence > 0">
          {{ Math.round(aceSuggestion.confidence * 100) }}% confiance
        </span>
        <span class="ace-overrides" v-if="aceSuggestion.total_overrides !== undefined">
          · {{ aceSuggestion.total_overrides }} décisions RH mémorisées
        </span>
      </div>
      <p class="ace-message">{{ aceSuggestion.message }}</p>
      <p v-if="!aceSuggestion.auto_acted" class="ace-validation-required">
        ⚠ Votre validation est requise — ACE ne peut pas encore agir seul.
      </p>

      <!-- Justifications ACE (bullets +/-) -->
      <div v-if="aceSuggestion.justifications?.length" class="ace-justifications">
        <div class="ace-just-title">Règles ACE appliquées :</div>
        <div v-for="j in aceSuggestion.justifications" :key="j.bullet_id"
             class="ace-just-item" :class="j.sign === '+' ? 'just-plus' : j.sign === '-' ? 'just-minus' : 'just-info'">
          <span class="just-sign">{{ j.sign }}</span>
          <span class="just-text">{{ j.text }}</span>
          <span class="just-helpful" v-if="j.helpful_count > 0">×{{ j.helpful_count }}</span>
        </div>
      </div>
    </div>

    <!-- ── Détails (forces / lacunes / résumé / email) ──────────────────────── -->
    <transition name="slide-down">
      <div v-if="showDetails" class="banner-details">

        <!-- Points forts / Axes d'amélioration -->
        <div class="score-grid"
             v-if="pendingAction.payload.strengths?.length || pendingAction.payload.gaps?.length">
          <div v-if="pendingAction.payload.strengths?.length" class="score-col strengths">
            <div class="col-title">
              <CheckCircleIcon class="col-icon strengths-icon" /> Points forts
            </div>
            <ul>
              <li v-for="s in pendingAction.payload.strengths" :key="s">{{ s }}</li>
            </ul>
          </div>
          <div v-if="pendingAction.payload.gaps?.length" class="score-col gaps">
            <div class="col-title">
              <AlertTriangleIcon class="col-icon gaps-icon" /> Axes d'amélioration
            </div>
            <ul>
              <li v-for="g in pendingAction.payload.gaps" :key="g">{{ g }}</li>
            </ul>
          </div>
        </div>

        <!-- Résumé IA -->
        <div v-if="pendingAction.payload.summary" class="summary-block">
          <SparklesIcon class="summary-icon" />
          <span>{{ pendingAction.payload.summary }}</span>
        </div>

        <!-- Créneau entretien -->
        <div v-if="pendingAction.payload.slot_formatted" class="slot-block">
          <CalendarIcon class="slot-icon" />
          <div class="slot-content">
            <span class="slot-label">Entretien planifié</span>
            <span class="slot-value">{{ pendingAction.payload.slot_formatted }}</span>
          </div>
          <a v-if="pendingAction.payload.event_link"
             :href="pendingAction.payload.event_link"
             target="_blank" class="cal-link">
            <ExternalLinkIcon class="link-icon" />
            Voir sur Calendar
          </a>
        </div>

        <!-- Brouillon email éditable
        <div class="email-preview">
          <div class="email-preview-header">
            <MailIcon class="mail-icon" />
            <span>Email à envoyer à</span>
            <strong class="email-to">{{ pendingAction.payload.to }}</strong>
            <span class="email-edit-hint">
              <PencilIcon class="pencil-icon" /> Modifiable avant envoi
            </span>
          </div>
          <textarea
            v-model="editableEmailBody"
            class="email-preview-body email-editable"
            rows="10"
            placeholder="Corps de l'email..."
          />
        </div> -->

      </div>
    </transition>

    <!-- ── Section Notes RH (pour ACE) ─────────────────────────────────────── -->
    <div class="rh-notes-section">
      <div class="rh-notes-title">
        <ClipboardListIcon class="rh-notes-icon" />
        Vos notes RH
        <span class="rh-notes-hint">— ACE apprend de vos critères</span>
      </div>

      <!-- Notes ajoutées -->
      <div v-if="rhNotes.length" class="rh-notes-list">
        <div v-for="(note, i) in rhNotes" :key="i"
             class="rh-note-item" :class="note.sign === '+' ? 'note-plus' : 'note-minus'">
          <span class="note-sign" :class="note.sign === '+' ? 'sign-plus' : 'sign-minus'">
            {{ note.sign }}
          </span>
          <span class="note-text">{{ note.text }}</span>
          <button class="note-remove" @click="removeNote(i)">×</button>
        </div>
      </div>
      <div v-else class="rh-notes-empty">Aucune note ajoutée — les notes aident ACE à apprendre</div>

      <!-- Champ d'ajout -->
      <div class="note-input-row">
        <div class="sign-toggle">
          <button :class="['sign-btn', newNote.sign === '+' ? 'sign-btn-plus' : '']"
                  @click="newNote.sign = '+'" title="Point positif">+</button>
          <button :class="['sign-btn', newNote.sign === '-' ? 'sign-btn-minus' : '']"
                  @click="newNote.sign = '-'" title="Point négatif">−</button>
        </div>
        <input v-model="newNote.text" class="note-input"
               :placeholder="newNote.sign === '+'
                 ? 'Ex: Maîtrise FreeRTOS confirmée en production'
                 : 'Ex: Aucune expérience DO-178C'"
               @keyup.enter="addNote"
               maxlength="200" />
        <button class="add-note-btn" @click="addNote" :disabled="!newNote.text.trim()">
          Ajouter
        </button>
      </div>
    </div>

    <!-- ── Actions RH ────────────────────────────────────────────────────────── -->
    <div class="banner-actions">

      <!-- CAS 1 : Recommandation = Entretien
           Action principale = planifier l'entretien ET envoyer l'invitation Calendar.
           Les boutons secondaires permettent de changer la décision. -->
      <template v-if="reco === 'Entretien'">
        <button class="action-validate action-validate--interview"
                :disabled="loading" @click="handleScheduleInterview">
          <LoaderIcon v-if="loading" class="btn-icon-spin" />
          <CalendarIcon v-else class="btn-icon-action" />
          <span>{{ loading ? 'Planification...' : 'Planifier l\'entretien + Envoyer l\'invitation' }}</span>
        </button>
        <div class="actions-sep"></div>
        <button class="action-btn action-waitlist"
                :disabled="loading" @click="handleDirectAction('ListeAttente')">
          <BookmarkIcon class="btn-icon-action" />
          Liste d'attente
        </button>
        <button class="action-btn action-refuse"
                :disabled="loading" @click="handleDirectAction('Refuse')">
          <XCircleIcon class="btn-icon-action" />
          Refuser
        </button>
        <button class="action-reject" :disabled="loading" @click="rejectEmail">
          <XCircleIcon class="btn-icon-action" />
          Ignorer
        </button>
      </template>

      <!-- CAS 2 : Recommandation = ListeAttente ou Refus
           Action principale = confirmer et envoyer l'email de score.
           Boutons secondaires pour changer la décision. -->
      <template v-else>
        <button v-if="reco !== 'Entretien'" class="action-btn action-schedule"
                :disabled="loading" @click="handleDirectAction('Entretien')">
          <CalendarIcon class="btn-icon-action" />
          Planifier entretien
        </button>
        <button class="action-btn action-waitlist"
                :disabled="loading" @click="handleDirectAction('ListeAttente')">
          <BookmarkIcon class="btn-icon-action" />
          Liste d'attente
        </button>
        <button class="action-btn action-refuse"
                :disabled="loading" @click="handleDirectAction('Refuse')">
          <XCircleIcon class="btn-icon-action" />
          Refuser
        </button>
        <div class="actions-sep"></div>
        <button class="action-validate" :disabled="loading" @click="validateEmail">
          <LoaderIcon v-if="loading" class="btn-icon-spin" />
          <SendIcon v-else class="btn-icon-action" />
          <span>{{ loading ? 'Envoi...' : 'Confirmer — Envoyer l\'email' }}</span>
        </button>
        <button class="action-reject" :disabled="loading" @click="rejectEmail">
          <XCircleIcon class="btn-icon-action" />
          Rejeter
        </button>
      </template>

    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { toast } from 'vue3-toastify'
import {
  CheckCircleIcon, AlertTriangleIcon, XCircleIcon,
  CalendarIcon, MailIcon, SendIcon, LoaderIcon,
  ChevronUpIcon, ChevronDownIcon, ExternalLinkIcon,
  UserIcon, BriefcaseIcon, SparklesIcon, ClockIcon,
  BookmarkIcon, PencilIcon,
} from 'lucide-vue-next'

// ClipboardListIcon n'est pas dans lucide-vue-next par défaut, on le définit inline
const ClipboardListIcon = {
  template: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
    <path d="M8 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2h-2"/>
    <path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>
  </svg>`,
}

const props = defineProps({
  documentId: { type: [Number, String], required: true },
})

const emit = defineEmits(['validated', 'rejected', 'has-pending'])

const AI_BASE = import.meta.env.VITE_AI_BACKEND_URL || 'http://localhost:8000'

const pendingAction = ref(null)
const showDetails   = ref(true)
const loading       = ref(false)
let   pollInterval  = null

// ── Notes RH ─────────────────────────────────────────────────────────────────
const rhNotes  = ref([])
const newNote  = ref({ sign: '+', text: '' })

function addNote() {
  if (!newNote.value.text.trim()) return
  rhNotes.value.push({ sign: newNote.value.sign, text: newNote.value.text.trim() })
  newNote.value.text = ''
}

function removeNote(i) {
  rhNotes.value.splice(i, 1)
}

// ── Suggestion ACE extraite du payload ───────────────────────────────────────
const aceSuggestion = computed(() =>
  pendingAction.value?.payload?.ace_suggestion || null
)

// ── Notifier le parent dès que l'état de la pendingAction change ──────────────
watch(pendingAction, (val) => {
  emit('has-pending', !!val)
}, { immediate: true })

// ── Mounting / polling ────────────────────────────────────────────────────────
// Polling CONTINU toutes les 4s : détecte l'arrivée ET la disparition
// de la pending_action (ex: backend redémarré → STM vidée).
onMounted(() => {
  loadPendingAction()
  pollInterval = setInterval(loadPendingAction, 4000)
})
onUnmounted(() => { if (pollInterval) clearInterval(pollInterval) })

watch(() => props.documentId, () => {
  pendingAction.value     = null
  editableEmailBody.value = ''
  rhNotes.value           = []
  _restoreAttempted       = false
  loadPendingAction()
})

const loadPendingAction = async () => {
  try {
    const res     = await fetch(`${AI_BASE}/pending-actions`)
    const data    = await res.json()
    const actions = data.actions || []
    const found   = actions.find(a =>
      a.action_type === 'send_score_email' &&
      String(a.payload?.document_id) === String(props.documentId) &&
      a.status === 'pending'
    )

    if (found) {
      pendingAction.value = found
      return
    }

    // Aucune pending_action trouvée.
    // Si la STM a été vidée (reload backend) mais que le candidat est encore
    // en ATraiter, tenter de restaurer la pending_action depuis la DB .NET.
    if (!_restoreAttempted) {
      _restoreAttempted = true
      await _tryRestorePending()
    } else {
      pendingAction.value = null
    }
  } catch {
    pendingAction.value = null
  }
}

// Flag pour n'essayer la restauration qu'une seule fois par montage
let _restoreAttempted = false

const _tryRestorePending = async () => {
  try {
    const res  = await fetch(
      `${AI_BASE}/recruitment/restore-pending/${props.documentId}`,
      { method: 'POST' }
    )
    const data = await res.json()
    if (data.restored) {
      // La pending_action a été recréée en STM → la recharger
      const res2  = await fetch(`${AI_BASE}/pending-actions`)
      const data2 = await res2.json()
      const found = (data2.actions || []).find(a =>
        a.action_type === 'send_score_email' &&
        String(a.payload?.document_id) === String(props.documentId) &&
        a.status === 'pending'
      )
      pendingAction.value = found || null
    } else {
      // Pas de restauration possible (candidat déjà traité, pas d'email, etc.)
      pendingAction.value = null
    }
  } catch {
    pendingAction.value = null
  }
}

// ── Computed visuels ──────────────────────────────────────────────────────────
const reco = computed(() => pendingAction.value?.payload?.recommendation)

const bannerClass = computed(() => ({
  'banner-green': reco.value === 'Entretien',
  'banner-amber': reco.value === 'ListeAttente',
  'banner-red':   ['Refus', 'Refuse'].includes(reco.value),
}))
const circleClass = computed(() => ({
  'circle-green': reco.value === 'Entretien',
  'circle-amber': reco.value === 'ListeAttente',
  'circle-red':   ['Refus', 'Refuse'].includes(reco.value),
}))
const chipClass = computed(() => ({
  'chip-green': reco.value === 'Entretien',
  'chip-amber': reco.value === 'ListeAttente',
  'chip-red':   ['Refus', 'Refuse'].includes(reco.value),
}))
const recoIcon = computed(() => {
  if (reco.value === 'Entretien')    return CalendarIcon
  if (reco.value === 'ListeAttente') return ClockIcon
  return XCircleIcon
})
const recoLabel = computed(() => {
  if (reco.value === 'Entretien')    return 'Candidature recommandée pour un entretien'
  if (reco.value === 'ListeAttente') return "Profil intéressant — liste d'attente"
  return 'Profil ne correspond pas au poste'
})

// ── Computed ACE ──────────────────────────────────────────────────────────────
const aceSectionClass = computed(() => {
  const phase = aceSuggestion.value?.phase
  if (phase === 1) return 'ace-observe'
  if (phase === 2) return 'ace-suggest'
  if (phase === 3) return 'ace-suggest-strong'
  if (phase === 4) return 'ace-auto'
  return 'ace-observe'
})
const acePhaseBadgeClass = computed(() => {
  const phase = aceSuggestion.value?.phase
  if (phase === 1) return 'badge-phase-1'
  if (phase === 2) return 'badge-phase-2'
  if (phase === 3) return 'badge-phase-3'
  if (phase === 4) return 'badge-phase-4'
  return 'badge-phase-1'
})

// ── Brouillon email éditable ──────────────────────────────────────────────────
// editableEmailBody est un ref mutable — le RH peut modifier le texte.
// C'est CE texte (potentiellement modifié) qui est envoyé au candidat,
// jamais une re-génération LLM au moment de la confirmation.
const editableEmailBody = ref('')

// Initialiser le brouillon dès qu'une pendingAction arrive (ou change)
watch(pendingAction, (action) => {
  if (!action) { editableEmailBody.value = ''; return }
  const p = action.payload

  // Priorité 1 : corps pré-généré par l'orchestrateur (body_sent dans le payload)
  if (p.body_sent && p.body_sent.trim()) {
    editableEmailBody.value = _cleanEmailBody(p.body_sent, p)
    return
  }

  // Priorité 2 : corps minimal non-trompeur si body_sent absent
  // (ancienne pending_action avant le fix orchestrateur)
  const name = (p.candidate_name || '').split(' ')[0] || 'Candidat'
  const rec  = p.recommendation || ''
  if (rec === 'Entretien') {
    editableEmailBody.value = (
      `Bonjour ${name},\n\n` +
      `Nous avons le plaisir de vous convier à un entretien pour le poste de ${p.position}.\n\n` +
      (p.slot_formatted ? `📅 ${p.slot_formatted}\n` : '') +
      `Merci de confirmer votre présence en répondant à cet email.\n\n` +
      `Cordialement,\nAeroTech RH`
    )
  } else if (rec === 'ListeAttente') {
    editableEmailBody.value = (
      `Bonjour ${name},\n\n` +
      `Votre candidature au poste de ${p.position} a retenu notre attention.\n` +
      `Nous n'avons pas de poste disponible actuellement, mais nous conservons ` +
      `votre dossier dans notre vivier.\n\n` +
      `Cordialement,\nAeroTech RH`
    )
  } else {
    editableEmailBody.value = (
      `Bonjour ${name},\n\n` +
      `Nous vous remercions d'avoir postulé au poste de ${p.position}.\n` +
      `Après examen de votre dossier, nous ne sommes pas en mesure de donner ` +
      `suite à votre candidature à ce stade.\n\n` +
      `Cordialement,\nAeroTech RH`
    )
  }
}, { immediate: true })

/**
 * Nettoie le corps de l'email généré par le LLM :
 * - Supprime les liens Meet si aucun créneau n'a encore été créé
 * - Supprime les artefacts de liste ("de 1,", "de 2,")
 * - Supprime les placeholders entre crochets résiduels
 */
function _cleanEmailBody(body, payload) {
  let cleaned = body

  // Supprimer les liens Meet/Calendar si pas de créneau planifié
  const hasMeet = payload?.meet_link?.trim()
  const hasSlot = payload?.slot_formatted?.trim()
  if (!hasMeet) {
    // Supprimer toute ligne contenant un lien meet.google.com
    cleaned = cleaned.replace(/.*meet\.google\.com\S*\n?/gi, '')
  }
  if (!hasSlot && !hasMeet) {
    // Supprimer toute ligne contenant calendar.google.com
    cleaned = cleaned.replace(/.*calendar\.google\.com\S*\n?/gi, '')
    // Supprimer les lignes "📅 ..." ou "Créneau : ..."
    cleaned = cleaned.replace(/.*📅.*\n?/g, '')
    cleaned = cleaned.replace(/(Créneau|Creneau)\s*:.*\n?/gi, '')
  }

  // Supprimer les artefacts de liste LLM : "de 1,", "• 1.", "- 1,", "1. "
  cleaned = cleaned.replace(/\b(de\s+\d+\s*[,.]?\s*)/gi, '')
  cleaned = cleaned.replace(/^\s*[-•]\s*\d+\s*[,.]?\s*/gm, '• ')

  // Supprimer les placeholders résiduels entre crochets
  cleaned = cleaned.replace(/\[[^\]]{1,60}\]/g, '')

  // Nettoyer les lignes vides multiples
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')

  return cleaned.trim()
}

// ── Actions ───────────────────────────────────────────────────────────────────

// Construire la payload des notes pour l'API
const _buildNotesPayload = () => ({
  notes:    rhNotes.value.map(n => `${n.sign} ${n.text}`).join('\n'),
  rh_notes: rhNotes.value,
})

/**
 * Action directe RH : planifier / liste d'attente / refuser
 * sans passer par la pending_action email — appel direct aux endpoints.
 */
const handleDirectAction = async (action) => {
  if (!pendingAction.value || loading.value) return
  const cid = pendingAction.value.payload?.candidate_id
  const did = props.documentId
  if (!cid) { toast.error('candidate_id manquant'); return }

  loading.value = true
  if (pollInterval) clearInterval(pollInterval)

  try {
    const { notes, rh_notes } = _buildNotesPayload()

    let url, body
    if (action === 'Entretien') {
      url  = `${AI_BASE}/recruitment/schedule-interview`
      body = { candidate_id: cid, document_id: String(did), notes, rh_notes }
    } else if (action === 'ListeAttente') {
      // Mise à jour statut directe via simple-refusal n'existe pas pour ListeAttente
      // → on passe par update_candidate_status via l'endpoint recruitment/decision
      // Pour l'instant on utilise le endpoint decision avec un statut ListeAttente
      // Si pas disponible, on peut utiliser simple-refusal avec statut override
      url  = `${AI_BASE}/recruitment/schedule-interview` // fallback : on override via notes
      // En réalité on veut juste changer le statut → appel direct MiniGED
      // On passe par un confirm-action modifié :
      const res2 = await fetch(`${AI_BASE}/confirm-action`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          action_id: pendingAction.value.action_id,
          confirmed: true,
          payload_override: { recommendation: 'ListeAttente' },
        }),
      })
      const d2 = await res2.json()
      toast.success('Candidat mis en liste d\'attente')
      pendingAction.value = null
      rhNotes.value       = []
      emit('validated', d2)
      return
    } else {
      url  = `${AI_BASE}/recruitment/simple-refusal`
      body = { candidate_id: cid, document_id: String(did), notes, rh_notes }
    }

    const res  = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
    const data = await res.json()

    if (data.success !== false) {
      const labels = { Entretien: 'Entretien planifié', Refuse: 'Candidat refusé' }
      const emailMsg = data.email_sent ? ` · Email envoyé` : ''
      toast.success(`${labels[action] || action}${emailMsg}`)
      pendingAction.value = null
      rhNotes.value       = []
      emit('validated', data)
    } else {
      toast.error(`Erreur : ${data.error || 'inconnue'}`)
    }
  } catch (e) {
    toast.error(`Erreur : ${e.message}`)
  } finally {
    loading.value = false
    // Redémarrer le polling dans tous les cas
    if (!pollInterval) pollInterval = setInterval(loadPendingAction, 4000)
  }
}

/**
 * Planifie l'entretien quand la recommandation IA est "Entretien" :
 * 1. Appelle /recruitment/schedule-interview → crée l'event Calendar + envoie l'invitation
 * 2. Rejette la pending_action d'email de score (plus nécessaire)
 * 3. Ferme la bannière → CandidateStatusBadge prend le relais
 */
const handleScheduleInterview = async () => {
  if (!pendingAction.value || loading.value) return
  const cid = pendingAction.value.payload?.candidate_id
  const did = props.documentId
  if (!cid) { toast.error('candidate_id manquant'); return }

  loading.value = true
  if (pollInterval) clearInterval(pollInterval)

  try {
    const { notes, rh_notes } = _buildNotesPayload()

    // 1. Planifier l'entretien (Calendar + email convocation via orchestrateur)
    const res  = await fetch(`${AI_BASE}/recruitment/schedule-interview`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        candidate_id: cid,
        document_id:  String(did),
        notes,
        rh_notes,
      }),
    })
    const data = await res.json()

    if (data.success !== false) {
      // 2. Rejeter la pending_action d'email de score (devenue inutile)
      if (pendingAction.value) {
        await fetch(`${AI_BASE}/confirm-action`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({
            action_id: pendingAction.value.action_id,
            confirmed: false,
          }),
        }).catch(() => {})
      }

      const slotMsg  = data.slot_formatted ? ` · ${data.slot_formatted}` : ''
      const emailMsg = data.email_sent     ? ' · Invitation envoyée' : ''
      toast.success(`Entretien planifié${slotMsg}${emailMsg}`)

      pendingAction.value     = null
      editableEmailBody.value = ''
      rhNotes.value           = []
      emit('validated', data)
    } else {
      toast.error(`Erreur : ${data.error || 'inconnue'}`)
    }
  } catch (e) {
    toast.error(`Erreur réseau : ${e.message}`)
  } finally {
    loading.value = false
    pollInterval  = setInterval(loadPendingAction, 4000)
  }
}

const validateEmail = async () => {
  if (!pendingAction.value || loading.value) return
  loading.value = true
  if (pollInterval) clearInterval(pollInterval)

  const _doConfirm = async (action) => {
    const { notes, rh_notes } = _buildNotesPayload()
    return await fetch(`${AI_BASE}/confirm-action`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        action_id:        action.action_id,
        confirmed:        true,
        payload_override: {
          notes,
          rh_notes,
          body:    editableEmailBody.value,
          subject: action.payload?.subject_sent || '',
        },
      }),
    })
  }

  try {
    let res  = await _doConfirm(pendingAction.value)
    let data = await res.json()

    // Si l'action est introuvable (backend redémarré → STM vidée),
    // recharger les actions et réessayer une seule fois.
    if (data.error?.includes('introuvable')) {
      await loadPendingAction()
      if (!pendingAction.value) {
        toast.warning(
          "La session backend a été réinitialisée. " +
          "L'email sera envoyé lors de la prochaine analyse.",
          { autoClose: 5000 }
        )
        loading.value = false
        pollInterval  = setInterval(loadPendingAction, 4000)
        return
      }
      res  = await _doConfirm(pendingAction.value)
      data = await res.json()
    }

    if (data.success || data.action_id) {
      const dest = pendingAction.value.payload.to
      toast.success(`Email envoyé à ${dest}`, { autoClose: 3000 })
      pendingAction.value     = null
      editableEmailBody.value = ''
      rhNotes.value           = []
      emit('validated', data)
    } else {
      toast.error(`Erreur : ${data.error || 'inconnu'}`, { autoClose: 4000 })
    }
  } catch (e) {
    toast.error(`Erreur réseau : ${e.message}`, { autoClose: 4000 })
  } finally {
    loading.value = false
    if (!pendingAction.value) {
      pollInterval = setInterval(loadPendingAction, 4000)
    }
  }
}

const rejectEmail = async () => {
  if (!pendingAction.value || loading.value) return
  loading.value = true
  if (pollInterval) clearInterval(pollInterval)
  try {
    await fetch(`${AI_BASE}/confirm-action`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ action_id: pendingAction.value.action_id, confirmed: false }),
    })
    toast.info('Email annulé', { autoClose: 2000 })
    pendingAction.value     = null
    editableEmailBody.value = ''
    emit('rejected')
  } finally {
    loading.value = false
    pollInterval  = setInterval(loadPendingAction, 4000)
  }
}
</script>

<style scoped>
/* ── Base ─────────────────────────────────────────────────────────────────── */
.score-banner {
  border-radius: 14px; border: 1px solid;
  padding: 16px; margin: 12px 0;
  display: flex; flex-direction: column; gap: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.banner-green { border-color: #bbf7d0; background: #f0fdf4; }
.banner-amber { border-color: #fde68a; background: #fffbeb; }
.banner-red   { border-color: #fecaca; background: #fef2f2; }

/* ── En-tête ──────────────────────────────────────────────────────────────── */
.banner-header { display: flex; align-items: center; gap: 12px; }

.score-circle {
  flex-shrink: 0; width: 54px; height: 54px; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  border: 2px solid; line-height: 1;
}
.circle-green { border-color: #22c55e; background: #dcfce7; }
.circle-amber { border-color: #f59e0b; background: #fef3c7; }
.circle-red   { border-color: #ef4444; background: #fee2e2; }
.score-value  { font-size: 17px; font-weight: 800; color: #111827; }
.score-max    { font-size: 9px; color: #6b7280; font-weight: 500; }

.banner-info { flex: 1; min-width: 0; }
.banner-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: #111827; flex-wrap: wrap; }
.reco-icon    { width: 15px; height: 15px; flex-shrink: 0; color: #6b7280; }
.reco-chip    { padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.chip-green { background: #dcfce7; color: #15803d; }
.chip-amber { background: #fef3c7; color: #b45309; }
.chip-red   { background: #fee2e2; color: #b91c1c; }
.banner-sub { display: flex; align-items: center; gap: 5px; font-size: 12px; color: #6b7280; margin-top: 4px; flex-wrap: wrap; }
.meta-icon  { width: 12px; height: 12px; flex-shrink: 0; }
.sep        { color: #d1d5db; }
.toggle-btn {
  flex-shrink: 0; width: 28px; height: 28px;
  border: 1px solid #e5e7eb; border-radius: 6px;
  background: white; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: #6b7280; transition: all 0.15s;
}
.toggle-btn:hover { background: #f9fafb; border-color: #d1d5db; color: #374151; }
.btn-icon-sm { width: 14px; height: 14px; }

/* ── Section ACE ──────────────────────────────────────────────────────────── */
.ace-section {
  border-radius: 10px; padding: 12px 14px;
  display: flex; flex-direction: column; gap: 8px;
  border: 1px solid;
}
.ace-observe       { background: #f8fafc; border-color: #e2e8f0; }
.ace-suggest       { background: #eff6ff; border-color: #bfdbfe; }
.ace-suggest-strong { background: #f5f3ff; border-color: #ddd6fe; }
.ace-auto          { background: #f0fdf4; border-color: #bbf7d0; }

.ace-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ace-phase-badge {
  padding: 2px 10px; border-radius: 20px;
  font-size: 10px; font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase;
}
.badge-phase-1 { background: #f1f5f9; color: #475569; }
.badge-phase-2 { background: #dbeafe; color: #1d4ed8; }
.badge-phase-3 { background: #ede9fe; color: #7c3aed; }
.badge-phase-4 { background: #dcfce7; color: #15803d; }

.ace-confidence { font-size: 11px; font-weight: 700; color: #475569; }
.ace-overrides  { font-size: 11px; color: #94a3b8; }
.ace-message    { font-size: 12.5px; color: #374151; line-height: 1.5; margin: 0; }
.ace-validation-required { font-size: 11.5px; color: #b45309; font-weight: 600; margin: 0; }

/* Justifications */
.ace-justifications { display: flex; flex-direction: column; gap: 5px; margin-top: 4px; }
.ace-just-title { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
.ace-just-item {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 10px; border-radius: 7px; font-size: 12px;
}
.just-plus  { background: #f0fdf4; border: 1px solid #bbf7d0; }
.just-minus { background: #fef2f2; border: 1px solid #fecaca; }
.just-info  { background: #f8fafc; border: 1px solid #e2e8f0; }
.just-sign {
  width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 11px; flex-shrink: 0;
}
.just-plus  .just-sign { background: #dcfce7; color: #16a34a; }
.just-minus .just-sign { background: #fee2e2; color: #dc2626; }
.just-info  .just-sign { background: #f1f5f9; color: #475569; }
.just-text    { flex: 1; color: #374151; line-height: 1.4; }
.just-helpful { font-size: 10px; color: #9ca3af; font-style: italic; white-space: nowrap; }

/* ── Détails ──────────────────────────────────────────────────────────────── */
.banner-details { display: flex; flex-direction: column; gap: 10px; }

.score-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.score-col  { border-radius: 8px; padding: 10px 12px; font-size: 12px; }
.score-col.strengths { background: #f0fdf4; border: 1px solid #bbf7d0; }
.score-col.gaps      { background: #fff7ed; border: 1px solid #fed7aa; }
.col-title  { display: flex; align-items: center; gap: 5px; font-weight: 700; font-size: 11px; margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.04em; color: #374151; }
.col-icon   { width: 13px; height: 13px; flex-shrink: 0; }
.strengths-icon { color: #16a34a; }
.gaps-icon      { color: #ea580c; }
.score-col ul { margin: 0; padding-left: 14px; color: #4b5563; line-height: 1.6; }
.score-col li { margin-bottom: 2px; }

.summary-block { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: #374151; line-height: 1.6; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; }
.summary-icon  { width: 14px; height: 14px; flex-shrink: 0; color: #6366f1; margin-top: 1px; }

.slot-block { display: flex; align-items: center; gap: 10px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 10px 12px; font-size: 12px; }
.slot-icon  { width: 16px; height: 16px; color: #2563eb; flex-shrink: 0; }
.slot-content { flex: 1; }
.slot-label { display: block; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: #3b82f6; }
.slot-value { color: #1e3a5f; font-weight: 500; }
.cal-link { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; color: #2563eb; text-decoration: none; padding: 4px 10px; background: white; border: 1px solid #bfdbfe; border-radius: 6px; white-space: nowrap; flex-shrink: 0; transition: all 0.15s; }
.cal-link:hover { background: #dbeafe; }
.link-icon { width: 11px; height: 11px; }

.email-preview { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; font-size: 12px; }
.email-preview-header { display: flex; align-items: center; gap: 6px; background: #f8fafc; padding: 8px 12px; border-bottom: 1px solid #e5e7eb; color: #374151; flex-wrap: wrap; }
.mail-icon { width: 13px; height: 13px; color: #6b7280; flex-shrink: 0; }
.email-to  { color: #111827; margin-left: 2px; }
.email-edit-hint { display: flex; align-items: center; gap: 3px; font-size: 10px; color: #9ca3af; font-style: italic; margin-left: auto; }
.pencil-icon { width: 11px; height: 11px; }
.email-preview-body {
  padding: 10px 12px; color: #4b5563; line-height: 1.6;
  white-space: pre-wrap; max-height: 130px; overflow-y: auto; background: white;
}
.email-editable {
  width: 100%; box-sizing: border-box;
  padding: 10px 12px; color: #1f2937; line-height: 1.65;
  font-family: inherit; font-size: 12.5px;
  border: none; outline: none; resize: vertical;
  background: white; min-height: 160px; max-height: 320px;
  transition: background 0.15s;
}
.email-editable:focus { background: #fafff4; }
.email-editable::placeholder { color: #d1d5db; }

/* ── Section Notes RH ─────────────────────────────────────────────────────── */
.rh-notes-section {
  background: #fafafa; border: 1px dashed #e2e8f0;
  border-radius: 10px; padding: 12px 14px;
  display: flex; flex-direction: column; gap: 8px;
}
.rh-notes-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 700; color: #374151;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.rh-notes-icon { color: #9ca3af; }
.rh-notes-hint { font-size: 10px; color: #a78bfa; font-style: italic; text-transform: none; letter-spacing: 0; font-weight: 400; }

.rh-notes-empty { font-size: 12px; color: #9ca3af; font-style: italic; padding: 4px 0; }
.rh-notes-list  { display: flex; flex-direction: column; gap: 5px; }
.rh-note-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: 8px; font-size: 12px;
}
.note-plus  { background: #f0fdf4; border: 1px solid #bbf7d0; }
.note-minus { background: #fef2f2; border: 1px solid #fecaca; }
.note-sign {
  width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 11px; flex-shrink: 0;
}
.sign-plus  { background: #dcfce7; color: #16a34a; }
.sign-minus { background: #fee2e2; color: #dc2626; }
.note-text   { flex: 1; color: #374151; }
.note-remove {
  width: 20px; height: 20px; border-radius: 4px; border: none;
  background: transparent; cursor: pointer; color: #9ca3af;
  font-size: 14px; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.note-remove:hover { background: rgba(0,0,0,0.06); color: #dc2626; }

/* Champ d'ajout de note */
.note-input-row { display: flex; gap: 6px; align-items: center; }
.sign-toggle {
  display: flex; border-radius: 6px; overflow: hidden;
  border: 1px solid #e5e7eb; flex-shrink: 0;
}
.sign-btn {
  width: 32px; height: 32px; border: none; font-size: 15px; font-weight: 800;
  cursor: pointer; background: #f9fafb; color: #9ca3af; transition: all 0.15s;
  display: flex; align-items: center; justify-content: center;
}
.sign-btn:first-child { border-right: 1px solid #e5e7eb; }
.sign-btn-plus  { background: #dcfce7 !important; color: #16a34a !important; }
.sign-btn-minus { background: #fee2e2 !important; color: #dc2626 !important; }
.note-input {
  flex: 1; height: 32px; border: 1px solid #e5e7eb; border-radius: 6px;
  padding: 0 10px; font-size: 12px; color: #111827;
  outline: none; transition: border-color 0.15s;
}
.note-input:focus { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.1); }
.note-input::placeholder { color: #d1d5db; }
.add-note-btn {
  padding: 0 12px; height: 32px; border-radius: 6px;
  background: #6366f1; color: white; border: none;
  font-size: 12px; font-weight: 600; cursor: pointer;
  white-space: nowrap; transition: all 0.15s; flex-shrink: 0;
}
.add-note-btn:hover:not(:disabled) { background: #4f46e5; }
.add-note-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Actions ──────────────────────────────────────────────────────────────── */
.banner-actions {
  display: flex; gap: 8px; flex-wrap: wrap;
  padding-top: 6px; border-top: 1px solid rgba(0,0,0,0.06);
  align-items: center;
}
.actions-sep { flex: 1; }

.action-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 13px; border-radius: 8px;
  font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all 0.15s; border: 1px solid;
}
.action-schedule {
  background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe;
}
.action-schedule:hover:not(:disabled) { background: #dbeafe; }
.action-waitlist {
  background: #fefce8; color: #854d0e; border-color: #fde68a;
}
.action-waitlist:hover:not(:disabled) { background: #fef9c3; }
.action-refuse {
  background: #fef2f2; color: #b91c1c; border-color: #fecaca;
}
.action-refuse:hover:not(:disabled) { background: #fee2e2; }

.action-validate {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 18px; background: #4f46e5; color: white;
  border: none; border-radius: 8px;
  font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.action-validate:hover:not(:disabled) { background: #4338ca; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,70,229,0.3); }
.action-validate--interview { background: #7c3aed; }
.action-validate--interview:hover:not(:disabled) { background: #6d28d9; box-shadow: 0 4px 12px rgba(124,58,237,0.3); }

.action-reject {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 14px; background: white; color: #6b7280;
  border: 1px solid #e5e7eb; border-radius: 8px;
  font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s;
}
.action-reject:hover:not(:disabled) { background: #fef2f2; color: #dc2626; border-color: #fca5a5; }

button:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; box-shadow: none !important; }
.btn-icon-action { width: 14px; height: 14px; flex-shrink: 0; }
.btn-icon-spin   { width: 14px; height: 14px; flex-shrink: 0; animation: spin 1s linear infinite; }

/* ── Transitions ──────────────────────────────────────────────────────────── */
.slide-down-enter-active { transition: all 0.25s ease; }
.slide-down-leave-active { transition: all 0.2s ease; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; transform: translateY(-6px); }

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>