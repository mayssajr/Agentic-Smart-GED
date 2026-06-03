<template>
  <div class="home-page">

    <!-- Header -->
    <div class="page-top">
      <div>
        <h1 class="page-title">Vue d'ensemble</h1>
        <p class="page-sub">Système agentique · <span class="live-dot-wrap"><span class="live-dot"></span>Temps réel</span></p>
      </div>
      <div class="top-right">
        <span class="last-sync">Sync: {{ lastSyncTime }}</span>
        <button class="refresh-btn" @click="loadAll" :class="{ spinning: loading }">
          <i class="fas fa-rotate-right"></i>
        </button>
      </div>
    </div>

    <!-- Error banner -->
    <div class="error-banner" v-if="error">
      <i class="fas fa-circle-exclamation"></i>
      {{ error }}
      <button @click="error = null"><i class="fas fa-xmark"></i></button>
    </div>

    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card" v-for="kpi in kpis" :key="kpi.id">
        <div class="kpi-left">
          <div class="kpi-icon-wrap" :style="{ background: kpi.bg }">
            <i :class="kpi.icon" :style="{ color: kpi.color }"></i>
          </div>
        </div>
        <div class="kpi-right">
          <div class="kpi-value" :style="{ color: kpi.color }">
            <span v-if="loading" class="skeleton-val"></span>
            <span v-else>{{ kpi.display }}</span>
          </div>
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-sub" :class="kpi.subClass">{{ kpi.sub }}</div>
        </div>
        <div class="kpi-bar-bottom" :style="{ background: kpi.color, opacity: 0.12 }"></div>
        <div class="kpi-bar-fill" :style="{ background: kpi.color, width: kpi.fillPct + '%' }"></div>
      </div>
    </div>

    <!-- Middle grid -->
    <div class="mid-grid">

      <!-- System health + Agents -->
      <div class="card health-card">
        <!-- <div class="card-header">
          <span class="card-title"><i class="fas fa-heart-pulse"></i> Santé Système</span>
          <span class="status-chip" :class="systemOk ? 'chip-ok' : 'chip-err'">
            {{ systemOk ? 'Opérationnel' : 'Dégradé' }}
          </span>
        </div>
        <div class="health-rows">
          <div class="health-row" v-for="h in healthItems" :key="h.id">
            <div class="health-dot" :class="h.ok ? 'dot-ok' : 'dot-err'"></div>
            <div class="health-name">{{ h.name }}</div>
            <div class="health-val">{{ h.value }}</div>
          </div>
          <div class="health-row" v-if="!healthItems.length && loading">
            <div class="sk-row" style="width:100%; height:12px; margin:0"></div>
          </div>
          <div class="health-empty" v-if="!healthItems.length && !loading">
            <i class="fas fa-plug-circle-xmark"></i> Backend IA non disponible
          </div>
        </div> -->

        <AgentGraph
          :react-trace="[]"
          :system-online="systemOk"
          :document-id="latestDocId"
          :ai-base-url="AI_BASE"
        />
      </div>

      <!-- Doc types donut -->
      <div class="card types-card">
        <div class="card-header">
          <span class="card-title"><i class="fas fa-chart-pie"></i> Types de Documents</span>
          <span class="total-badge">{{ totalDocs }} total</span>
        </div>

        <div class="donut-wrap">
          <svg viewBox="0 0 160 160" class="donut-svg">
            <circle cx="80" cy="80" r="58" fill="none" stroke="#f1f5f9" stroke-width="22"/>
            <circle
              v-for="(seg, i) in donutSegments" :key="i"
              cx="80" cy="80" r="58"
              fill="none"
              :stroke="seg.color"
              stroke-width="22"
              :stroke-dasharray="`${seg.dash} ${364 - seg.dash}`"
              :stroke-dashoffset="seg.offset"
              style="transition: stroke-dashoffset 1s ease"
            />
            <text x="80" y="75" text-anchor="middle" class="d-center-val">{{ totalDocs }}</text>
            <text x="80" y="91" text-anchor="middle" class="d-center-lbl">DOCS</text>
          </svg>
        </div>

        <div class="type-list">
          <div class="type-row" v-for="t in docTypes" :key="t.label">
            <div class="type-dot" :style="{ background: t.color }"></div>
            <div class="type-label">{{ t.label }}</div>
            <div class="type-bar-wrap">
              <div class="type-bar" :style="{ width: (totalDocs ? t.count / totalDocs * 100 : 0) + '%', background: t.color }"></div>
            </div>
            <div class="type-count">{{ t.count }}</div>
          </div>
          <div class="type-empty" v-if="!docTypes.length && !loading">
            <i class="fas fa-chart-pie text-slate-300"></i> Aucune donnée de type
          </div>
        </div>
      </div>

      <!-- Processing status -->
      <div class="card status-card">
        <div class="card-header">
          <span class="card-title"><i class="fas fa-layer-group"></i> État Traitement</span>
        </div>

        <div class="status-rings">
          <div class="ring-item" v-for="s in statusRings" :key="s.id">
            <svg viewBox="0 0 80 80" class="ring-svg">
              <circle cx="40" cy="40" r="30" fill="none" stroke="#f1f5f9" stroke-width="8"/>
              <circle cx="40" cy="40" r="30" fill="none"
                :stroke="s.color" stroke-width="8" stroke-linecap="round"
                :stroke-dasharray="`${188 * s.pct / 100} 188`"
                transform="rotate(-90 40 40)"
                style="transition: stroke-dasharray 1s ease"/>
              <text x="40" y="44" text-anchor="middle" class="ring-num">{{ s.count }}</text>
            </svg>
            <div class="ring-lbl">{{ s.label }}</div>
            <div class="ring-pct" :style="{ color: s.color }">{{ s.pct }}%</div>
          </div>
        </div>

        <div class="pending-alert" v-if="pendingDocs > 0">
          <i class="fas fa-triangle-exclamation"></i>
          <div>
            <strong>{{ pendingDocs }} document(s) non traités</strong>
            <div class="alert-sub">En attente d'analyse OCR / IA</div>
          </div>
        </div>

        <div class="conv-section" v-if="convStats.total > 0 || convStats.messages > 0">
          <div class="card-subtitle"><i class="fas fa-comments"></i> Conversations IA</div>
          <div class="conv-row">
            <div class="conv-stat">
              <div class="conv-val">{{ convStats.total }}</div>
              <div class="conv-lbl">Conversations</div>
            </div>
            <div class="conv-stat">
              <div class="conv-val">{{ convStats.messages }}</div>
              <div class="conv-lbl">Messages</div>
            </div>
            <div class="conv-stat">
              <div class="conv-val">{{ convStats.signed }}</div>
              <div class="conv-lbl">Signés</div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Recent documents table -->
    <div class="card feed-card">
      <div class="card-header">
        <span class="card-title"><i class="fas fa-clock-rotate-left"></i> Derniers Documents Analysés</span>
        <a class="see-all" @click="$router.push('/documents')">Voir tous <i class="fas fa-arrow-right"></i></a>
      </div>

      <div class="feed-table" v-if="recentDocs.length">
        <div class="feed-row feed-head">
          <span>Document</span><span>Type IA</span><span>Date analyse</span><span>Statut</span>
        </div>
        <div class="feed-row" v-for="doc in recentDocs" :key="doc.id"
          @click="$router.push('/document/' + doc.id)">
          <span class="feed-name">
            <i class="fas fa-file-pdf" style="color:#ef4444"></i>
            {{ doc.title }}
          </span>
          <span class="feed-type-badge"
            :style="{ background: typeColor(doc.type) + '18', color: typeColor(doc.type) }">
            {{ doc.type || '—' }}
          </span>
          <span class="feed-date">{{ doc.analyzedAt || '—' }}</span>
          <span class="feed-status" :class="doc.analyzed ? 'st-ok' : 'st-pending'">
            <i :class="doc.analyzed ? 'fas fa-check-circle' : 'fas fa-hourglass-half'"></i>
            {{ doc.analyzed ? 'Analysé' : 'En attente' }}
          </span>
        </div>
      </div>

      <div class="feed-empty" v-else-if="!loading">
        <i class="fas fa-inbox"></i>
        <p>Aucun document trouvé</p>
      </div>

      <div v-else>
        <div class="sk-row" v-for="i in 5" :key="i"></div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import apiClient from '../services/api'
import AgentGraph from '../components/AgentGraph.vue'

// ── State ─────────────────────────────────────────────────────────────────────
const loading      = ref(false)
const error        = ref(null)
const lastSyncTime = ref('—')

const dashStats  = ref({})   // GET /dashboard/stats  ← MiniGED C# API proxied via apiClient
const agentStats = ref({})   // GET /stats            ← FastAPI
const healthData = ref({})   // GET /health           ← FastAPI
const allDocs    = ref([])   // GET /document         ← MiniGED C# API
const aiDocs     = ref({})   // GET /documents/ai-enriched ← FastAPI

// ── AI backend base URL (configurable via .env VITE_AI_BASE_URL) ──────────────
const AI_BASE = (import.meta.env?.VITE_AI_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

async function fetchAi(path) {
  const token = localStorage.getItem('token') || ''
  const res = await fetch(`${AI_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`)
  return res.json()
}

async function loadAll() {
  loading.value = true
  error.value   = null
  const errs    = []

  const [dash, agt, hlth, docs, ai] = await Promise.allSettled([
    apiClient.get('/dashboard/stats').then(r => r.data),
    fetchAi('/stats'),
    fetchAi('/health'),
    apiClient.get('/document').then(r => r.data),
    fetchAi('/documents/ai-enriched'),
  ])

  if (dash.status  === 'fulfilled') dashStats.value  = dash.value  || {}
  else errs.push('dashboard/stats')

  if (agt.status   === 'fulfilled') agentStats.value = agt.value   || {}
  else errs.push('stats IA')

  if (hlth.status  === 'fulfilled') healthData.value = hlth.value  || {}
  else errs.push('health IA')

  if (docs.status  === 'fulfilled') allDocs.value    = Array.isArray(docs.value) ? docs.value : []
  else errs.push('documents')

  if (ai.status    === 'fulfilled') aiDocs.value     = ai.value    || {}
  else errs.push('ai-enriched')

  if (errs.length) {
    error.value = `Données partielles — certains services non disponibles : ${errs.join(', ')}`
  }

  lastSyncTime.value = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  loading.value = false
}

// ── Computed from real data ───────────────────────────────────────────────────

const totalDocs = computed(() =>
  dashStats.value?.totalDocuments ?? allDocs.value.length ?? 0
)

const analyzedCount = computed(() =>
  dashStats.value?.analyzedCount ?? 0
)

const pendingDocs = computed(() =>
  Math.max(0, totalDocs.value - analyzedCount.value)
)

const avgMs = computed(() => agentStats.value?.avg_processing_ms ?? 0)

function formatAvgMs(ms) {
  if (!ms || ms <= 0) return '—'
  if (ms < 1000) return ms + ' ms'
  const totalSec = Math.round(ms / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  if (min === 0) return sec + 's'
  return min + 'min ' + (sec > 0 ? sec + 's' : '')
}

const convStats = computed(() => ({
  total:    agentStats.value?.conversations  ?? 0,
  messages: agentStats.value?.total_messages ?? 0,
  signed:   agentStats.value?.signed_count   ?? 0,
}))

const systemOk = computed(() => healthData.value?.status === 'ok')

// ── KPIs ──────────────────────────────────────────────────────────────────────
const kpis = computed(() => {
  const total    = totalDocs.value
  const analyzed = analyzedCount.value
  const pending  = pendingDocs.value
  const pct      = total > 0 ? Math.round(analyzed * 100 / total) : 0

  return [
    {
      id: 1, label: 'Documents Total',
      display: total,
      sub: analyzed + ' analysés',
      subClass: 'sub-ok',
      icon: 'fas fa-folder-open', color: '#2563eb', bg: '#eff6ff',
      fillPct: Math.min(100, total / 5),
    },
    {
      id: 2, label: 'Taux d\'analyse IA',
      display: pct + '%',
      sub: analyzed + ' / ' + total,
      subClass: pct >= 80 ? 'sub-ok' : 'sub-warn',
      icon: 'fas fa-brain', color: '#059669', bg: '#ecfdf5',
      fillPct: pct,
    },
    {
      id: 3, label: 'Non traités',
      display: pending,
      sub: pending > 0 ? 'En attente OCR / IA' : 'Tout est traité ✓',
      subClass: pending > 0 ? 'sub-warn' : 'sub-ok',
      icon: 'fas fa-hourglass-half',
      color: pending > 0 ? '#d97706' : '#059669',
      bg:    pending > 0 ? '#fffbeb' : '#ecfdf5',
      fillPct: total > 0 ? Math.round(pending * 100 / total) : 0,
    },
    {
      id: 4, label: 'Temps traitement moy.',
      display: formatAvgMs(avgMs.value),
      sub: healthData.value?.llm?.model || 'Groq LLM',
      subClass: 'sub-neutral',
      icon: 'fas fa-bolt', color: '#7c3aed', bg: '#f5f3ff',
      fillPct: avgMs.value > 0 ? Math.min(100, avgMs.value / 120000 * 100) : 0,
    },
  ]
})

// ── Health items ──────────────────────────────────────────────────────────────
const healthItems = computed(() => {
  const h = healthData.value
  if (!h?.status) return []
  return [
    { id: 1, name: 'Backend IA (FastAPI)',  ok: h.status === 'ok',        value: h.status === 'ok' ? 'En ligne' : 'Hors ligne' },
    { id: 2, name: 'LLM Groq',             ok: !!h.llm?.key_set,         value: h.llm?.model || '—' },
    { id: 3, name: 'Base de données',      ok: !!h.db,                   value: h.db ? 'Connectée' : 'N/A' },
    { id: 4, name: 'Index RAG (ChromaDB)', ok: h.rag?.status !== 'error', value: h.rag?.total_chunks != null ? h.rag.total_chunks + ' chunks' : (h.rag?.status || '—') },
    { id: 5, name: 'Gmail OAuth',          ok: !!h.gmail_token,          value: h.gmail_token ? 'Token valide' : 'Non configuré' },
  ]
})

// ── Latest document id for AgentGraph polling ────────────────────────────────
const latestDocId = computed(() => {
  const list = aiDocs.value?.documents || allDocs.value
  if (!list.length) return ''
  const sorted = [...list].sort((a, b) => {
    const da = new Date(a.analyzedAt || a.aiAnalyzedAt || a.AiAnalyzedAt || 0)
    const db = new Date(b.analyzedAt || b.aiAnalyzedAt || b.AiAnalyzedAt || 0)
    return db - da
  })
  return String(sorted[0]?.id ?? sorted[0]?.Id ?? '')
})

// ── Doc types ─────────────────────────────────────────────────────────────────
const TYPE_COLORS = {
  'Contrat':  '#2563eb', 'Facture':  '#059669', 'CV':       '#d97706',
  'Rapport':  '#7c3aed', 'RH':       '#db2777', 'Courrier': '#0891b2',
  'Autre':    '#94a3b8',
}

function typeColor(type) {
  return TYPE_COLORS[type] || TYPE_COLORS['Autre']
}

const docTypes = computed(() => {
  // Prefer C# dashboard byType, then AI enriched by_type
  const raw = dashStats.value?.byType || aiDocs.value?.by_type || {}
  return Object.entries(raw)
    .map(([label, count]) => ({ label, count: Number(count), color: typeColor(label) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6)
})

// ── Donut ─────────────────────────────────────────────────────────────────────
const CIRC = 364 // 2π × 58

const donutSegments = computed(() => {
  const total = docTypes.value.reduce((s, t) => s + t.count, 0)
  if (!total) return []
  let offset = CIRC / 4  // start at top
  return docTypes.value.map(t => {
    const dash = (t.count / total) * CIRC
    const seg  = { color: t.color, dash: +dash.toFixed(2), offset: +offset.toFixed(2) }
    offset -= dash
    return seg
  })
})

// ── Status rings ──────────────────────────────────────────────────────────────
const statusRings = computed(() => {
  const total   = totalDocs.value
  const done    = analyzedCount.value
  const pending = pendingDocs.value
  const inprog  = Math.max(0, total - done - pending)
  const safe    = n => total > 0 ? Math.round(n * 100 / total) : 0
  return [
    { id: 1, label: 'Analysés',   count: done,    pct: safe(done),    color: '#059669' },
    { id: 2, label: 'En cours',   count: inprog,  pct: safe(inprog),  color: '#2563eb' },
    { id: 3, label: 'En attente', count: pending, pct: safe(pending), color: '#d97706' },
  ]
})

// ── Recent docs ───────────────────────────────────────────────────────────────
const recentDocs = computed(() => {
  const list = aiDocs.value?.documents || []
  if (list.length) {
    return list.slice(0, 8).map(d => ({
      id:         d.id ?? d.Id,
      title:      d.title || d.Title || 'Sans titre',
      type:       d.aiDocumentType || d.AiDocumentType || null,
      analyzed:   !!(d.isAnalyzed || d.IsAnalyzed),
      analyzedAt: d.analyzedAt ? new Date(d.analyzedAt).toLocaleDateString('fr-FR') : null,
    }))
  }
  return allDocs.value.slice(0, 8).map(d => ({
    id:         d.id ?? d.Id,
    title:      d.title || d.Title || 'Sans titre',
    type:       d.aiDocumentType || d.AiDocumentType || null,
    analyzed:   !!(d.aiAnalyzedAt || d.AiAnalyzedAt),
    analyzedAt: (d.aiAnalyzedAt || d.AiAnalyzedAt)
                  ? new Date(d.aiAnalyzedAt || d.AiAnalyzedAt).toLocaleDateString('fr-FR')
                  : null,
  }))
})

// ── Lifecycle ─────────────────────────────────────────────────────────────────
let timer = null
onMounted(() => {
  loadAll()
  timer = setInterval(loadAll, 30_000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap');

.home-page {
  padding: 28px 32px 48px;
  background: #f8fafc;
  min-height: 100%;
  font-family: 'DM Sans', sans-serif;
  color: #1e293b;
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.page-top {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 24px;
}
.page-title { font-size: 22px; font-weight: 700; color: #0f172a; margin: 0 0 4px; }
.page-sub   { font-size: 13px; color: #64748b; display: flex; align-items: center; gap: 8px; }
.live-dot-wrap { display: flex; align-items: center; gap: 5px; }
.live-dot {
  width: 7px; height: 7px; background: #10b981; border-radius: 50%;
  animation: blink 1.4s ease-in-out infinite;
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

.top-right   { display: flex; align-items: center; gap: 10px; }
.last-sync   { font-size: 12px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
.refresh-btn {
  width: 34px; height: 34px; border-radius: 8px;
  border: 1px solid #e2e8f0; background: white;
  color: #475569; cursor: pointer; font-size: 13px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.refresh-btn:hover { background: #f1f5f9; color: #1e293b; }
.refresh-btn.spinning i { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Error ───────────────────────────────────────────────────────────────── */
.error-banner {
  display: flex; align-items: center; gap: 10px;
  background: #fef2f2; border: 1px solid #fca5a5;
  border-radius: 10px; padding: 10px 16px;
  color: #dc2626; font-size: 13px; margin-bottom: 16px;
}
.error-banner button { margin-left: auto; background: none; border: none; color: #dc2626; cursor: pointer; font-size: 14px; }

/* ── KPI Row ─────────────────────────────────────────────────────────────── */
.kpi-row {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 14px; margin-bottom: 18px;
}
.kpi-card {
  background: white; border-radius: 14px;
  border: 1px solid #e2e8f0; padding: 20px;
  display: flex; gap: 14px; align-items: flex-start;
  position: relative; overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s; cursor: default;
}
.kpi-card:hover { box-shadow: 0 4px 20px rgba(15,23,42,0.07); transform: translateY(-1px); }
.kpi-icon-wrap {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.kpi-right  { flex: 1; min-width: 0; }
.kpi-value  { font-size: 28px; font-weight: 700; line-height: 1.1; font-family: 'JetBrains Mono', monospace; letter-spacing: -1px; }
.kpi-label  { font-size: 12px; color: #64748b; font-weight: 500; margin: 4px 0 3px; }
.kpi-sub    { font-size: 11px; font-weight: 600; }
.sub-ok     { color: #059669; }
.sub-warn   { color: #d97706; }
.sub-neutral{ color: #94a3b8; }

.kpi-bar-bottom { position: absolute; bottom: 0; left: 0; right: 0; height: 3px; }
.kpi-bar-fill   { position: absolute; bottom: 0; left: 0; height: 3px; border-radius: 0 2px 2px 0; transition: width 1s ease; }

.skeleton-val {
  display: inline-block; width: 64px; height: 28px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200%; animation: shimmer 1.2s infinite; border-radius: 6px;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ── Mid grid ────────────────────────────────────────────────────────────── */
.mid-grid {
  display: grid; grid-template-columns: 1.7fr 1fr 1fr;
  gap: 14px; margin-bottom: 14px;
}

/* ── Card base ───────────────────────────────────────────────────────────── */
.card {
  background: white; border-radius: 14px;
  border: 1px solid #e2e8f0; padding: 20px;
}
.card-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px;
}
.card-title {
  font-size: 13px; font-weight: 600; color: #475569;
  display: flex; align-items: center; gap: 6px;
}
.card-title i { color: #6366f1; font-size: 12px; }
.card-subtitle {
  font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;
  display: flex; align-items: center; gap: 5px;
  margin: 14px 0 10px; border-top: 1px solid #f1f5f9; padding-top: 14px;
}
.card-subtitle i { color: #6366f1; }

/* ── Health ──────────────────────────────────────────────────────────────── */
.status-chip { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; }
.chip-ok  { background: #dcfce7; color: #16a34a; }
.chip-err { background: #fee2e2; color: #dc2626; }

.health-rows { display: flex; flex-direction: column; }
.health-row  { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid #f8fafc; }
.health-dot  { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-ok   { background: #10b981; }
.dot-err  { background: #ef4444; box-shadow: 0 0 5px rgba(239,68,68,0.4); }
.dot-idle { background: #cbd5e1; }
.health-name { flex: 1; font-size: 12px; color: #475569; }
.health-val  { font-size: 11px; font-weight: 600; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
.health-empty { font-size: 12px; color: #94a3b8; padding: 12px 0; text-align: center; }

/* ── Agents ──────────────────────────────────────────────────────────────── */
.agent-rows { display: flex; flex-direction: column; gap: 2px; }
.agent-row  {
  display: grid; grid-template-columns: 10px 1fr 80px;
  gap: 10px; align-items: center; padding: 8px 0;
  border-bottom: 1px solid #f8fafc;
}
.agent-dot   { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.agent-info  { overflow: hidden; }
.agent-name  { font-size: 11px; font-weight: 600; color: #1e293b; font-family: 'JetBrains Mono', monospace; }
.agent-task  { font-size: 10px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; }
.agent-load-bar  { height: 4px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.agent-load-fill { height: 100%; border-radius: 4px; transition: width 0.8s ease; }

/* ── Donut ───────────────────────────────────────────────────────────────── */
.total-badge { font-size: 12px; font-weight: 700; color: #2563eb; background: #eff6ff; padding: 2px 10px; border-radius: 20px; }
.donut-wrap  { display: flex; justify-content: center; margin-bottom: 14px; }
.donut-svg   { width: 130px; height: 130px; }
.d-center-val { font-size: 22px; font-weight: 700; fill: #0f172a; font-family: 'JetBrains Mono', monospace; }
.d-center-lbl { font-size: 9px; fill: #94a3b8; letter-spacing: 2px; }

.type-list  { display: flex; flex-direction: column; gap: 7px; }
.type-row   { display: flex; align-items: center; gap: 8px; }
.type-dot   { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.type-label { font-size: 11px; color: #64748b; width: 68px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.type-bar-wrap { flex: 1; height: 4px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.type-bar   { height: 100%; border-radius: 4px; transition: width 1s ease; }
.type-count { font-size: 11px; font-weight: 700; color: #1e293b; font-family: 'JetBrains Mono', monospace; min-width: 26px; text-align: right; }
.type-empty { font-size: 12px; color: #94a3b8; text-align: center; padding: 12px 0; }

/* ── Rings ───────────────────────────────────────────────────────────────── */
.status-rings { display: flex; justify-content: space-around; margin-bottom: 16px; }
.ring-item    { display: flex; flex-direction: column; align-items: center; gap: 5px; }
.ring-svg     { width: 72px; height: 72px; }
.ring-num {
  font-size: 15px; font-weight: 700; fill: #0f172a;
  font-family: 'JetBrains Mono', monospace; dominant-baseline: middle;
}
.ring-lbl { font-size: 11px; color: #64748b; }
.ring-pct { font-size: 12px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

.pending-alert {
  display: flex; align-items: flex-start; gap: 10px;
  background: #fffbeb; border: 1px solid #fde68a;
  border-radius: 10px; padding: 10px 12px;
  font-size: 12px; color: #92400e; margin-bottom: 10px;
}
.pending-alert i { color: #d97706; margin-top: 1px; flex-shrink: 0; }
.alert-sub { font-weight: 400; color: #b45309; margin-top: 2px; }

/* ── Conversations ───────────────────────────────────────────────────────── */
.conv-row  { display: flex; }
.conv-stat { flex: 1; text-align: center; padding: 8px 4px; border-right: 1px solid #f1f5f9; }
.conv-stat:last-child { border: none; }
.conv-val  { font-size: 18px; font-weight: 700; color: #1e293b; font-family: 'JetBrains Mono', monospace; }
.conv-lbl  { font-size: 10px; color: #94a3b8; margin-top: 2px; }

/* ── Feed table ──────────────────────────────────────────────────────────── */
.feed-card { }
.see-all   { font-size: 12px; color: #2563eb; cursor: pointer; display: flex; align-items: center; gap: 4px; font-weight: 600; }
.see-all:hover { text-decoration: underline; }

.feed-table { display: flex; flex-direction: column; }
.feed-row   {
  display: grid; grid-template-columns: 3fr 1.4fr 1fr 1fr;
  gap: 12px; align-items: center; padding: 10px 10px; border-radius: 8px;
}
.feed-head  { font-size: 11px; font-weight: 600; color: #94a3b8; background: #f8fafc; border-radius: 8px; }
.feed-row:not(.feed-head) { border-bottom: 1px solid #f8fafc; cursor: pointer; transition: background 0.15s; font-size: 13px; }
.feed-row:not(.feed-head):hover { background: #f8fafc; }
.feed-name  { display: flex; align-items: center; gap: 8px; font-weight: 500; color: #1e293b; overflow: hidden; }
.feed-name span, .feed-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.feed-type-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px; width: fit-content; }
.feed-date  { font-size: 12px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
.feed-status{ display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; }
.st-ok      { color: #059669; }
.st-pending { color: #d97706; }

.feed-empty { text-align: center; padding: 40px; color: #94a3b8; }
.feed-empty i { font-size: 30px; margin-bottom: 10px; display: block; }
.feed-empty p { font-size: 14px; }

.sk-row {
  height: 40px; margin-bottom: 8px; border-radius: 8px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200%; animation: shimmer 1.2s infinite;
}

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 1280px) {
  .mid-grid  { grid-template-columns: 1fr 1fr; }
  .health-card { grid-column: 1 / -1; }
}
@media (max-width: 900px) {
  .kpi-row   { grid-template-columns: 1fr 1fr; }
  .mid-grid  { grid-template-columns: 1fr; }
  .home-page { padding: 16px; }
  .feed-row  { grid-template-columns: 1fr 1fr; }
}
</style>