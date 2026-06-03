<template>
  <!-- Badge compact -->
  <span v-if="compact" :class="['status-badge', statusConfig.class]">
    <span class="badge-dot"></span>
    {{ statusConfig.label }}
  </span>

  <!-- Carte complète -->
  <div v-else class="candidate-status-card">

    <!-- En-tête -->
    <div class="status-header">
      <div class="status-icon-wrap" :style="{ background: statusConfig.bg }">
        <component :is="statusConfig.icon" class="status-svg-icon" :style="{ color: statusConfig.iconColor }" />
      </div>
      <div class="status-info">
        <div class="status-label">{{ statusConfig.label }}</div>
        <div class="status-sub">{{ statusConfig.description }}</div>
      </div>
      <div :class="['status-chip', statusConfig.class]">
        {{ statusConfig.label }}
      </div>
    </div>

    <!-- Timeline -->
    <div class="timeline">
      <div v-for="(step, index) in timeline" :key="step.key"
           :class="['timeline-step', getStepState(step.key)]">
        <div class="step-connector" v-if="index > 0"></div>
        <div class="step-dot">
          <CheckIcon v-if="getStepState(step.key) === 'done'" class="dot-check" />
          <span v-else-if="getStepState(step.key) === 'current'" class="dot-pulse"></span>
          <span v-else class="dot-empty"></span>
        </div>
        <div class="step-label">{{ step.label }}</div>
      </div>
    </div>

      <!-- Notes affichées avec badge +/- si format structuré
      <div v-if="notes" class="status-notes">
        <div class="notes-header">
          <ClipboardIcon class="notes-icon" />
          Notes RH
        </div>
        <div class="notes-body">
          <template v-if="parsedNotes.length">
            <div v-for="(n, i) in parsedNotes" :key="i"
                :class="['note-line', n.sign === '+' ? 'note-positive' : n.sign === '-' ? 'note-negative' : 'note-free']">
              <span v-if="n.sign" :class="['note-sign-badge', n.sign === '+' ? 'sign-plus' : 'sign-minus']">
                {{ n.sign }}
              </span>
              <span class="note-text">{{ n.text }}</span>
            </div>
          </template>
          <span v-else class="note-plain">{{ notes }}</span>
        </div>
      </div> -->

    <!-- Actions RH -->
    <div class="status-actions" v-if="showActions && availableActions.length">
      <div class="actions-label">Actions RH</div>
      <div class="actions-row">
        <button
          v-for="action in availableActions"
          :key="action.value"
          :class="['action-btn', action.variant]"
          @click="openNotesModal(action)"
          :disabled="loading"
          :title="action.tooltip"
        >
          <component :is="action.icon" class="action-icon" />
          {{ action.label }}
        </button>
      </div>
    </div>

  </div>

  <!-- ═══════════════════════════════════════════════════════════════════════
       MODAL NOTES RH
       ═══════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="showModal" class="modal-overlay" @click.self="cancelModal">
        <div class="modal-card">

          <!-- Header modal -->
          <div class="modal-header" :style="{ borderColor: pendingAction?.color }">
            <div class="modal-header-left">
              <div class="modal-action-icon" :style="{ background: pendingAction?.iconBg }">
                <component :is="pendingAction?.icon" class="modal-icon"
                           :style="{ color: pendingAction?.color }" />
              </div>
              <div>
                <div class="modal-title">{{ pendingAction?.label }}</div>
                <div class="modal-subtitle">
                  Ajoutez des notes pour justifier votre décision
                  <span class="modal-subtitle-hint">— ACE apprend de vos critères</span>
                </div>
              </div>
            </div>
            <button class="modal-close" @click="cancelModal">
              <XIcon class="close-icon" />
            </button>
          </div>

          <!-- Corps modal -->
          <div class="modal-body">

            <!-- Explication ACE -->
            <div class="ace-info-banner">
              <div class="ace-info-icon">🧠</div>
              <div class="ace-info-text">
                <strong>ACE apprend de vos notes.</strong>
                Utilisez <span class="sign-badge-inline plus">+</span> pour les points forts
                et <span class="sign-badge-inline minus">−</span> pour les points faibles.
                Plus vos notes sont précises, plus ACE sera autonome rapidement.
              </div>
            </div>

            <!-- Champ d'ajout de note -->
            <div class="note-input-section">
              <div class="note-input-label">Ajouter une note</div>
              <div class="note-input-row">
                <div class="sign-toggle">
                  <button
                    :class="['sign-btn', newNote.sign === '+' ? 'sign-btn-active-plus' : '']"
                    @click="newNote.sign = '+'"
                    title="Avantage / Point positif"
                  >+</button>
                  <button
                    :class="['sign-btn', newNote.sign === '-' ? 'sign-btn-active-minus' : '']"
                    @click="newNote.sign = '-'"
                    title="Inconvénient / Point négatif"
                  >−</button>
                </div>
                <input
                  ref="noteInputRef"
                  v-model="newNote.text"
                  class="note-input"
                  :placeholder="newNote.sign === '+'
                    ? 'Ex: Maîtrise FreeRTOS confirmée en production'
                    : 'Ex: Aucune expérience DO-178C'"
                  @keyup.enter="addNote"
                  maxlength="200"
                />
                <button class="add-note-btn" @click="addNote" :disabled="!newNote.text.trim()">
                  <PlusIcon class="add-icon" />
                  Ajouter
                </button>
              </div>
            </div>

            <!-- Liste des notes ajoutées -->
            <div v-if="rhNotes.length" class="notes-added">
              <div class="notes-added-label">
                Notes ajoutées
                <span class="notes-count">{{ rhNotes.length }}</span>
              </div>
              <TransitionGroup name="note-list" tag="div" class="notes-list">
                <div
                  v-for="(note, i) in rhNotes"
                  :key="i"
                  :class="['note-item', note.sign === '+' ? 'note-item-plus' : 'note-item-minus']"
                >
                  <span :class="['note-item-sign', note.sign === '+' ? 'sign-plus' : 'sign-minus']">
                    {{ note.sign }}
                  </span>
                  <span class="note-item-text">{{ note.text }}</span>
                  <button class="note-remove" @click="removeNote(i)" title="Supprimer">
                    <XIcon class="remove-icon" />
                  </button>
                </div>
              </TransitionGroup>
            </div>

            <!-- Placeholder si aucune note -->
            <div v-else class="notes-empty">
              <MessageSquareIcon class="empty-icon" />
              <span>Aucune note ajoutée — les notes aident ACE à mieux apprendre</span>
            </div>

            <!-- Note libre facultative -->
            <div class="free-note-section">
              <label class="free-note-label">Note libre (optionnel)</label>
              <textarea
                v-model="freeNote"
                class="free-note-textarea"
                placeholder="Contexte supplémentaire, observations, etc."
                rows="2"
                maxlength="500"
              />
            </div>

          </div>

          <!-- Footer modal -->
          <div class="modal-footer">
            <div class="footer-hint" v-if="!rhNotes.length">
              <AlertCircleIcon class="hint-icon" />
              Ajoutez au moins une note pour aider ACE à apprendre
            </div>
            <div class="footer-hint success" v-else>
              <CheckCircleIcon class="hint-icon" />
              {{ rhNotes.length }} note(s) — ACE créera des règles précises
            </div>
            <div class="footer-actions">
              <button class="btn-cancel" @click="cancelModal">
                Annuler
              </button>
              <button
                :class="['btn-confirm', pendingAction?.confirmVariant]"
                @click="confirmModal"
                :disabled="loading"
              >
                <component :is="pendingAction?.icon" class="confirm-icon" />
                Confirmer : {{ pendingAction?.label }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>

</template>

<script setup>
import { computed, ref, nextTick } from 'vue'
import {
  InboxIcon, SearchIcon, ClockIcon, CalendarIcon,
  CheckCircleIcon, XCircleIcon, BookmarkIcon, CheckIcon,
  ClipboardIcon, RefreshCwIcon, UserCheckIcon, ArchiveIcon,
  XIcon, PlusIcon, MessageSquareIcon, AlertCircleIcon,
} from 'lucide-vue-next'

const props = defineProps({
  status:      { type: String,  default: 'Recu' },
  notes:       { type: String,  default: '' },
  compact:     { type: Boolean, default: false },
  showActions: { type: Boolean, default: true },
  loading:     { type: Boolean, default: false },
})

const emit = defineEmits(['update-status'])

// ── État modal ────────────────────────────────────────────────────────────────
const showModal     = ref(false)
const pendingAction = ref(null)
const rhNotes       = ref([])
const freeNote      = ref('')
const newNote       = ref({ sign: '+', text: '' })
const noteInputRef  = ref(null)

// ── Config statuts ────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
  Recu: {
    label: 'Reçu', description: "Dossier reçu, en attente d'analyse IA",
    icon: InboxIcon, iconColor: '#6366f1', bg: 'rgba(99,102,241,0.10)', class: 'status-recu',
  },
  EnAnalyse: {
    label: 'En analyse', description: "L'IA analyse le dossier en cours",
    icon: SearchIcon, iconColor: '#d97706', bg: 'rgba(245,158,11,0.10)', class: 'status-analyse',
  },
  ATraiter: {
    label: 'À traiter', description: 'Analyse terminée — décision RH requise',
    icon: ClockIcon, iconColor: '#2563eb', bg: 'rgba(59,130,246,0.10)', class: 'status-traiter',
  },
  Entretien: {
    label: 'Entretien', description: 'Entretien planifié — en attente du résultat',
    icon: CalendarIcon, iconColor: '#7c3aed', bg: 'rgba(139,92,246,0.10)', class: 'status-entretien',
  },
  Accepte: {
    label: 'Accepté', description: 'Candidature retenue après entretien',
    icon: CheckCircleIcon, iconColor: '#059669', bg: 'rgba(16,185,129,0.10)', class: 'status-accepte',
  },
  Refuse: {
    label: 'Refusé', description: 'Candidature non retenue',
    icon: XCircleIcon, iconColor: '#dc2626', bg: 'rgba(239,68,68,0.10)', class: 'status-refuse',
  },
  ListeAttente: {
    label: "Liste d'attente", description: "Profil intéressant — pas de poste disponible",
    icon: BookmarkIcon, iconColor: '#4b5563', bg: 'rgba(107,114,128,0.10)', class: 'status-attente',
  },
}

// ── Actions avec config modale ────────────────────────────────────────────────
const NEXT_ACTIONS = {
  Recu: [],
  EnAnalyse: [
    { value: 'ATraiter', label: 'Marquer traité', icon: CheckIcon,
      variant: 'btn-primary', tooltip: "L'analyse est terminée",
      color: '#6366f1', iconBg: 'rgba(99,102,241,0.1)', confirmVariant: 'confirm-primary' },
  ],
  ATraiter: [
    { value: 'Entretien', label: 'Planifier entretien', icon: CalendarIcon,
      variant: 'btn-primary', tooltip: 'Convoquer le candidat à un entretien',
      color: '#7c3aed', iconBg: 'rgba(139,92,246,0.1)', confirmVariant: 'confirm-primary' },
    { value: 'ListeAttente', label: "Liste d'attente", icon: BookmarkIcon,
      variant: 'btn-secondary', tooltip: 'Profil intéressant, pas de poste maintenant',
      color: '#4b5563', iconBg: 'rgba(107,114,128,0.1)', confirmVariant: 'confirm-secondary' },
    { value: 'Refuse', label: 'Refuser', icon: XCircleIcon,
      variant: 'btn-danger', tooltip: 'Candidature ne correspond pas au poste',
      color: '#dc2626', iconBg: 'rgba(239,68,68,0.1)', confirmVariant: 'confirm-danger' },
  ],
  Entretien: [
    { value: 'Accepte', label: 'Accepter le candidat', icon: UserCheckIcon,
      variant: 'btn-success', tooltip: 'Candidature retenue — décision post-entretien',
      color: '#059669', iconBg: 'rgba(16,185,129,0.1)', confirmVariant: 'confirm-success' },
    { value: 'Refuse', label: 'Refuser', icon: XCircleIcon,
      variant: 'btn-danger', tooltip: 'Candidature non retenue après entretien',
      color: '#dc2626', iconBg: 'rgba(239,68,68,0.1)', confirmVariant: 'confirm-danger' },
    { value: 'ListeAttente', label: "Liste d'attente", icon: BookmarkIcon,
      variant: 'btn-secondary', tooltip: 'Intéressant mais pas de poste disponible',
      color: '#4b5563', iconBg: 'rgba(107,114,128,0.1)', confirmVariant: 'confirm-secondary' },
  ],
  Accepte: [],
  Refuse:  [],
  ListeAttente: [
    { value: 'Entretien', label: 'Réactiver — Convoquer', icon: RefreshCwIcon,
      variant: 'btn-primary', tooltip: 'Un poste est disponible, relancer le processus',
      color: '#7c3aed', iconBg: 'rgba(139,92,246,0.1)', confirmVariant: 'confirm-primary' },
    { value: 'Refuse', label: 'Archiver / Refuser', icon: ArchiveIcon,
      variant: 'btn-danger', tooltip: 'Clore définitivement le dossier',
      color: '#dc2626', iconBg: 'rgba(239,68,68,0.1)', confirmVariant: 'confirm-danger' },
  ],
}

const TIMELINE_STEPS = [
  { key: 'Recu',      label: 'Reçu'      },
  { key: 'EnAnalyse', label: 'Analyse IA' },
  { key: 'ATraiter',  label: 'À traiter'  },
  { key: 'Entretien', label: 'Entretien'  },
  { key: 'Accepte',   label: 'Accepté'   },
]
const STATUS_ORDER = ['Recu', 'EnAnalyse', 'ATraiter', 'Entretien', 'Accepte']

// ── Computed ──────────────────────────────────────────────────────────────────
const statusConfig     = computed(() => STATUS_CONFIG[props.status] || STATUS_CONFIG['Recu'])
const timeline         = computed(() => TIMELINE_STEPS)
const availableActions = computed(() => NEXT_ACTIONS[props.status] || [])
const currentIndex     = computed(() => STATUS_ORDER.indexOf(props.status))

// Parse les notes stockées au format "+/-  texte\n Note: ..." en array structuré
const parsedNotes = computed(() => {
  if (!props.notes) return []
  return props.notes.split('\n')
    .filter(l => l.trim())
    .map(line => {
      if (line.startsWith('+ ')) return { sign: '+', text: line.slice(2) }
      if (line.startsWith('- ')) return { sign: '-', text: line.slice(2) }
      if (line.startsWith('Note : ')) return { sign: null, text: line.slice(7) }
      return { sign: null, text: line }
    })
})

function getStepState(key) {
  if (props.status === 'Refuse' || props.status === 'ListeAttente') {
    return STATUS_ORDER.indexOf(key) <= STATUS_ORDER.indexOf('ATraiter') ? 'done' : 'pending'
  }
  const stepIdx    = STATUS_ORDER.indexOf(key)
  const currentIdx = currentIndex.value
  if (stepIdx < currentIdx)  return 'done'
  if (stepIdx === currentIdx) return 'current'
  return 'pending'
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openNotesModal(action) {
  pendingAction.value = action
  rhNotes.value       = []
  freeNote.value      = ''
  newNote.value       = { sign: '+', text: '' }
  showModal.value     = true
  nextTick(() => noteInputRef.value?.focus())
}

function cancelModal() {
  showModal.value     = false
  pendingAction.value = null
  rhNotes.value       = []
  freeNote.value      = ''
}

function addNote() {
  if (!newNote.value.text.trim()) return
  rhNotes.value.push({ sign: newNote.value.sign, text: newNote.value.text.trim() })
  newNote.value.text = ''
  nextTick(() => noteInputRef.value?.focus())
}

function removeNote(i) {
  rhNotes.value.splice(i, 1)
}

function confirmModal() {
  if (!pendingAction.value) return

  // Construire la payload notes complète
  const notesPayload = {
    rhNotes:   rhNotes.value,
    freeNote:  freeNote.value.trim(),
  }

  emit('update-status', pendingAction.value.value, notesPayload)
  showModal.value = false
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════════════
   BADGE COMPACT
═══════════════════════════════════════════════════════════════════════════ */
.status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 20px;
  font-size: 12px; font-weight: 600; letter-spacing: 0.02em;
}
.badge-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.7; }

/* ═══════════════════════════════════════════════════════════════════════════
   CARTE PRINCIPALE
═══════════════════════════════════════════════════════════════════════════ */
.candidate-status-card {
  background: var(--surface-card, #fff);
  border: 1px solid var(--surface-border, #e5e7eb);
  border-radius: 12px; padding: 16px;
  display: flex; flex-direction: column; gap: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.status-header { display: flex; align-items: center; gap: 12px; }
.status-icon-wrap {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.status-svg-icon { width: 18px; height: 18px; }
.status-info { flex: 1; }
.status-label { font-size: 14px; font-weight: 700; color: var(--text-color, #111827); }
.status-sub   { font-size: 12px; color: var(--text-color-secondary, #6b7280); margin-top: 2px; }
.status-chip {
  padding: 4px 12px; border-radius: 20px;
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.05em; text-transform: uppercase; white-space: nowrap;
}

/* Timeline */
.timeline { display: flex; align-items: center; padding: 4px 0; overflow-x: auto; }
.timeline-step { display: flex; flex-direction: column; align-items: center; flex: 1; position: relative; gap: 4px; }
.step-connector { position: absolute; top: 10px; right: 50%; width: 100%; height: 2px; background: #e5e7eb; z-index: 0; }
.timeline-step.done    .step-connector { background: #10b981; }
.timeline-step.current .step-connector { background: linear-gradient(to right, #10b981, #e5e7eb); }
.step-dot {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  position: relative; z-index: 1;
  border: 2px solid #e5e7eb; background: #fff; transition: all 0.2s;
}
.timeline-step.done    .step-dot { background: #10b981; border-color: #10b981; }
.timeline-step.current .step-dot { background: #3b82f6; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.2); }
.dot-check  { width: 12px; height: 12px; color: #fff; }
.dot-pulse  { width: 8px; height: 8px; border-radius: 50%; background: #fff; }
.dot-empty  { width: 6px; height: 6px; border-radius: 50%; background: #d1d5db; }
.step-label { font-size: 10px; color: #9ca3af; text-align: center; white-space: nowrap; }
.timeline-step.done    .step-label { color: #10b981; font-weight: 600; }
.timeline-step.current .step-label { color: #3b82f6; font-weight: 700; }

/* Notes affichées */
.status-notes {
  background: var(--surface-hover, #f9fafb);
  border-radius: 8px; padding: 10px 12px;
  border: 1px solid var(--surface-border, #f3f4f6);
}
.notes-header {
  display: flex; align-items: center; gap: 5px;
  font-weight: 700; color: var(--text-color, #374151);
  margin-bottom: 8px; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.notes-icon { width: 13px; height: 13px; color: #9ca3af; }
.notes-body { display: flex; flex-direction: column; gap: 5px; }

.note-line {
  display: flex; align-items: flex-start; gap: 8px; font-size: 12px;
}
.note-sign-badge {
  width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 11px; flex-shrink: 0; margin-top: 1px;
}
.sign-plus  { background: #dcfce7; color: #16a34a; }
.sign-minus { background: #fee2e2; color: #dc2626; }
.note-text  { color: var(--text-color-secondary, #6b7280); line-height: 1.5; }
.note-plain { color: var(--text-color-secondary, #6b7280); font-size: 12px; line-height: 1.5; white-space: pre-wrap; }

/* Actions */
.status-actions {
  display: flex; flex-direction: column; gap: 8px;
  padding-top: 4px; border-top: 1px solid var(--surface-border, #f3f4f6);
}
.actions-label { font-size: 11px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; }
.actions-row { display: flex; gap: 8px; flex-wrap: wrap; }
.action-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: 8px;
  font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all 0.15s; border: none;
}
.action-icon { width: 13px; height: 13px; flex-shrink: 0; }
.btn-primary   { background: #6366f1; color: #fff; }
.btn-primary:hover:not(:disabled)   { background: #4f46e5; transform: translateY(-1px); }
.btn-success   { background: #10b981; color: #fff; }
.btn-success:hover:not(:disabled)   { background: #059669; transform: translateY(-1px); }
.btn-danger    { background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; }
.btn-danger:hover:not(:disabled)    { background: #fecaca; }
.btn-secondary { background: var(--surface-hover, #f3f4f6); color: var(--text-color, #374151); border: 1px solid var(--surface-border, #e5e7eb); }
.btn-secondary:hover:not(:disabled) { background: var(--surface-border, #e5e7eb); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   MODAL
═══════════════════════════════════════════════════════════════════════════ */
.modal-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.45); backdrop-filter: blur(3px);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.modal-card {
  background: #fff; border-radius: 16px;
  width: 100%; max-width: 560px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08);
  display: flex; flex-direction: column;
  max-height: 90vh; overflow: hidden;
}

/* Header */
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 16px; border-bottom: 2px solid #f3f4f6;
  gap: 12px;
}
.modal-header-left { display: flex; align-items: center; gap: 14px; flex: 1; }
.modal-action-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.modal-icon { width: 22px; height: 22px; }
.modal-title { font-size: 16px; font-weight: 700; color: #111827; }
.modal-subtitle { font-size: 12px; color: #6b7280; margin-top: 2px; }
.modal-subtitle-hint { color: #a78bfa; font-style: italic; }
.modal-close {
  width: 32px; height: 32px; border-radius: 8px; border: none;
  background: #f3f4f6; cursor: pointer; display: flex;
  align-items: center; justify-content: center;
  flex-shrink: 0; transition: background 0.15s;
}
.modal-close:hover { background: #e5e7eb; }
.close-icon { width: 15px; height: 15px; color: #6b7280; }

/* Body */
.modal-body {
  padding: 20px 24px; display: flex; flex-direction: column; gap: 18px;
  overflow-y: auto; flex: 1;
}

/* Banner ACE */
.ace-info-banner {
  display: flex; align-items: flex-start; gap: 12px;
  background: linear-gradient(135deg, #faf5ff, #eff6ff);
  border: 1px solid #e9d5ff; border-radius: 10px; padding: 12px 14px;
}
.ace-info-icon { font-size: 20px; flex-shrink: 0; line-height: 1; }
.ace-info-text { font-size: 12px; color: #374151; line-height: 1.6; }
.ace-info-text strong { color: #7c3aed; }
.sign-badge-inline {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  font-weight: 800; font-size: 11px;
}
.sign-badge-inline.plus  { background: #dcfce7; color: #16a34a; }
.sign-badge-inline.minus { background: #fee2e2; color: #dc2626; }

/* Input note */
.note-input-section { display: flex; flex-direction: column; gap: 8px; }
.note-input-label { font-size: 12px; font-weight: 600; color: #374151; }
.note-input-row { display: flex; gap: 8px; align-items: center; }

/* Toggle +/- */
.sign-toggle {
  display: flex; border-radius: 8px;
  overflow: hidden; border: 1px solid #e5e7eb; flex-shrink: 0;
}
.sign-btn {
  width: 36px; height: 36px; border: none; font-size: 16px; font-weight: 800;
  cursor: pointer; background: #f9fafb; color: #9ca3af;
  transition: all 0.15s; display: flex; align-items: center; justify-content: center;
}
.sign-btn:first-child { border-right: 1px solid #e5e7eb; }
.sign-btn-active-plus  { background: #dcfce7 !important; color: #16a34a !important; }
.sign-btn-active-minus { background: #fee2e2 !important; color: #dc2626 !important; }

.note-input {
  flex: 1; height: 36px; border: 1px solid #e5e7eb; border-radius: 8px;
  padding: 0 12px; font-size: 13px; color: #111827;
  outline: none; transition: border-color 0.15s;
  background: var(--surface-card, #fff);
}
.note-input:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.note-input::placeholder { color: #d1d5db; }

.add-note-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 0 14px; height: 36px; border-radius: 8px;
  background: #6366f1; color: #fff; border: none;
  font-size: 12px; font-weight: 600; cursor: pointer;
  white-space: nowrap; transition: all 0.15s; flex-shrink: 0;
}
.add-note-btn:hover:not(:disabled) { background: #4f46e5; }
.add-note-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.add-icon { width: 13px; height: 13px; }

/* Notes ajoutées */
.notes-added { display: flex; flex-direction: column; gap: 8px; }
.notes-added-label {
  font-size: 11px; font-weight: 600; color: #6b7280;
  text-transform: uppercase; letter-spacing: 0.05em;
  display: flex; align-items: center; gap: 8px;
}
.notes-count {
  background: #6366f1; color: #fff;
  font-size: 10px; font-weight: 700;
  padding: 1px 7px; border-radius: 20px;
}
.notes-list { display: flex; flex-direction: column; gap: 6px; }
.note-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 9px;
  font-size: 13px; transition: transform 0.15s;
}
.note-item-plus  { background: #f0fdf4; border: 1px solid #bbf7d0; }
.note-item-minus { background: #fef2f2; border: 1px solid #fecaca; }
.note-item-sign {
  width: 20px; height: 20px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 12px; flex-shrink: 0;
}
.note-item-text { flex: 1; color: #374151; line-height: 1.4; }
.note-remove {
  width: 24px; height: 24px; border-radius: 6px; border: none;
  background: transparent; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: all 0.15s; flex-shrink: 0;
}
.note-item:hover .note-remove { opacity: 1; background: rgba(0,0,0,0.06); }
.remove-icon { width: 13px; height: 13px; color: #9ca3af; }

/* Empty state */
.notes-empty {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 16px; border-radius: 10px;
  background: #f9fafb; border: 1px dashed #e5e7eb;
  color: #9ca3af; font-size: 12px; font-style: italic;
}
.empty-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* Note libre */
.free-note-section { display: flex; flex-direction: column; gap: 6px; }
.free-note-label { font-size: 12px; font-weight: 600; color: #6b7280; }
.free-note-textarea {
  width: 100%; border: 1px solid #e5e7eb; border-radius: 8px;
  padding: 10px 12px; font-size: 13px; color: #374151;
  resize: none; outline: none; font-family: inherit;
  transition: border-color 0.15s;
  background: var(--surface-card, #fff); box-sizing: border-box;
}
.free-note-textarea:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.free-note-textarea::placeholder { color: #d1d5db; }

/* Footer */
.modal-footer {
  padding: 16px 24px; border-top: 1px solid #f3f4f6;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  background: #fafafa; border-radius: 0 0 16px 16px;
}
.footer-hint {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #9ca3af;
}
.footer-hint.success { color: #16a34a; }
.hint-icon { width: 14px; height: 14px; flex-shrink: 0; }
.footer-actions { display: flex; gap: 10px; align-items: center; }

.btn-cancel {
  padding: 9px 18px; border-radius: 8px; border: 1px solid #e5e7eb;
  background: #fff; color: #6b7280; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.btn-cancel:hover { background: #f3f4f6; }

.btn-confirm {
  display: flex; align-items: center; gap: 7px;
  padding: 9px 20px; border-radius: 8px; border: none;
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.confirm-icon { width: 15px; height: 15px; }
.confirm-primary   { background: #6366f1; color: #fff; }
.confirm-primary:hover:not(:disabled)   { background: #4f46e5; }
.confirm-success   { background: #10b981; color: #fff; }
.confirm-success:hover:not(:disabled)   { background: #059669; }
.confirm-danger    { background: #dc2626; color: #fff; }
.confirm-danger:hover:not(:disabled)    { background: #b91c1c; }
.confirm-secondary { background: #374151; color: #fff; }
.confirm-secondary:hover:not(:disabled) { background: #1f2937; }
.btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }

/* Transitions */
.modal-fade-enter-active, .modal-fade-leave-active { transition: all 0.2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-from .modal-card { transform: scale(0.95) translateY(-10px); }
.modal-fade-leave-to  .modal-card { transform: scale(0.95) translateY(-10px); }

.note-list-enter-active { transition: all 0.2s ease; }
.note-list-leave-active { transition: all 0.15s ease; }
.note-list-enter-from   { opacity: 0; transform: translateY(-8px); }
.note-list-leave-to     { opacity: 0; transform: translateX(10px); }

/* ═══════════════════════════════════════════════════════════════════════════
   STATUTS
═══════════════════════════════════════════════════════════════════════════ */
.status-recu      { background: rgba(99,102,241,0.1);  color: #6366f1; }
.status-analyse   { background: rgba(245,158,11,0.1);  color: #d97706; }
.status-traiter   { background: rgba(59,130,246,0.1);  color: #2563eb; }
.status-entretien { background: rgba(139,92,246,0.1);  color: #7c3aed; }
.status-accepte   { background: rgba(16,185,129,0.1);  color: #059669; }
.status-refuse    { background: rgba(239,68,68,0.1);   color: #dc2626; }
.status-attente   { background: rgba(107,114,128,0.1); color: #4b5563; }
</style>