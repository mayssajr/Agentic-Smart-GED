<template>
  <div class="agent-graph-wrap">

    <!-- Header -->
    <div class="graph-header">
      <div class="graph-title">
        <span class="graph-badge">LIVE</span>
        <span>Pipeline Agentique</span>
      </div>
      <div class="graph-legend">
        <span class="leg-item"><span class="leg-dot leg-dot--idle"></span>Idle</span>
        <span class="leg-item"><span class="leg-dot leg-dot--running"></span>Actif</span>
        <span class="leg-item"><span class="leg-dot leg-dot--done"></span>Terminé</span>
        <span class="leg-item"><span class="leg-dot leg-dot--error"></span>Erreur</span>
      </div>
    </div>

    <!-- SVG Graph -->
    <div class="graph-svg-wrap">
      <svg :viewBox="`0 0 ${W} ${H}`" class="graph-svg" xmlns="http://www.w3.org/2000/svg">

        <!-- ── Edges ── -->
        <g class="edges">
          <path v-for="e in edges" :key="e.id"
            :d="e.d" fill="none" stroke-width="1.5" stroke-linecap="round"
            :class="['edge', isEdgeActive(e) ? 'edge--active' : 'edge--idle']"
          />
          <!-- Flow dots on active edges -->
          <circle v-for="e in edges.filter(isEdgeActive)" :key="'dot-'+e.id"
            r="3.5" :class="['flow-dot', `flow-dot--${e.color}`]"
            :style="`--path-len:${e.len}px`"
          >
            <animateMotion :dur="(e.len / 80).toFixed(1) + 's'" repeatCount="indefinite" calcMode="linear">
              <mpath :href="'#path-'+e.id"/>
            </animateMotion>
          </circle>
          <!-- Hidden paths for animateMotion -->
          <path v-for="e in edges" :key="'p-'+e.id"
            :id="'path-'+e.id" :d="e.d" fill="none" stroke="none" pointer-events="none"/>
        </g>

        <!-- ── Nodes ── -->
        <g v-for="n in nodes" :key="n.id"
          class="node-group"
          :class="`node-group--${nodeState(n.id)}`"
          @mouseenter="hoveredNode = n.id"
          @mouseleave="hoveredNode = null"
        >
          <!-- Pulse ring (running state) -->
          <circle v-if="nodeState(n.id) === 'running'"
            :cx="n.x" :cy="n.y" :r="NR + 6"
            class="node-ring-pulse" fill="none" stroke-width="2"
          />
          <!-- Glow shadow (done state) -->
          <circle v-if="nodeState(n.id) === 'done'"
            :cx="n.x" :cy="n.y" :r="NR + 4"
            class="node-glow-done" fill="none" stroke-width="3"
          />
          <!-- Main circle -->
          <circle
            :cx="n.x" :cy="n.y" :r="NR"
            :class="['node-circle', `node-circle--${nodeState(n.id)}`]"
          />
          <!-- Abbrev text -->
          <text :x="n.x" :y="n.y + 1" text-anchor="middle" dominant-baseline="middle"
            :class="['node-abbr', `node-abbr--${nodeState(n.id)}`]">
            {{ n.abbr }}
          </text>
          <!-- Name label -->
          <text :x="n.x" :y="n.y + NR + 13" text-anchor="middle"
            :class="['node-label', `node-label--${nodeState(n.id)}`]">
            {{ n.label }}
          </text>
          <!-- Check icon (done) -->
          <text v-if="nodeState(n.id) === 'done'" :x="n.x + NR - 3" :y="n.y - NR + 3"
            text-anchor="middle" dominant-baseline="middle" class="node-check">✓</text>
        </g>

        <!-- ── Tooltip ── -->
        <g v-if="hoveredNode" class="tooltip-group">
          <rect
            :x="tooltipX - 60" :y="tooltipY - 40"
            width="120" height="38" rx="6"
            class="tooltip-bg"
          />
          <text :x="tooltipX" :y="tooltipY - 27" text-anchor="middle" class="tooltip-text tooltip-name">
            {{ hoveredNodeDef?.name }}
          </text>
          <text :x="tooltipX" :y="tooltipY - 12" text-anchor="middle" class="tooltip-text tooltip-task">
            {{ hoveredNodeDef?.task }}
          </text>
        </g>

      </svg>
    </div>

    <!-- Last run info bar -->
    <div class="graph-footer" v-if="traceSteps.length">
      <span class="footer-stat">
        <i class="fas fa-list-check"></i> {{ traceSteps.length }} étapes
      </span>
      <span class="footer-stat" v-if="processingMs">
        <i class="fas fa-stopwatch"></i> {{ formatMs(processingMs) }}
      </span>
      <span class="footer-stat">
        <i class="fas fa-microchip"></i> {{ doneCount }}/{{ nodes.length }} agents complétés
      </span>
      <span class="footer-status" :class="allDone ? 'st-ok' : 'st-run'">
        {{ allDone ? '✓ Run complet' : '⟳ En cours...' }}
      </span>
    </div>
    <div class="graph-footer graph-footer--empty" v-else>
      <i class="fas fa-circle-info"></i>
      Lancez une analyse pour voir le pipeline s'activer en temps réel
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  reactTrace:   { type: Array,   default: () => [] },  // trace passée depuis parent (legacy)
  systemOnline: { type: Boolean, default: true    },
  documentId:   { type: [String, Number], default: '' }, // id du document en cours d'analyse
  aiBaseUrl:    { type: String,  default: ''       },
})

// ── Layout constants ──────────────────────────────────────────────────────────
const W  = 520
const H  = 180
const NR = 22

// ── Node definitions ──────────────────────────────────────────────────────────
const nodes = [
  { id: 'orch',       x:  52, y: 90,  abbr: 'ORC', label: 'Orchestrator', name: 'OrchestratorAgent',  task: "Chef d'orchestration"      },
  { id: 'classifier', x: 165, y: 55,  abbr: 'CLS', label: 'Classifier',   name: 'ClassifierAgent',    task: 'Classification des docs'   },
  { id: 'summarizer', x: 165, y: 135, abbr: 'SUM', label: 'Summarizer',   name: 'SummarizerAgent',    task: 'Génération de résumés'      },
  { id: 'rag',        x: 278, y: 55,  abbr: 'RAG', label: 'RAG Index',    name: 'RAG Pipeline',       task: 'Indexation ChromaDB'        },
  { id: 'task',       x: 278, y: 135, abbr: 'TSK', label: 'TaskAgent',    name: 'TaskAgent',          task: 'Tâches + statut MiniGED'   },
  { id: 'score',      x: 390, y: 90,  abbr: 'SCR', label: 'ScoreAgent',   name: 'ScoreAgent',         task: 'Scoring candidat IA'        },
  { id: 'email',      x: 468, y: 50,  abbr: 'MAI', label: 'EmailAgent',   name: 'EmailAgent',         task: 'Rédaction & envoi emails'  },
  { id: 'ace',        x: 468, y: 135, abbr: 'ACE', label: 'ACE Router',   name: 'ACE Router',         task: 'Apprentissage & playbook'  },
]

// ── Edge definitions ──────────────────────────────────────────────────────────
function edgePath(fromId, toId) {
  const f = nodes.find(n => n.id === fromId)
  const t = nodes.find(n => n.id === toId)
  const dx = t.x - f.x, dy = t.y - f.y
  const dist = Math.sqrt(dx * dx + dy * dy)
  const ux = dx / dist, uy = dy / dist
  const sx = f.x + ux * (NR + 2), sy = f.y + uy * (NR + 2)
  const ex = t.x - ux * (NR + 5), ey = t.y - uy * (NR + 5)
  const mx = (sx + ex) / 2, my = (sy + ey) / 2
  const perp = dist > 100 ? 12 : 0
  const cpx = mx - uy * perp, cpy = my + ux * perp
  return `M${sx.toFixed(1)},${sy.toFixed(1)} Q${cpx.toFixed(1)},${cpy.toFixed(1)} ${ex.toFixed(1)},${ey.toFixed(1)}`
}

const edges = [
  { id: 'orch-clf',   from: 'orch',       to: 'classifier', color: 'blue'   },
  { id: 'orch-sum',   from: 'orch',       to: 'summarizer', color: 'blue'   },
  { id: 'clf-rag',    from: 'classifier', to: 'rag',        color: 'cyan'   },
  { id: 'sum-task',   from: 'summarizer', to: 'task',       color: 'amber'  },
  { id: 'rag-score',  from: 'rag',        to: 'score',      color: 'green'  },
  { id: 'task-score', from: 'task',       to: 'score',      color: 'green'  },
  { id: 'score-mail', from: 'score',      to: 'email',      color: 'pink'   },
  { id: 'score-ace',  from: 'score',      to: 'ace',        color: 'purple' },
].map(e => ({ ...e, d: edgePath(e.from, e.to), len: 100 }))

// ── Keyword mapping — correspond aux vrais contenus de trace orchestrateur ───
// Les mots-clés sont tirés directement des _step("action"/"observe") dans orchestrator.py
const AGENT_KEYWORDS = {
  orch:       ['Analyse classify', 'Résumé |', 'orchestrat', 'Orchestrat'],
  classifier: ['ClassifierAgent', 'ClassifierAgent →', 'classifier'],
  summarizer: ['SummarizerAgent', 'SummarizerAgent →', 'summarizer', 'résumé='],
  rag:        ['RAG', 'rag', 'ChromaDB', 'index', 'chunks', 'RAG indexé'],
  task:       ['TaskAgent', 'TaskAgent →', 'tâche(s) créée', 'Statut candidat', 'update_candidate_status'],
  score:      ['ScoreAgent', 'ScoreAgent →', 'score=', 'scoring', 'AiScore'],
  email:      ['EmailAgent', 'EmailAgent.', 'email', 'Email', 'brouillon', 'EMAIL PREVIEW', 'convocation'],
  ace:        ['ACE', 'ace', 'playbook', 'AceDecisionAgent', 'ace_post_score', 'Override'],
}

// ── Polling state ─────────────────────────────────────────────────────────────
const polledTrace    = ref([])
const processingMs   = ref(0)
const pollTimer      = ref(null)
const lastDocId      = ref('')

const AI_BASE = computed(() => {
  if (props.aiBaseUrl) return props.aiBaseUrl.replace(/\/$/, '')
  return (typeof import.meta !== 'undefined' && import.meta.env?.VITE_AI_BASE_URL
    ? import.meta.env.VITE_AI_BASE_URL
    : 'http://localhost:8000'
  ).replace(/\/$/, '')
})

async function fetchTrace(docId) {
  if (!docId) return
  try {
    const r = await fetch(`${AI_BASE.value}/trace/${docId}`)
    if (!r.ok) return
    const data = await r.json()
    if (data.found && Array.isArray(data.trace)) {
      polledTrace.value  = data.trace
      if (data.processing_ms) processingMs.value = data.processing_ms
      // Sauvegarder en localStorage pour compatibilité
      try {
        localStorage.setItem(`ai_trace_${docId}`, JSON.stringify(data.trace))
      } catch {}
    }
  } catch {}
}

// Démarrer le polling quand documentId change
watch(() => props.documentId, (newId) => {
  if (!newId) return
  lastDocId.value = String(newId)
  polledTrace.value = []
  processingMs.value = 0
  // Poll immédiatement puis toutes les 3s
  fetchTrace(newId)
  clearInterval(pollTimer.value)
  pollTimer.value = setInterval(() => {
    fetchTrace(newId)
    // Stopper le polling quand l'analyse est terminée
    if (allDone.value) clearInterval(pollTimer.value)
  }, 3000)
}, { immediate: true })

onMounted(() => {
  // Essayer de charger la dernière trace connue depuis localStorage
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('ai_trace_'))
    if (keys.length) {
      const sorted = keys.sort((a, b) => {
        return (parseInt(b.replace('ai_trace_', '')) || 0) - (parseInt(a.replace('ai_trace_', '')) || 0)
      })
      const stored = JSON.parse(localStorage.getItem(sorted[0]) || '[]')
      if (stored.length && !polledTrace.value.length) {
        polledTrace.value = stored
        // Essayer de récupérer le docId depuis la clé
        const storedDocId = sorted[0].replace('ai_trace_', '')
        if (storedDocId && !props.documentId) {
          fetchTrace(storedDocId)
        }
      }
    }
  } catch {}
})

onUnmounted(() => clearInterval(pollTimer.value))

// ── Résoudre la trace active ───────────────────────────────────────────────────
// Priorité : 1) trace polled depuis API  2) prop reactTrace  3) localStorage
const traceSteps = computed(() => {
  if (polledTrace.value.length) return polledTrace.value
  if (props.reactTrace?.length) return props.reactTrace
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('ai_trace_'))
    if (!keys.length) return []
    const sorted = keys.sort((a, b) =>
      (parseInt(b.replace('ai_trace_', '')) || 0) - (parseInt(a.replace('ai_trace_', '')) || 0))
    return JSON.parse(localStorage.getItem(sorted[0]) || '[]')
  } catch { return [] }
})

// ── Parser les états agents depuis la trace ───────────────────────────────────
const agentStates = computed(() => {
  const steps  = traceSteps.value
  const states = {}
  if (!steps.length) return states

  // Orchestrateur est toujours actif dès qu'il y a une trace
  states['orch'] = 'running'

  steps.forEach((step, i) => {
    const text    = (step.content || step.agent || '')
    const isLast  = i === steps.length - 1

    for (const [agentId, keywords] of Object.entries(AGENT_KEYWORDS)) {
      if (!keywords.some(kw => text.includes(kw))) continue

      const type = step.type || ''

      if (type === 'action') {
        // Step "action" = l'agent est appelé → running
        // Si ce n'est pas le dernier step, il est potentiellement déjà done
        // On met running; un step "observe" suivant le marquera done
        if (!states[agentId] || states[agentId] === 'idle') {
          states[agentId] = 'running'
        }
      } else if (type === 'observe') {
        // Step "observe" = résultat reçu → done
        states[agentId] = 'done'
      } else if (type === 'thought') {
        if (!states[agentId]) states[agentId] = 'running'
      } else if (type === 'answer') {
        states[agentId] = 'done'
      }
    }
  })

  // Si la trace contient une étape "answer" → orchestrateur terminé
  if (steps.some(s => s.type === 'answer' || (s.type === 'observe' && s.content?.includes('persistée')))) {
    states['orch'] = 'done'
  }

  // Tout agent "running" qui a un "observe" subséquent le marquant → done
  // (deuxième passe pour les agents qui ont action + observe séquentiels)
  const actionIdx = {}
  steps.forEach((step, i) => {
    const text = step.content || ''
    if (step.type === 'action') {
      for (const [id, kws] of Object.entries(AGENT_KEYWORDS)) {
        if (kws.some(kw => text.includes(kw))) actionIdx[id] = i
      }
    } else if (step.type === 'observe') {
      for (const [id, kws] of Object.entries(AGENT_KEYWORDS)) {
        if (kws.some(kw => text.includes(kw)) && actionIdx[id] !== undefined) {
          states[id] = 'done'
        }
      }
    }
  })

  return states
})

function nodeState(id) {
  if (!props.systemOnline) return 'error'
  return agentStates.value[id] || 'idle'
}

function isEdgeActive(e) {
  const from = nodeState(e.from)
  const to   = nodeState(e.to)
  return from === 'running' || from === 'done' || to === 'running' || to === 'done'
}

// ── Stats ─────────────────────────────────────────────────────────────────────
const doneCount = computed(() => nodes.filter(n => nodeState(n.id) === 'done').length)

const allDone = computed(() => {
  const steps = traceSteps.value
  return steps.some(s =>
    s.type === 'answer' ||
    (s.type === 'observe' && s.content?.includes('Trace persistée'))
  )
})

function formatMs(ms) {
  if (!ms || ms <= 0) return ''
  if (ms < 1000) return ms + ' ms'
  const totalSec = Math.round(ms / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  if (min === 0) return sec + 's'
  return min + 'min ' + (sec > 0 ? sec + 's' : '')
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
const hoveredNode    = ref(null)
const hoveredNodeDef = computed(() => nodes.find(n => n.id === hoveredNode.value))
const tooltipX       = computed(() => hoveredNodeDef.value?.x ?? 0)
const tooltipY       = computed(() => (hoveredNodeDef.value?.y ?? 0) - NR - 2)
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&display=swap');

.agent-graph-wrap {
  display: flex; flex-direction: column; gap: 0;
  font-family: 'DM Sans', -apple-system, sans-serif;
}

/* ── Header ── */
.graph-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px; flex-wrap: wrap; gap: 6px;
}
.graph-title {
  display: flex; align-items: center; gap: 7px;
  font-size: 12px; font-weight: 700; color: #1e293b;
  text-transform: uppercase; letter-spacing: 0.4px;
}
.graph-badge {
  font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;
  background: #dcfce7; color: #16a34a; letter-spacing: 1px;
  animation: badge-pulse 2s ease-in-out infinite;
}
@keyframes badge-pulse { 0%,100% { opacity:1 } 50% { opacity:0.6 } }

.graph-legend { display: flex; gap: 10px; flex-wrap: wrap; }
.leg-item {
  display: flex; align-items: center; gap: 4px;
  font-size: 10px; color: #94a3b8; font-weight: 600;
}
.leg-dot { width: 7px; height: 7px; border-radius: 50%; }
.leg-dot--idle    { background: #e2e8f0; border: 1.5px solid #cbd5e1; }
.leg-dot--running { background: #dbeafe; border: 1.5px solid #2563eb; animation: badge-pulse 1s infinite; }
.leg-dot--done    { background: #dcfce7; border: 1.5px solid #059669; }
.leg-dot--error   { background: #fee2e2; border: 1.5px solid #ef4444; }

/* ── SVG ── */
.graph-svg-wrap {
  background: #fafbff; border: 1px solid #e8edf5; border-radius: 12px; overflow: hidden;
}
.graph-svg { width: 100%; display: block; }

/* ── Edges ── */
.edge { transition: stroke 0.4s ease; }
.edge--idle   { stroke: #e2e8f0; stroke-dasharray: none; }
.edge--active { stroke: #bfdbfe; stroke-dasharray: 5 4; animation: edge-flow 0.8s linear infinite; }
@keyframes edge-flow { to { stroke-dashoffset: -18; } }

/* ── Flow dots ── */
.flow-dot { opacity: 0.9; }
.flow-dot--blue   { fill: #2563eb; }
.flow-dot--cyan   { fill: #0891b2; }
.flow-dot--amber  { fill: #d97706; }
.flow-dot--green  { fill: #059669; }
.flow-dot--pink   { fill: #db2777; }
.flow-dot--purple { fill: #7c3aed; }

/* ── Nodes ── */
.node-group { cursor: pointer; transition: opacity 0.2s; }
.node-group:hover { opacity: 0.85; }

.node-circle { transition: fill 0.4s ease, stroke 0.4s ease; stroke-width: 2; }
.node-circle--idle    { fill: #f8fafc; stroke: #cbd5e1; }
.node-circle--running { fill: #eff6ff; stroke: #2563eb; }
.node-circle--done    { fill: #f0fdf4; stroke: #059669; }
.node-circle--error   { fill: #fef2f2; stroke: #ef4444; }

.node-ring-pulse {
  stroke: #2563eb; opacity: 0.4;
  animation: ring-pulse 1.2s ease-out infinite;
}
@keyframes ring-pulse { 0% { r: 26; opacity: 0.5; } 100% { r: 34; opacity: 0; } }

.node-glow-done { stroke: #059669; opacity: 0.2; }

.node-abbr {
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px; font-weight: 700; letter-spacing: 0.5px; pointer-events: none;
}
.node-abbr--idle    { fill: #94a3b8; }
.node-abbr--running { fill: #1d4ed8; }
.node-abbr--done    { fill: #059669; }
.node-abbr--error   { fill: #dc2626; }

.node-label { font-size: 8px; font-weight: 600; pointer-events: none; }
.node-label--idle    { fill: #94a3b8; }
.node-label--running { fill: #1d4ed8; font-weight: 700; }
.node-label--done    { fill: #059669; }
.node-label--error   { fill: #dc2626; }

.node-check { font-size: 8px; fill: #059669; font-weight: 900; pointer-events: none; }

/* ── Tooltip ── */
.tooltip-bg   { fill: #0f172a; opacity: 0.92; }
.tooltip-text { pointer-events: none; }
.tooltip-name { font-family: 'JetBrains Mono', monospace; font-size: 8px; font-weight: 700; fill: #f8fafc; }
.tooltip-task { font-size: 7.5px; fill: #94a3b8; }

/* ── Footer ── */
.graph-footer {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding: 8px 4px 0;
}
.graph-footer--empty {
  font-size: 11px; color: #94a3b8; justify-content: center; padding: 10px 0 2px; gap: 6px;
}
.graph-footer--empty i { color: #cbd5e1; }
.footer-stat {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #64748b; font-family: 'JetBrains Mono', monospace;
}
.footer-stat i { color: #94a3b8; font-size: 10px; }
.footer-status { margin-left: auto; font-size: 11px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.st-ok  { color: #059669; }
.st-run { color: #2563eb; }
</style>