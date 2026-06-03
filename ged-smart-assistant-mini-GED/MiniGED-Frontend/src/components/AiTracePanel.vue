<template>
  <div class="trace-panel">

    <!-- Header + actions -->
    <div class="trace-header">
      <div class="trace-title">
        <span class="trace-badge">IA</span>
        Trace ReAct — dernière analyse
      </div>
      <div class="trace-actions">
        <span class="trace-meta" v-if="traceData.length">
          {{ traceData.length }} étapes · {{ totalMs ? totalMs + ' ms' : '' }}
        </span>
        <!-- View mode toggle -->
        <div class="view-toggle">
          <button class="toggle-btn" :class="{ 'toggle-btn--active': viewMode === 'steps' }"
            @click="viewMode = 'steps'" title="Vue liste">
            <i class="fas fa-list"></i> Étapes
          </button>
          <button class="toggle-btn" :class="{ 'toggle-btn--active': viewMode === 'timeline' }"
            @click="viewMode = 'timeline'" title="Vue timeline Gantt">
            <i class="fas fa-timeline"></i> Timeline
          </button>
        </div>
        <button v-if="viewMode === 'steps'" class="trace-btn" @click="expandAll = !expandAll" title="Tout déplier/replier">
          <i :class="expandAll ? 'fas fa-compress' : 'fas fa-expand'"></i>
          {{ expandAll ? 'Replier' : 'Déplier' }}
        </button>
        <button class="trace-btn trace-btn--export" @click="exportJson" title="Exporter en JSON">
          <i class="fas fa-download"></i> JSON
        </button>
      </div>
    </div>

    <!-- Vide / chargement -->
    <div v-if="!traceData.length" class="trace-empty">
      <div class="trace-empty-icon"><i class="fas fa-microchip"></i></div>
      <p>Aucune trace disponible pour ce document.</p>
      <p class="trace-empty-sub">Lancez une analyse IA pour voir la trace ReAct.</p>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         VIEW : STEPS
    ════════════════════════════════════════════════════════════════════════ -->
    <div v-else-if="viewMode === 'steps'" class="trace-steps">
      <div
        v-for="(step, i) in traceData"
        :key="i"
        class="step"
        :class="`step--${step.type}`"
      >
        <div class="step-line" v-if="i < traceData.length - 1"></div>
        <div class="step-dot-wrap">
          <div class="step-dot">
            <i :class="STEP_ICONS[step.type] ?? 'fas fa-circle'"></i>
          </div>
        </div>
        <div class="step-card" @click="toggleStep(i)">
          <div class="step-card-head">
            <span class="step-type-badge" :class="`step-type--${step.type}`">
              {{ STEP_LABELS[step.type] ?? step.type }}
            </span>
            <span class="step-agent" v-if="step.agent">{{ step.agent }}</span>
            <span class="step-ms"  v-if="step.ms">{{ step.ms }} ms</span>
            <i class="fas fa-chevron-down step-chevron"
               :class="{ 'step-chevron--open': expandAll || openSteps.has(i) }"></i>
          </div>
          <div class="step-content" v-show="expandAll || openSteps.has(i)">
            <pre class="step-text">{{ step.content }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         VIEW : TIMELINE (Gantt)
    ════════════════════════════════════════════════════════════════════════ -->
    <div v-else class="timeline-wrap">

      <!-- X-axis header (time ticks) -->
      <div class="tl-header">
        <div class="tl-label-col"></div>
        <div class="tl-axis">
          <span class="tl-tick" v-for="tick in timeTicks" :key="tick.label"
            :style="{ left: tick.pct + '%' }">
            {{ tick.label }}
          </span>
        </div>
      </div>

      <!-- Total duration bar -->
      <div class="tl-total">
        <div class="tl-label-col">
          <span class="tl-total-label">Durée totale</span>
        </div>
        <div class="tl-track">
          <div class="tl-bar tl-bar--total" :style="{ width: '100%' }">
            {{ totalMs ? totalMs + ' ms' : traceData.length + ' étapes' }}
          </div>
        </div>
      </div>

      <!-- One row per agent/type -->
      <div class="tl-rows">
        <div class="tl-row" v-for="row in ganttRows" :key="row.id"
          @mouseenter="hoveredGantt = row.id"
          @mouseleave="hoveredGantt = null"
          :class="{ 'tl-row--hovered': hoveredGantt === row.id }"
        >
          <div class="tl-label-col">
            <span class="tl-agent-dot" :class="`tl-dot--${row.type}`"></span>
            <span class="tl-agent-name">{{ row.label }}</span>
            <span class="tl-step-count">{{ row.count }}×</span>
          </div>
          <div class="tl-track">
            <div class="tl-bar-bg"></div>
            <div
              class="tl-bar"
              :class="`tl-bar--${row.type}`"
              :style="{ left: row.startPct + '%', width: row.widthPct + '%' }"
            >
              <span class="tl-bar-label">
                {{ row.durationMs ? row.durationMs + ' ms' : '' }}
              </span>
            </div>
          </div>
          <div class="tl-tooltip" v-if="hoveredGantt === row.id">
            <div class="tl-tt-title">{{ row.label }}</div>
            <div class="tl-tt-row" v-for="(s, i) in row.steps.slice(0,3)" :key="i">
              <span :class="`tl-tt-badge tl-tt-badge--${s.type}`">{{ STEP_LABELS[s.type] || s.type }}</span>
              <span class="tl-tt-text">{{ truncate(s.content, 50) }}</span>
            </div>
            <div v-if="row.steps.length > 3" class="tl-tt-more">+{{ row.steps.length - 3 }} autres étapes</div>
          </div>
        </div>
      </div>

      <!-- Legend -->
      <div class="tl-legend">
        <span v-for="(lbl, type) in STEP_LABELS" :key="type" class="tl-leg-item">
          <span :class="`tl-dot--${type}`" class="tl-leg-dot"></span>
          {{ lbl }}
        </span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  documentId: { type: [String, Number], default: '' },
  // FIX 2 : ce prop est maintenant la SOURCE DE VÉRITÉ principale.
  // Il est mis à jour directement par DocumentDetails.vue dans onAnalyzed().
  reactTrace: { type: Array, default: () => [] },
})

// ── Config visuelle ───────────────────────────────────────────────────────────
const STEP_ICONS = {
  thought: 'fas fa-brain',
  action:  'fas fa-bolt',
  observe: 'fas fa-eye',
  answer:  'fas fa-check-circle',
}
const STEP_LABELS = {
  thought: 'Réflexion',
  action:  'Action',
  observe: 'Observation',
  answer:  'Réponse',
}

const AGENT_MAP = [
  { id: 'orchestrator', label: 'Orchestrator',    keywords: ['orchestrat'], type: 'thought' },
  { id: 'classifier',   label: 'ClassifierAgent', keywords: ['classif', 'Classifier'], type: 'action' },
  { id: 'summarizer',   label: 'SummarizerAgent', keywords: ['summar', 'Summariz', 'résumé'], type: 'action' },
  { id: 'rag',          label: 'RAG Pipeline',    keywords: ['RAG', 'rag', 'chunk', 'ChromaDB', 'index'], type: 'observe' },
  { id: 'task',         label: 'TaskAgent',       keywords: ['TaskAgent', 'tâche', 'task'], type: 'action' },
  { id: 'score',        label: 'ScoreAgent',      keywords: ['Score', 'score', 'AiScore'], type: 'action' },
  { id: 'email',        label: 'EmailAgent',      keywords: ['Email', 'email', 'brouillon', 'envoi'], type: 'action' },
  { id: 'ace',          label: 'ACE',             keywords: ['ACE', 'ace', 'playbook', 'Playbook'], type: 'observe' },
]

// ── State ─────────────────────────────────────────────────────────────────────
const viewMode     = ref('steps')
const expandAll    = ref(false)
const openSteps    = ref(new Set())
const hoveredGantt = ref(null)

// ── Source interne de trace (alimente traceData) ──────────────────────────────
// Priorité : prop reactTrace > localStorage
const _localTrace = ref([])

onMounted(() => {
  // Au montage, charger depuis localStorage uniquement si le prop est vide
  if (!props.reactTrace?.length && props.documentId) {
    try {
      const stored = localStorage.getItem(`ai_trace_${props.documentId}`)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length) {
          _localTrace.value = parsed
        }
      }
    } catch { /* non bloquant */ }
  }
})

// Quand le prop reactTrace change (ex: après onAnalyzed dans le parent),
// l'utiliser immédiatement — pas besoin de passer par localStorage.
watch(
  () => props.reactTrace,
  (newTrace) => {
    if (newTrace?.length) {
      _localTrace.value = newTrace
      // Persister en localStorage pour les navigations futures
      if (props.documentId) {
        try {
          localStorage.setItem(`ai_trace_${props.documentId}`, JSON.stringify(newTrace))
        } catch { /* non bloquant */ }
      }
    }
  },
  { deep: true, immediate: true }
)

// ── traceData = source unifiée ────────────────────────────────────────────────
const traceData = computed(() => {
  const source = _localTrace.value.length ? _localTrace.value : []
  return parseTrace(source)
})

function parseTrace(raw) {
  return raw.map(step => {
    const m = step.content?.match(/^\[([^\]]+)\/([A-Z]+)\]\s*(.*)$/s)
    return {
      type:    (m ? m[2].toLowerCase() : step.type) || 'observe',
      agent:   m ? m[1] : null,
      content: m ? m[3] : step.content,
      ms:      step.ms ?? null,
    }
  })
}

const totalMs = computed(() => {
  const answer = traceData.value.findLast?.(s => s.type === 'answer')
  return answer?.ms ?? traceData.value.findLast?.(s => s.ms)?.ms ?? null
})

// ── Gantt rows ────────────────────────────────────────────────────────────────
const ganttRows = computed(() => {
  const steps = traceData.value
  if (!steps.length) return []

  const total = steps.length

  const agentBuckets = {}
  steps.forEach((step, i) => {
    const content = (step.content || '') + (step.agent || '')
    let matched = false
    for (const agentDef of AGENT_MAP) {
      if (agentDef.keywords.some(kw => content.toLowerCase().includes(kw.toLowerCase()))) {
        if (!agentBuckets[agentDef.id]) {
          agentBuckets[agentDef.id] = { ...agentDef, startIdx: i, endIdx: i, startMs: step.ms, endMs: step.ms, steps: [] }
        }
        agentBuckets[agentDef.id].endIdx = i
        agentBuckets[agentDef.id].endMs  = step.ms
        agentBuckets[agentDef.id].steps.push(step)
        matched = true
        break
      }
    }
    if (!matched) {
      const fallbackId = `misc-${step.type}`
      if (!agentBuckets[fallbackId]) {
        agentBuckets[fallbackId] = {
          id: fallbackId, label: STEP_LABELS[step.type] || step.type,
          type: step.type, startIdx: i, endIdx: i, steps: []
        }
      }
      agentBuckets[fallbackId].endIdx = i
      agentBuckets[fallbackId].steps.push(step)
    }
  })

  return Object.values(agentBuckets)
    .sort((a, b) => a.startIdx - b.startIdx)
    .map(bucket => {
      const startPct  = (bucket.startIdx / total) * 100
      const endPct    = ((bucket.endIdx + 1) / total) * 100
      const widthPct  = Math.max(2, endPct - startPct)
      const durationMs = (bucket.startMs != null && bucket.endMs != null)
        ? Math.max(0, bucket.endMs - bucket.startMs)
        : null
      return { ...bucket, startPct, widthPct, count: bucket.steps.length, durationMs }
    })
})

const timeTicks = computed(() => {
  const total = traceData.value.length
  if (!total) return []
  const ticks = []
  for (let i = 0; i <= 4; i++) {
    const pct = i * 25
    const idx = Math.round((pct / 100) * total)
    const step = traceData.value[Math.min(idx, total - 1)]
    ticks.push({ pct, label: step?.ms ? step.ms + 'ms' : `t${idx}` })
  }
  return ticks
})

// ── Interactions ──────────────────────────────────────────────────────────────
function toggleStep(i) {
  if (openSteps.value.has(i)) openSteps.value.delete(i)
  else openSteps.value.add(i)
  openSteps.value = new Set(openSteps.value)
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '…' : str
}

function exportJson() {
  const blob = new Blob(
    [JSON.stringify(traceData.value, null, 2)],
    { type: 'application/json' }
  )
  const a = Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(blob),
    download: `trace_ia_doc_${props.documentId}.json`,
  })
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<style scoped>
.trace-panel {
  display: flex; flex-direction: column; gap: 14px;
  padding: 16px; font-family: 'DM Sans', -apple-system, sans-serif;
}

.trace-header {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 8px;
}
.trace-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 700; color: #1e293b;
}
.trace-badge {
  background: linear-gradient(135deg,#6366f1,#8b5cf6);
  color: white; font-size: 10px; font-weight: 800; padding: 2px 7px;
  border-radius: 6px; letter-spacing: .5px;
}
.trace-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.trace-meta    { font-size: 11.5px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }

.view-toggle {
  display: flex; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
}
.toggle-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 10px; background: white; border: none;
  font-size: 12px; font-weight: 600; color: #94a3b8; cursor: pointer;
  transition: all .15s;
}
.toggle-btn:first-child { border-right: 1px solid #e2e8f0; }
.toggle-btn--active { background: #eff6ff; color: #2563eb; }
.toggle-btn:hover:not(.toggle-btn--active) { background: #f8fafc; color: #475569; }

.trace-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 11px; border-radius: 8px;
  border: 1px solid #e2e8f0; background: white;
  font-size: 12px; font-weight: 600; color: #475569; cursor: pointer; transition: all .15s;
}
.trace-btn:hover { background: #f8fafc; border-color: #cbd5e1; }
.trace-btn--export:hover { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }

.trace-empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 40px 20px; text-align: center; color: #94a3b8;
}
.trace-empty-icon {
  width: 48px; height: 48px; border-radius: 12px;
  background: #f8fafc; display: flex; align-items: center; justify-content: center;
  font-size: 20px; color: #cbd5e1; margin-bottom: 4px;
}
.trace-empty p { font-size: 13.5px; margin: 0; }
.trace-empty-sub { font-size: 12px !important; }

.trace-steps { display: flex; flex-direction: column; gap: 0; }
.step { display: flex; gap: 0; position: relative; }
.step-line {
  position: absolute; left: 19px; top: 32px;
  width: 2px; background: #e2e8f0; bottom: 0; z-index: 0;
}
.step--action  .step-line { background: #dbeafe; }
.step--observe .step-line { background: #dcfce7; }
.step--answer  .step-line { background: #ede9fe; }
.step-dot-wrap {
  width: 40px; flex-shrink: 0; display: flex; justify-content: center;
  padding-top: 12px; position: relative; z-index: 1;
}
.step-dot {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; border: 2px solid;
}
.step--thought .step-dot { background: #fef3c7; border-color: #fde68a; color: #d97706; }
.step--action  .step-dot { background: #dbeafe; border-color: #bfdbfe; color: #2563eb; }
.step--observe .step-dot { background: #dcfce7; border-color: #a7f3d0; color: #059669; }
.step--answer  .step-dot { background: #ede9fe; border-color: #c4b5fd; color: #7c3aed; }
.step-card {
  flex: 1; margin: 8px 0 8px 8px; border-radius: 10px;
  border: 1px solid #f1f5f9; background: white;
  cursor: pointer; transition: box-shadow .15s; overflow: hidden;
}
.step-card:hover { box-shadow: 0 2px 8px rgba(15,23,42,.06); }
.step-card-head {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; flex-wrap: wrap;
}
.step-type-badge {
  padding: 2px 8px; border-radius: 6px; font-size: 10.5px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .4px;
}
.step-type--thought { background: #fef3c7; color: #d97706; }
.step-type--action  { background: #dbeafe; color: #2563eb; }
.step-type--observe { background: #dcfce7; color: #059669; }
.step-type--answer  { background: #ede9fe; color: #7c3aed; }
.step-agent { font-size: 11px; font-weight: 700; color: #64748b; font-family: 'JetBrains Mono', monospace; }
.step-ms    { font-size: 11px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; margin-left: auto; }
.step-chevron { font-size: 10px; color: #cbd5e1; transition: transform .2s; margin-left: 4px; }
.step-chevron--open { transform: rotate(180deg); }
.step-content { padding: 0 12px 10px; border-top: 1px solid #f8fafc; }
.step-text {
  font-size: 12px; font-family: 'JetBrains Mono', monospace;
  color: #374151; white-space: pre-wrap; word-break: break-word;
  margin: 8px 0 0; background: #f8fafc; border-radius: 6px;
  padding: 8px 10px; max-height: 200px; overflow-y: auto;
}

/* ── TIMELINE / GANTT ── */
.timeline-wrap { display: flex; flex-direction: column; gap: 6px; }

.tl-header { display: flex; align-items: center; gap: 0; }
.tl-label-col {
  width: 130px; flex-shrink: 0;
  font-size: 10px; color: #94a3b8; font-family: 'JetBrains Mono', monospace;
  padding-right: 10px;
}
.tl-axis {
  flex: 1; position: relative; height: 18px; border-bottom: 1px dashed #e2e8f0;
}
.tl-tick {
  position: absolute; transform: translateX(-50%);
  font-size: 9px; color: #94a3b8; font-family: 'JetBrains Mono', monospace;
  top: 0; white-space: nowrap;
}

.tl-total { display: flex; align-items: center; gap: 0; margin-bottom: 6px; }
.tl-total-label {
  font-size: 10px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.4px;
}
.tl-bar--total {
  background: linear-gradient(90deg, #e0e7ff, #c7d2fe);
  border: 1px solid #a5b4fc;
  color: #4338ca; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700;
}

.tl-rows { display: flex; flex-direction: column; gap: 5px; }
.tl-row {
  display: flex; align-items: center; gap: 0;
  position: relative; border-radius: 6px; transition: background 0.15s;
}
.tl-row--hovered { background: #f8fafc; }

.tl-label-col { display: flex; align-items: center; gap: 5px; }
.tl-agent-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.tl-dot--thought { background: #d97706; }
.tl-dot--action  { background: #2563eb; }
.tl-dot--observe { background: #059669; }
.tl-dot--answer  { background: #7c3aed; }
.tl-agent-name {
  font-size: 11px; font-weight: 600; color: #1e293b;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 95px;
}
.tl-step-count { font-size: 9px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; margin-left: 2px; }

.tl-track { flex: 1; position: relative; height: 26px; }
.tl-bar-bg { position: absolute; inset: 6px 0; background: #f1f5f9; border-radius: 4px; }
.tl-bar {
  position: absolute; top: 4px; bottom: 4px;
  border-radius: 5px; display: flex; align-items: center; padding: 0 8px;
  font-size: 9.5px; font-weight: 700; white-space: nowrap;
  overflow: hidden; min-width: 6px;
  transition: left 0.4s ease, width 0.4s ease;
  animation: bar-slide-in 0.5s ease;
}
@keyframes bar-slide-in { from { opacity: 0; transform: scaleX(0.4); } to { opacity: 1; transform: scaleX(1); } }

.tl-bar--thought { background: #fef3c7; border: 1px solid #fde68a; color: #92400e; }
.tl-bar--action  { background: #dbeafe; border: 1px solid #93c5fd; color: #1e40af; }
.tl-bar--observe { background: #d1fae5; border: 1px solid #6ee7b7; color: #065f46; }
.tl-bar--answer  { background: #ede9fe; border: 1px solid #c4b5fd; color: #5b21b6; }

.tl-bar-label { font-family: 'JetBrains Mono', monospace; font-size: 8.5px; opacity: 0.8; }

.tl-tooltip {
  position: absolute; left: 140px; top: 32px; z-index: 20;
  background: #0f172a; border-radius: 10px; padding: 10px 12px;
  width: 260px; box-shadow: 0 8px 24px rgba(0,0,0,0.2);
  pointer-events: none; animation: tooltip-in 0.15s ease;
}
@keyframes tooltip-in { from { opacity:0; transform:translateY(-4px) } to { opacity:1; transform:none } }
.tl-tt-title {
  font-size: 11px; font-weight: 700; color: #f8fafc;
  font-family: 'JetBrains Mono', monospace; margin-bottom: 7px; padding-bottom: 6px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.tl-tt-row { display: flex; align-items: flex-start; gap: 6px; margin-bottom: 4px; }
.tl-tt-badge {
  font-size: 8.5px; font-weight: 700; padding: 1px 5px; border-radius: 4px;
  text-transform: uppercase; flex-shrink: 0; margin-top: 1px;
}
.tl-tt-badge--thought { background: #fef3c7; color: #92400e; }
.tl-tt-badge--action  { background: #dbeafe; color: #1e40af; }
.tl-tt-badge--observe { background: #d1fae5; color: #065f46; }
.tl-tt-badge--answer  { background: #ede9fe; color: #5b21b6; }
.tl-tt-text { font-size: 10px; color: #94a3b8; line-height: 1.4; }
.tl-tt-more { font-size: 9.5px; color: #64748b; margin-top: 4px; font-style: italic; }

.tl-legend {
  display: flex; gap: 14px; flex-wrap: wrap;
  padding-top: 8px; border-top: 1px solid #f1f5f9; margin-top: 4px;
}
.tl-leg-item { display: flex; align-items: center; gap: 4px; font-size: 10px; color: #94a3b8; font-weight: 600; }
.tl-leg-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
</style>