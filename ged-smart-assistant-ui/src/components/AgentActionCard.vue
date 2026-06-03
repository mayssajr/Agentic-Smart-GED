<template>
  <div class="aac-wrapper" :class="`aac--${state}`">

    <!-- En-tête action -->
    <div class="aac-header">
      <div class="aac-icon" :class="`icon--${state}`">
        <i v-if="state === 'pending'"    class="pi pi-shield"></i>
        <i v-else-if="state === 'working'" class="pi pi-spin pi-cog"></i>
        <i v-else-if="state === 'done'"  class="pi pi-check-circle"></i>
        <i v-else                         class="pi pi-times-circle"></i>
      </div>
      <div class="aac-title-block">
        <span class="aac-title">{{ titles[state] }}</span>
        <span class="aac-subtitle">{{ action.description }}</span>
      </div>
      <div v-if="state === 'working'" class="aac-live-badge">
        <span class="live-dot"></span> En cours
      </div>
    </div>

    <!-- Aperçu cible (mini-GED) -->
    <div class="aac-preview" :class="{ 'aac-preview--active': state === 'working' }">
      <!-- Barre titre mini-fenêtre -->
      <div class="preview-titlebar">
        <span class="preview-dots">
          <span></span><span></span><span></span>
        </span>
        <span class="preview-url">MiniGED · {{ action.target || 'Document' }}</span>
      </div>

      <!-- Contenu simulé -->
      <div class="preview-body" ref="previewBody">
        <!-- Champs simulés du GED -->
        <div v-for="(field, i) in action.fields || []" :key="i"
          class="preview-field" :class="{ 'preview-field--active': activeFieldIndex === i }">
          <span class="preview-field-label">{{ field.label }}</span>
          <div class="preview-field-value" :class="{ 'typing': activeFieldIndex === i && isTyping }">
            <span v-if="activeFieldIndex === i && state === 'working'">{{ typedText }}<span class="cursor-blink" v-if="isTyping">|</span></span>
            <span v-else class="field-placeholder">{{ field.placeholder || field.value || '—' }}</span>
          </div>
        </div>

        <!-- Curseur agentique SVG -->
        <div class="agent-cursor-wrap" ref="cursorWrap"
          :style="cursorStyle">
          <svg class="agent-cursor" viewBox="0 0 20 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M0 0L0 20L5.5 14.5L9 22L11.5 21L8 13.5H15L0 0Z" fill="#5B5BD6" stroke="white" stroke-width="1.2"/>
          </svg>
          <div v-if="state === 'working'" class="cursor-ripple"></div>
        </div>
      </div>
    </div>

    <!-- Steps de progression -->
    <div class="aac-steps" v-if="state === 'working' || state === 'done'">
      <div v-for="(step, i) in steps" :key="i"
        class="aac-step" :class="stepClass(i)">
        <div class="step-indicator">
          <i v-if="completedSteps > i"    class="pi pi-check step-icon step-done"></i>
          <span v-else-if="currentStep === i" class="step-spinner"><i class="pi pi-spin pi-circle-fill"></i></span>
          <span v-else                        class="step-num">{{ i + 1 }}</span>
        </div>
        <span class="step-label">{{ step }}</span>
      </div>
    </div>

    <!-- Barre de progression -->
    <div v-if="state === 'working'" class="aac-progress-bar">
      <div class="aac-progress-fill" :style="{ width: progressPct + '%' }"></div>
    </div>

    <!-- Boutons (état pending) -->
    <div v-if="state === 'pending'" class="aac-actions">
      <button class="aac-btn aac-btn--confirm" @click="confirm">
        <i class="pi pi-check"></i> Autoriser
      </button>
      <button class="aac-btn aac-btn--cancel" @click="cancel">
        <i class="pi pi-times"></i> Refuser
      </button>
    </div>

    <!-- Résultat final -->
    <div v-if="state === 'done'" class="aac-result">
      <i class="pi pi-check-circle"></i>
      <span>{{ action.successMessage || 'Action effectuée avec succès.' }}</span>
    </div>
    <div v-if="state === 'error'" class="aac-result aac-result--error">
      <i class="pi pi-times-circle"></i>
      <span>{{ errorMsg || 'Une erreur est survenue.' }}</span>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  action: { type: Object, required: true },
  // action = {
  //   description: "Mettre à jour le statut du candidat",
  //   target: "Recrutement > Lucas Bernard",
  //   fields: [{ label: "Statut", placeholder: "À traiter", value: "Entretien" }],
  //   type: "update_status" | "create_task" | "send_email" | ...,
  //   successMessage: "Statut mis à jour → Entretien",
  //   steps: ["Vérification permissions", "Navigation", "Mise à jour", "Confirmation"],
  // }
})

const emit = defineEmits(['confirm', 'cancel', 'done', 'error'])

// ── State machine ─────────────────────────────────────────────────────────────
const state    = ref('pending')  // pending | working | done | error
const errorMsg = ref('')

const titles = {
  pending: "Autorisation requise",
  working: "Agent en action",
  done:    "Action terminée",
  error:   "Échec de l'action",
}

// ── Steps & Progress ──────────────────────────────────────────────────────────
const defaultSteps = ["Vérification", "Navigation", "Exécution", "Confirmation"]
const steps        = computed(() => props.action.steps || defaultSteps)
const currentStep  = ref(0)
const completedSteps = ref(0)
const progressPct  = ref(0)

// ── Curseur agentique ─────────────────────────────────────────────────────────
const cursorX = ref(10)
const cursorY = ref(10)

const cursorStyle = computed(() => ({
  transform: `translate(${cursorX.value}px, ${cursorY.value}px)`,
  transition: cursorX.value === 10 ? 'none' : 'transform 0.9s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
}))

// ── Typage live ───────────────────────────────────────────────────────────────
const typedText     = ref('')
const isTyping      = ref(false)
const activeFieldIndex = ref(-1)
const previewBody   = ref(null)

let _timers = []
const _t = (fn, ms) => { const id = setTimeout(fn, ms); _timers.push(id); return id }
const _clearAll = () => { _timers.forEach(clearTimeout); _timers = [] }

// ── Actions ───────────────────────────────────────────────────────────────────
const confirm = () => {
  state.value = 'working'
  emit('confirm')
  runAnimation()
}

const cancel = () => {
  emit('cancel')
}

const markDone = () => {
  state.value = 'done'
  completedSteps.value = steps.value.length
  progressPct.value = 100
  emit('done')
}

const markError = (msg) => {
  state.value = 'error'
  errorMsg.value = msg || 'Erreur inconnue.'
  emit('error', msg)
}

// ── Animation séquencée ───────────────────────────────────────────────────────
const runAnimation = () => {
  const fields  = props.action.fields || []
  const nSteps  = steps.value.length
  const stepDur = 900

  // Phase 1 — Steps progressifs
  for (let i = 0; i < nSteps; i++) {
    _t(() => {
      currentStep.value = i
      progressPct.value = Math.round(((i + 0.5) / nSteps) * 90)
    }, i * stepDur)
    _t(() => {
      completedSteps.value = i + 1
      progressPct.value = Math.round(((i + 1) / nSteps) * 90)
    }, i * stepDur + stepDur * 0.7)
  }

  // Phase 2 — Mouvement curseur vers le premier champ
  if (fields.length > 0) {
    _t(() => {
      cursorX.value = 60
      cursorY.value = 42
    }, 400)

    // Typer dans chaque champ
    fields.forEach((field, fi) => {
      const baseDelay = 1200 + fi * 1800
      _t(() => {
        activeFieldIndex.value = fi
        // Déplacer curseur vers ce champ
        cursorX.value = 60
        cursorY.value = 42 + fi * 48
      }, baseDelay)

      _t(() => {
        // Click ripple puis start typing
        isTyping.value = true
        typedText.value = ''
        const target   = field.value || field.placeholder || ''
        let idx = 0
        const typeChar = () => {
          if (idx < target.length) {
            typedText.value += target[idx++]
            _t(typeChar, 50 + Math.random() * 60)
          } else {
            isTyping.value = false
          }
        }
        typeChar()
      }, baseDelay + 600)
    })
  }

  // Phase finale — Done
  const totalDur = Math.max(nSteps * stepDur, 1200 + (fields.length || 0) * 1800 + 1200)
  _t(() => {
    activeFieldIndex.value = -1
    cursorX.value = 10
    cursorY.value = 10
    progressPct.value = 100
    markDone()
  }, totalDur)
}

// Exposer markDone / markError pour que le parent puisse signaler le résultat réel
defineExpose({ markDone, markError })

onUnmounted(_clearAll)

const stepClass = (i) => ({
  'step--done':    completedSteps.value > i,
  'step--active':  currentStep.value === i && completedSteps.value <= i,
  'step--pending': i > currentStep.value && completedSteps.value <= i,
})
</script>

<style scoped>
/* ── Wrapper ── */
.aac-wrapper {
  border-radius: 14px;
  border: 1.5px solid #e4e4f0;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(91,91,214,.08);
  transition: border-color .3s, box-shadow .3s;
  font-family: inherit;
}
.aac--working {
  border-color: #a5b4fc;
  box-shadow: 0 4px 24px rgba(91,91,214,.15);
}
.aac--done  { border-color: #86efac; box-shadow: 0 4px 16px rgba(22,163,74,.08); }
.aac--error { border-color: #fca5a5; box-shadow: 0 4px 16px rgba(239,68,68,.08); }

/* ── Header ── */
.aac-header {
  display: flex; align-items: flex-start; gap: .75rem;
  padding: .875rem 1rem;
  background: linear-gradient(135deg, #f5f3ff 0%, #fafbff 100%);
  border-bottom: 1px solid #e4e4f0;
}
.aac--working .aac-header { background: linear-gradient(135deg, #eef0ff 0%, #f5f3ff 100%); }
.aac--done    .aac-header { background: linear-gradient(135deg, #f0fdf4 0%, #fafbff 100%); border-color: #bbf7d0; }
.aac--error   .aac-header { background: linear-gradient(135deg, #fef2f2 0%, #fff 100%); border-color: #fecaca; }

.aac-icon {
  width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
}
.icon--pending { background: #eef0ff; color: #5b5bd6; }
.icon--working { background: #dbeafe; color: #2563eb; }
.icon--done    { background: #dcfce7; color: #16a34a; }
.icon--error   { background: #fee2e2; color: #dc2626; }

.aac-title-block { flex: 1; min-width: 0; }
.aac-title {
  display: block; font-size: 13px; font-weight: 700; color: #0d0d0d;
  margin-bottom: 2px;
}
.aac-subtitle {
  display: block; font-size: 11.5px; color: #6b7280;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.aac-live-badge {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; color: #2563eb;
  background: #dbeafe; border-radius: 20px; padding: 3px 10px; flex-shrink: 0;
}
.live-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #2563eb;
  animation: livePulse 1s ease-in-out infinite;
}
@keyframes livePulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: .4; transform: scale(.7); }
}

/* ── Preview (mini GED) ── */
.aac-preview {
  margin: .75rem; border-radius: 10px;
  border: 1px solid #e4e4f0; overflow: hidden;
  background: #f9f9fc;
  transition: border-color .3s, box-shadow .3s;
}
.aac-preview--active {
  border-color: #a5b4fc;
  box-shadow: 0 2px 12px rgba(91,91,214,.12), inset 0 0 0 2px rgba(91,91,214,.04);
}

.preview-titlebar {
  display: flex; align-items: center; gap: .5rem;
  padding: 6px 10px;
  background: #f0f0f6; border-bottom: 1px solid #e4e4f0;
}
.preview-dots { display: flex; gap: 4px; }
.preview-dots span {
  width: 8px; height: 8px; border-radius: 50%;
  background: #d4d4d8;
}
.preview-dots span:nth-child(1) { background: #fc8181; }
.preview-dots span:nth-child(2) { background: #fbbf24; }
.preview-dots span:nth-child(3) { background: #34d399; }
.preview-url {
  font-size: 10.5px; color: #6b7280; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.preview-body {
  padding: .6rem .75rem; position: relative; min-height: 80px;
}

.preview-field {
  display: flex; align-items: center; gap: .5rem;
  padding: .4rem .5rem; border-radius: 7px;
  margin-bottom: .3rem; transition: background .2s;
}
.preview-field--active { background: #eef0ff; }

.preview-field-label {
  font-size: 10.5px; font-weight: 600; color: #9ca3af;
  min-width: 56px; text-transform: uppercase; letter-spacing: .03em;
  flex-shrink: 0;
}
.preview-field-value {
  flex: 1; font-size: 12px; color: #0d0d0d;
  background: white; border: 1px solid #e4e4f0;
  border-radius: 6px; padding: 5px 8px;
  min-height: 28px; display: flex; align-items: center;
  transition: border-color .2s, box-shadow .2s;
}
.preview-field--active .preview-field-value {
  border-color: #5b5bd6;
  box-shadow: 0 0 0 2px rgba(91,91,214,.12);
}
.field-placeholder { color: #d1d5db; font-style: italic; }
.cursor-blink {
  display: inline-block; width: 2px; background: #5b5bd6;
  animation: blinkCursor .8s step-end infinite;
  margin-left: 1px; height: 13px; vertical-align: text-bottom;
}
@keyframes blinkCursor {
  0%, 100% { opacity: 1; } 50% { opacity: 0; }
}

/* ── Curseur agentique ── */
.agent-cursor-wrap {
  position: absolute; top: 0; left: 0;
  pointer-events: none; z-index: 20;
  width: 24px; height: 28px;
}
.agent-cursor { width: 20px; height: 24px; filter: drop-shadow(0 2px 4px rgba(91,91,214,.3)); }

.cursor-ripple {
  position: absolute; top: 14px; left: 8px;
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid #5b5bd6;
  animation: rippleOut 1.2s ease-out infinite;
}
@keyframes rippleOut {
  0%   { transform: scale(0); opacity: .8; }
  100% { transform: scale(2.5); opacity: 0; }
}

/* ── Steps ── */
.aac-steps {
  display: flex; flex-direction: column; gap: .2rem;
  padding: .5rem .875rem;
  border-top: 1px solid #f0f0f6;
}
.aac-step {
  display: flex; align-items: center; gap: .5rem;
  padding: .25rem 0; font-size: 11.5px; color: #9ca3af;
  transition: color .2s;
}
.step--done   { color: #16a34a; }
.step--active { color: #5b5bd6; font-weight: 600; }

.step-indicator {
  width: 18px; height: 18px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.step-icon { font-size: 12px; }
.step-done { color: #16a34a; }
.step-spinner { color: #5b5bd6; font-size: 12px; }
.step-num {
  width: 16px; height: 16px; border-radius: 50%;
  background: #f0f0f6; color: #9ca3af; font-size: 10px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.step-label { flex: 1; }

/* ── Barre de progression ── */
.aac-progress-bar {
  height: 3px; background: #f0f0f6; overflow: hidden;
  border-top: 1px solid #e4e4f0;
}
.aac-progress-fill {
  height: 100%; background: linear-gradient(90deg, #5b5bd6, #818cf8);
  transition: width .5s cubic-bezier(.4, 0, .2, 1);
  border-radius: 2px;
}

/* ── Boutons ── */
.aac-actions {
  display: flex; gap: .5rem; padding: .75rem;
  border-top: 1px solid #f0f0f6;
}
.aac-btn {
  flex: 1; padding: 8px 12px; border-radius: 10px;
  font-size: 12.5px; font-weight: 600; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: .4rem;
  border: none; transition: all .15s; font-family: inherit;
}
.aac-btn--confirm {
  background: #5b5bd6; color: white;
  box-shadow: 0 2px 8px rgba(91,91,214,.25);
}
.aac-btn--confirm:hover { background: #4c4cb5; transform: translateY(-1px); }
.aac-btn--cancel  {
  background: #f4f4f5; color: #6b7280;
  border: 1px solid #e4e4f0;
}
.aac-btn--cancel:hover { background: #fef2f2; color: #dc2626; border-color: #fecaca; }

/* ── Résultat ── */
.aac-result {
  display: flex; align-items: center; gap: .5rem;
  padding: .7rem 1rem; font-size: 12.5px; font-weight: 500;
  border-top: 1px solid #f0f0f6;
  color: #16a34a; background: #f0fdf4;
}
.aac-result .pi { font-size: 15px; }
.aac-result--error { color: #dc2626; background: #fef2f2; }
</style>
