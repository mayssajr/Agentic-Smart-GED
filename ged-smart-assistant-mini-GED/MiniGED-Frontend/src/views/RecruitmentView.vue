<template>
  <div class="rh">

    <!-- ── HERO HEADER ─────────────────────────────────────────────── -->
    <div class="hero">
      <div class="hero-left">
        <div class="hero-icon"><i class="fas fa-briefcase"></i></div>
        <div>
          <h1 class="hero-title">Pipeline Recrutement</h1>
          <p class="hero-sub">{{ filtered.length }} candidature(s) · mis à jour {{ lastSync }}</p>
        </div>
      </div>
      <div class="hero-right">
        <select v-model="positionFilter" class="filter-select">
          <option value="">Tous les postes</option>
          <option v-for="p in positions" :key="p" :value="p">{{ p }}</option>
        </select>
        <button class="btn-reload" @click="loadAll" :disabled="loading">
          <i class="fas fa-arrows-rotate" :class="{ spin: loading }"></i>
        </button>
      </div>
    </div>

    <!-- ── KPI CARDS ────────────────────────────────────────────────── -->
    <div class="kpi-grid">
      <div class="kpi-card" v-for="k in kpis" :key="k.id"
           :style="{ '--a': k.from, '--b': k.to }">
        <div class="kpi-glow"></div>
        <i :class="k.icon" class="kpi-ico"></i>
        <div class="kpi-num">{{ k.value }}</div>
        <div class="kpi-lbl">{{ k.label }}</div>
      </div>
    </div>

    <!-- ── FUNNEL PIPELINE ──────────────────────────────────────────── -->
    <div class="funnel-section">
      <div class="section-title">
        <i class="fas fa-filter"></i> Entonnoir de recrutement
      </div>
      <div class="funnel">
        <div
          v-for="(col, i) in COLUMNS" :key="col.key"
          class="funnel-step"
          :class="{ 'funnel-step--active': byStatus(col.key).length > 0 }"
          :style="{ '--fc': col.color, '--fw': funnel_width(i) }"
          @click="activeStatus = activeStatus === col.key ? null : col.key"
        >
          <div class="funnel-bar">
            <div class="funnel-fill"
                 :style="{ height: funnel_pct(col.key) + '%', background: col.gradient }">
            </div>
            <div class="funnel-count" :style="{ color: col.color }">
              {{ byStatus(col.key).length }}
            </div>
          </div>
          <div class="funnel-label" :style="{ color: col.color }">
            <span class="funnel-dot" :style="{ background: col.color }"></span>
            {{ col.label }}
          </div>
        </div>
      </div>
    </div>

    <!-- ── CANDIDATES GRID ──────────────────────────────────────────── -->
    <div class="candidates-section">
      <div class="section-title">
        <i class="fas fa-users"></i>
        Candidats
        <span v-if="activeStatus" class="active-filter-chip"
              :style="{ background: activeStatusConfig?.color + '18', color: activeStatusConfig?.color, borderColor: activeStatusConfig?.color + '40' }">
          {{ activeStatusConfig?.label }}
          <button @click="activeStatus = null"><i class="fas fa-xmark"></i></button>
        </span>
      </div>

      <div v-if="loading" class="cands-grid">
        <div class="skel-card" v-for="i in 8" :key="i"></div>
      </div>

      <div v-else-if="displayedCandidates.length" class="cands-grid">
        <div
          v-for="c in displayedCandidates" :key="c.candidateId"
          class="cand-card"
          :style="{ '--cc': statusConfig(c.status)?.color }"
          @click="openCandidate(c)"
        >
          <!-- Bande couleur statut -->
          <div class="cand-stripe"
               :style="{ background: statusConfig(c.status)?.gradient }">
          </div>

          <div class="cand-body">
            <!-- Avatar + nom -->
            <div class="cand-top">
              <div class="cand-avatar"
                   :style="{ background: statusConfig(c.status)?.gradient }">
                {{ initials(c.name) }}
              </div>
              <div class="cand-meta">
                <div class="cand-name">{{ c.name }}</div>
                <div class="cand-pos">{{ c.position }}</div>
              </div>
              <div class="cand-status-pill"
                   :style="{ background: statusConfig(c.status)?.color + '18',
                              color: statusConfig(c.status)?.color,
                              borderColor: statusConfig(c.status)?.color + '35' }">
                <i :class="statusConfig(c.status)?.icon" style="font-size:10px"></i>
                {{ statusConfig(c.status)?.label }}
              </div>
            </div>

            <!-- Score -->
            <div v-if="c.score > 0" class="cand-score-row">
              <div class="score-bar-wrap">
                <div class="score-bar"
                     :style="{ width: c.score + '%', background: scoreGradient(c.score) }">
                </div>
              </div>
              <span class="score-val" :style="{ color: scoreColor(c.score) }">
                {{ c.score }}/100
              </span>
            </div>

            <!-- Footer -->
            <div class="cand-foot">
              <span class="cand-date">
                <i class="fas fa-calendar-days"></i>
                {{ formatDate(c.createdAt) }}
              </span>
              <span class="cand-arrow"><i class="fas fa-arrow-right"></i></span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-cands">
        <div class="empty-icon"><i class="fas fa-user-slash"></i></div>
        <p>Aucun candidat{{ activeStatus ? ' pour ce statut' : '' }}</p>
        <button v-if="activeStatus" class="btn-clear" @click="activeStatus = null">
          Voir tous les candidats
        </button>
      </div>
    </div>

    <!-- ── BOTTOM ANALYTICS ─────────────────────────────────────────── -->
    <div class="analytics-grid">

      <!-- Répartition par statut — donut -->
      <section class="panel panel--donut">
        <div class="panel-head"><i class="fas fa-chart-pie"></i> Répartition par statut</div>
        <div class="donut-wrap">
          <svg viewBox="0 0 160 160" class="donut-svg">
            <circle cx="80" cy="80" r="56" fill="none" stroke="#f1f5f9" stroke-width="20"/>
            <circle v-for="(seg, i) in donutSegs" :key="i"
              cx="80" cy="80" r="56" fill="none"
              :stroke="seg.color" stroke-width="20"
              :stroke-dasharray="`${seg.dash} ${351 - seg.dash}`"
              :stroke-dashoffset="seg.offset"
              style="transition:all 1.2s ease"/>
            <text x="80" y="76" text-anchor="middle" class="d-num">{{ filtered.length }}</text>
            <text x="80" y="92" text-anchor="middle" class="d-sub">TOTAL</text>
          </svg>
          <div class="donut-legend">
            <div v-for="col in COLUMNS" :key="col.key" class="leg-row"
                 @click="activeStatus = activeStatus === col.key ? null : col.key"
                 :class="{ 'leg-row--active': activeStatus === col.key }">
              <div class="leg-dot" :style="{ background: col.color }"></div>
              <div class="leg-label">{{ col.label }}</div>
              <div class="leg-bar-wrap">
                <div class="leg-bar" :style="{
                  width: (filtered.length ? byStatus(col.key).length / filtered.length * 100 : 0) + '%',
                  background: col.color
                }"></div>
              </div>
              <div class="leg-count" :style="{ color: col.color }">{{ byStatus(col.key).length }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Stats par poste -->
      <section class="panel panel--pos">
        <div class="panel-head"><i class="fas fa-building"></i> Par poste</div>
        <div class="pos-list">
          <div v-for="ps in statsByPosition" :key="ps.position" class="pos-item">
            <div class="pos-top">
              <span class="pos-name">{{ ps.position }}</span>
              <span class="pos-total">{{ ps.total }}</span>
            </div>
            <div class="pos-chips">
              <span class="pos-chip pos-chip--green" v-if="ps.accepted">
                <i class="fas fa-check"></i> {{ ps.accepted }} accepté(s)
              </span>
              <span class="pos-chip pos-chip--purple" v-if="ps.interview">
                <i class="fas fa-calendar"></i> {{ ps.interview }} entretien(s)
              </span>
              <span class="pos-chip pos-chip--blue" v-if="ps.avgScore">
                ★ {{ ps.avgScore }}/100
              </span>
            </div>
            <div class="pos-track">
              <div class="pos-track-fill"
                   :style="{ width: (ps.total / maxPositionCount * 100) + '%' }"></div>
            </div>
          </div>
          <div v-if="!statsByPosition.length" class="pos-empty">Aucune donnée</div>
        </div>
      </section>

      <!-- Graphe semaines -->
      <section class="panel panel--chart">
        <div class="panel-head"><i class="fas fa-chart-column"></i> Candidatures / semaine</div>
        <div v-if="weeklyData.length" class="chart-wrap">
          <div class="chart-bars">
            <div v-for="w in weeklyData" :key="w.week" class="chart-col"
                 :title="`Semaine ${w.week} : ${w.count}`">
              <div class="bar-val">{{ w.count }}</div>
              <div class="bar-fill"
                   :style="{
                     height: (w.count / maxWeekCount * 100) + '%',
                     background: weekBarGradient(w.count),
                   }"></div>
              <div class="bar-lbl">S{{ w.week }}</div>
            </div>
          </div>
        </div>
        <div v-else class="chart-empty">
          <i class="fas fa-chart-column"></i> Pas assez de données
        </div>
      </section>

    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router    = useRouter()
const authStore = useAuthStore()

// ── Config statuts ────────────────────────────────────────────────────────────
const COLUMNS = [
  { key: 'Recu',         label: 'Reçu',           color: '#6366f1', from: '#818cf8', to: '#6366f1',
    gradient: 'linear-gradient(135deg,#818cf8,#6366f1)', icon: 'fas fa-inbox' },
  { key: 'ATraiter',     label: 'À traiter',       color: '#0891b2', from: '#38bdf8', to: '#0891b2',
    gradient: 'linear-gradient(135deg,#38bdf8,#0891b2)', icon: 'fas fa-clock' },
  { key: 'Entretien',    label: 'Entretien',        color: '#7c3aed', from: '#a78bfa', to: '#7c3aed',
    gradient: 'linear-gradient(135deg,#a78bfa,#7c3aed)', icon: 'fas fa-calendar-check' },
  { key: 'Accepte',      label: 'Accepté',          color: '#059669', from: '#34d399', to: '#059669',
    gradient: 'linear-gradient(135deg,#34d399,#059669)', icon: 'fas fa-circle-check' },
  { key: 'Refuse',       label: 'Refusé',           color: '#dc2626', from: '#f87171', to: '#dc2626',
    gradient: 'linear-gradient(135deg,#f87171,#dc2626)', icon: 'fas fa-circle-xmark' },
  { key: 'ListeAttente', label: 'Liste d\'attente', color: '#d97706', from: '#fbbf24', to: '#d97706',
    gradient: 'linear-gradient(135deg,#fbbf24,#d97706)', icon: 'fas fa-bookmark' },
]

const STATUS_MAP = Object.fromEntries(COLUMNS.map(c => [c.key, c]))
const statusConfig = (key) => STATUS_MAP[key]

// ── State ─────────────────────────────────────────────────────────────────────
const loading        = ref(false)
const candidates     = ref([])
const positionFilter = ref('')
const activeStatus   = ref(null)
const lastSync       = ref('—')

const activeStatusConfig = computed(() =>
  activeStatus.value ? STATUS_MAP[activeStatus.value] : null)

// ── Chargement ────────────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true
  try {
    const res = await fetch(
      `${import.meta.env?.VITE_MINIGED_API_URL || 'http://localhost:5092'}/api/recruitment/applications?pageSize=200`,
      { headers: { Authorization: `Bearer ${authStore.token}` } }
    )
    if (res.ok) {
      const data       = await res.json()
      candidates.value = data.candidates ?? data ?? []
    }
  } catch (e) {
    console.error('loadAll:', e)
  } finally {
    loading.value = false
    lastSync.value = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  }
}
onMounted(loadAll)

// ── Filtres ───────────────────────────────────────────────────────────────────
const filtered = computed(() =>
  positionFilter.value
    ? candidates.value.filter(c => c.position === positionFilter.value)
    : candidates.value
)

const positions = computed(() =>
  [...new Set(candidates.value.map(c => c.position).filter(Boolean))].sort()
)

const byStatus = (key) =>
  filtered.value.filter(c => c.status === key)
               .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))

const displayedCandidates = computed(() =>
  activeStatus.value
    ? byStatus(activeStatus.value)
    : [...filtered.value].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
)

// ── KPIs ──────────────────────────────────────────────────────────────────────
const kpis = computed(() => {
  const total     = filtered.value.length
  const interview = filtered.value.filter(c => c.status === 'Entretien').length
  const accepted  = filtered.value.filter(c => c.status === 'Accepte').length
  const refused   = filtered.value.filter(c => c.status === 'Refuse').length
  const waiting   = filtered.value.filter(c => c.status === 'ListeAttente').length
  const scored    = filtered.value.filter(c => c.score > 0)
  const avg       = scored.length
    ? Math.round(scored.reduce((s, c) => s + c.score, 0) / scored.length) : null
  const rate      = total > 0 ? Math.round(accepted * 100 / total) : 0

  return [
    { id:1, label:'Total',         value: total,                  icon:'fas fa-users',         from:'#818cf8', to:'#6366f1' },
    { id:2, label:'Entretiens',     value: interview,              icon:'fas fa-calendar-check', from:'#a78bfa', to:'#7c3aed' },
    { id:3, label:'Acceptés',       value: accepted,               icon:'fas fa-user-check',     from:'#34d399', to:'#059669' },
    { id:4, label:'Refusés',        value: refused,                icon:'fas fa-user-xmark',     from:'#f87171', to:'#dc2626' },
    // { id:5, label:'Score moyen',    value: avg ? avg + '/100' : '—', icon:'fas fa-star',          from:'#fbbf24', to:'#d97706' },
    // { id:6, label:'Taux succès',    value: rate + '%',             icon:'fas fa-chart-line',     from:'#38bdf8', to:'#0891b2' },
  ]
})

// ── Funnel ────────────────────────────────────────────────────────────────────
const maxCount = computed(() =>
  Math.max(1, ...COLUMNS.map(c => byStatus(c.key).length))
)
const funnel_pct   = (key) => Math.max(8, byStatus(key).length / maxCount.value * 100)
const funnel_width = (i)   => 100 - i * 4   // s'amincit légèrement

// ── Donut ─────────────────────────────────────────────────────────────────────
const CIRC = 351
const donutSegs = computed(() => {
  const total = filtered.value.length
  if (!total) return []
  let offset = CIRC / 4
  return COLUMNS.map(col => {
    const count = byStatus(col.key).length
    const dash  = (count / total) * CIRC
    const seg   = { color: col.color, dash: +dash.toFixed(2), offset: +offset.toFixed(2) }
    offset -= dash
    return seg
  })
})

// ── Stats par poste ───────────────────────────────────────────────────────────
const statsByPosition = computed(() => {
  const map = {}
  filtered.value.forEach(c => {
    const p = c.position || 'Non défini'
    if (!map[p]) map[p] = { position: p, total: 0, accepted: 0, interview: 0, scores: [] }
    map[p].total++
    if (c.status === 'Accepte')   map[p].accepted++
    if (c.status === 'Entretien') map[p].interview++
    if (c.score > 0)              map[p].scores.push(c.score)
  })
  return Object.values(map)
    .map(p => ({ ...p,
      avgScore: p.scores.length
        ? Math.round(p.scores.reduce((a, b) => a + b, 0) / p.scores.length) : null,
    }))
    .sort((a, b) => b.total - a.total).slice(0, 7)
})

const maxPositionCount = computed(() =>
  Math.max(1, ...statsByPosition.value.map(p => p.total))
)

// ── Weekly chart ──────────────────────────────────────────────────────────────
const weeklyData = computed(() => {
  const map = {}
  filtered.value.forEach(c => {
    const d = new Date(c.createdAt)
    if (isNaN(d)) return
    const w = getIsoWeek(d)
    map[w] = (map[w] || 0) + 1
  })
  return Object.entries(map)
    .map(([w, count]) => ({ week: parseInt(w), count }))
    .sort((a, b) => a.week - b.week)
    .slice(-10)
})
const maxWeekCount = computed(() => Math.max(1, ...weeklyData.value.map(w => w.count)))

const weekBarGradient = (count) => {
  const pct = count / maxWeekCount.value
  if (pct > 0.75) return 'linear-gradient(180deg,#34d399,#059669)'
  if (pct > 0.4)  return 'linear-gradient(180deg,#818cf8,#6366f1)'
  return 'linear-gradient(180deg,#94a3b8,#64748b)'
}

function getIsoWeek(d) {
  const dt = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  const day = dt.getUTCDay() || 7
  dt.setUTCDate(dt.getUTCDate() + 4 - day)
  const yearStart = new Date(Date.UTC(dt.getUTCFullYear(), 0, 1))
  return Math.ceil((((dt - yearStart) / 86400000) + 1) / 7)
}

// ── Utils ─────────────────────────────────────────────────────────────────────
const initials   = (n) => (n || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
const formatDate = (d) => d
  ? new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' }) : ''
const scoreColor = (s) => s >= 75 ? '#059669' : s >= 55 ? '#d97706' : '#dc2626'
const scoreGradient = (s) =>
  s >= 75 ? 'linear-gradient(90deg,#34d399,#059669)'
  : s >= 55 ? 'linear-gradient(90deg,#fbbf24,#d97706)'
  : 'linear-gradient(90deg,#f87171,#dc2626)'

const openCandidate = (c) => {
  if (c.documentId) router.push(`/document/${c.documentId}`)
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

/* ── Base ── */
.rh {
  padding: 24px 28px 56px;
  background: #f1f4fb;
  min-height: 100%;
  font-family: 'Sora', sans-serif;
  color: #0f172a;
  display: flex; flex-direction: column; gap: 22px;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;

  scrollbar-width: thin;
  scrollbar-color: #6c757d transparent;
}

/* Chrome / Edge / Brave */
.rh::-webkit-scrollbar {
  width: 10px;
}

.rh::-webkit-scrollbar-track {
  background: transparent;
}

.rh::-webkit-scrollbar-thumb {
  background-color: #adb5bd;
  border-radius: 4px;
}

.rh::-webkit-scrollbar-thumb:hover {
  background-color: #6c757d;
}

/* ── Hero ── */
.hero {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 12px;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
  border-radius: 18px; padding: 22px 28px; color: white;
  box-shadow: 0 8px 32px rgba(99,102,241,.3);
}
.hero-left    { display: flex; align-items: center; gap: 16px; }
.hero-icon    {
  width: 52px; height: 52px; border-radius: 14px;
  background: rgba(255,255,255,.15); backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: white;
}
.hero-title   { font-size: 20px; font-weight: 800; margin: 0 0 4px; }
.hero-sub     { font-size: 12px; color: rgba(255,255,255,.65); margin: 0; }
.hero-right   { display: flex; align-items: center; gap: 10px; }

.filter-select {
  padding: 8px 14px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,.25);
  background: rgba(255,255,255,.12); color: white;
  font-size: 12.5px; font-family: inherit; outline: none; cursor: pointer;
}
.filter-select option { background: #1e1b4b; color: white; }

.btn-reload {
  width: 38px; height: 38px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,.25);
  background: rgba(255,255,255,.12); color: white;
  cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center; transition: all .2s;
}
.btn-reload:hover { background: rgba(255,255,255,.25); }
.spin { animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── KPI Grid ── */
.kpi-grid {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px;
}
.kpi-card {
  border-radius: 16px; padding: 18px 16px;
  background: linear-gradient(135deg, var(--a), var(--b));
  position: relative; overflow: hidden;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  text-align: center; color: white;
  box-shadow: 0 4px 20px color-mix(in srgb, var(--b) 30%, transparent);
  transition: transform .2s, box-shadow .2s;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 28px color-mix(in srgb, var(--b) 40%, transparent); }
.kpi-glow {
  position: absolute; top: -20px; right: -20px;
  width: 80px; height: 80px; border-radius: 50%;
  background: rgba(255,255,255,.12);
}
.kpi-ico  { font-size: 20px; opacity: .9; position: relative; }
.kpi-num  { font-size: 26px; font-weight: 800; font-family: 'JetBrains Mono',monospace; letter-spacing: -1px; position: relative; }
.kpi-lbl  { font-size: 10.5px; font-weight: 600; opacity: .85; text-transform: uppercase; letter-spacing: .4px; position: relative; }

/* ── Section title ── */
.section-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 700; color: #334155; margin-bottom: 14px;
}
.section-title i { color: #6366f1; }

/* ── Funnel ── */
.funnel-section {
  background: white; border-radius: 16px; padding: 20px 24px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 12px rgba(15,23,42,.04);
}
.funnel {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px;
  align-items: end; height: 140px;
}
.funnel-step {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  cursor: pointer; transition: all .2s;
}
.funnel-step:hover { transform: translateY(-3px); }

.funnel-bar {
  width: 100%; height: 110px; border-radius: 10px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  position: relative; overflow: hidden; display: flex; align-items: flex-end;
}
.funnel-fill {
  width: 100%; border-radius: 10px 10px 0 0;
  transition: height 1.2s cubic-bezier(.4,0,.2,1);
  min-height: 8px;
}
.funnel-count {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  font-size: 22px; font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  text-shadow: 0 2px 8px rgba(255,255,255,.8);
}

.funnel-label {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 700; text-align: center;
}
.funnel-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

/* ── Candidate Cards ── */
.candidates-section {
  background: white; border-radius: 16px; padding: 20px 24px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 12px rgba(15,23,42,.04);
}

.active-filter-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700;
  border: 1px solid; margin-left: 6px;
}
.active-filter-chip button {
  background: none; border: none; cursor: pointer; color: inherit;
  font-size: 11px; padding: 0; line-height: 1;
}

.cands-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.skel-card {
  height: 110px; border-radius: 14px;
  background: linear-gradient(90deg,#f1f5f9 25%,#e8edf5 50%,#f1f5f9 75%);
  background-size: 200%; animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

.cand-card {
  border-radius: 14px; border: 1px solid #e2e8f0;
  overflow: hidden; cursor: pointer; background: white;
  transition: transform .2s, box-shadow .2s, border-color .2s;
  display: flex;
}
.cand-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15,23,42,.08);
  border-color: var(--cc, #6366f1);
}

.cand-stripe { width: 4px; flex-shrink: 0; }
.cand-body   { flex: 1; padding: 13px 14px; display: flex; flex-direction: column; gap: 8px; }

.cand-top { display: flex; align-items: flex-start; gap: 10px; }
.cand-avatar {
  width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
  color: white; font-size: 12px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
}
.cand-meta  { flex: 1; min-width: 0; }
.cand-name  { font-size: 13px; font-weight: 700; color: #1e293b;
              overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cand-pos   { font-size: 11px; color: #94a3b8; margin-top: 1px;
              overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.cand-status-pill {
  font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 20px;
  border: 1px solid; white-space: nowrap; display: flex; align-items: center; gap: 4px;
  flex-shrink: 0;
}

.cand-score-row {
  display: flex; align-items: center; gap: 8px;
}
.score-bar-wrap {
  flex: 1; height: 5px; background: #f1f5f9; border-radius: 4px; overflow: hidden;
}
.score-bar { height: 100%; border-radius: 4px; transition: width 1s ease; }
.score-val {
  font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace;
  min-width: 42px; text-align: right; flex-shrink: 0;
}

.cand-foot {
  display: flex; justify-content: space-between; align-items: center;
}
.cand-date {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: #94a3b8;
}
.cand-arrow { font-size: 10px; color: #cbd5e1; transition: transform .15s; }
.cand-card:hover .cand-arrow { transform: translateX(3px); color: var(--cc, #6366f1); }

.empty-cands {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 48px 20px; text-align: center; color: #94a3b8;
}
.empty-icon {
  width: 56px; height: 56px; border-radius: 14px;
  background: #f8fafc; display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: #cbd5e1;
}
.btn-clear {
  font-size: 12.5px; font-weight: 700; color: #6366f1;
  background: #eff0ff; border: 1px solid #c7d2fe; border-radius: 8px;
  padding: 6px 14px; cursor: pointer; transition: all .15s;
}
.btn-clear:hover { background: #e0e7ff; }

/* ── Analytics ── */
.analytics-grid {
  display: grid; grid-template-columns: 300px 1fr 1fr; gap: 14px;
}

.panel {
  background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px;
  box-shadow: 0 2px 12px rgba(15,23,42,.04);
}
.panel-head {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 700; color: #334155; margin-bottom: 16px;
}
.panel-head i { color: #6366f1; }

/* ── Donut ── */
.donut-wrap  { display: flex; flex-direction: column; align-items: center; gap: 14px; }
.donut-svg   { width: 130px; height: 130px; }
.d-num { font-size: 22px; font-weight: 800; fill: #0f172a; font-family: 'JetBrains Mono', monospace; }
.d-sub { font-size: 8px; fill: #94a3b8; letter-spacing: 3px; text-transform: uppercase; }

.donut-legend { width: 100%; display: flex; flex-direction: column; gap: 6px; }
.leg-row {
  display: flex; align-items: center; gap: 7px; cursor: pointer;
  padding: 4px 6px; border-radius: 7px; transition: background .15s;
}
.leg-row:hover        { background: #f8fafc; }
.leg-row--active      { background: #eff0ff; }
.leg-dot   { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.leg-label { flex: 1; font-size: 11.5px; color: #475569; font-weight: 600; }
.leg-bar-wrap { width: 60px; height: 4px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.leg-bar   { height: 100%; border-radius: 4px; transition: width 1s ease; }
.leg-count { font-size: 12px; font-weight: 800; font-family: 'JetBrains Mono', monospace;
             min-width: 18px; text-align: right; }

/* ── Pos ── */
.pos-list { display: flex; flex-direction: column; gap: 12px; }
.pos-item { display: flex; flex-direction: column; gap: 5px; }
.pos-top  { display: flex; justify-content: space-between; align-items: center; }
.pos-name { font-size: 12.5px; font-weight: 700; color: #1e293b; }
.pos-total{ font-size: 12px; font-weight: 800; color: #6366f1;
            font-family: 'JetBrains Mono', monospace; }
.pos-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.pos-chip {
  display: flex; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
}
.pos-chip--green  { background: #dcfce7; color: #059669; }
.pos-chip--purple { background: #ede9fe; color: #7c3aed; }
.pos-chip--blue   { background: #dbeafe; color: #2563eb; }
.pos-track { height: 4px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.pos-track-fill {
  height: 100%; background: linear-gradient(90deg,#818cf8,#6366f1);
  border-radius: 4px; transition: width 1s ease;
}
.pos-empty { font-size: 12px; color: #94a3b8; text-align: center; padding: 16px 0; }

/* ── Chart ── */
.chart-wrap { height: 160px; }
.chart-bars {
  display: flex; align-items: flex-end; gap: 6px; height: 100%;
  border-bottom: 2px solid #f1f5f9;
}
.chart-col  { flex: 1; display: flex; flex-direction: column; align-items: center;
              gap: 4px; height: 100%; justify-content: flex-end; }
.bar-val    { font-size: 10.5px; font-weight: 800; color: #475569;
              font-family: 'JetBrains Mono', monospace; }
.bar-fill   { width: 100%; min-height: 4px; border-radius: 5px 5px 0 0;
              transition: height 1.2s cubic-bezier(.4,0,.2,1); }
.bar-lbl    { font-size: 9.5px; color: #94a3b8; font-family: 'JetBrains Mono', monospace;
              margin-top: 5px; }
.chart-empty {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  height: 100%; font-size: 13px; color: #cbd5e1;
}

/* ── Responsive ── */
@media (max-width: 1400px) {
  .analytics-grid { grid-template-columns: 280px 1fr 1fr; }
}
@media (max-width: 1200px) {
  .kpi-grid       { grid-template-columns: repeat(3, 1fr); }
  .funnel         { grid-template-columns: repeat(3, 1fr); height: auto; }
  .analytics-grid { grid-template-columns: 1fr 1fr; }
  .panel--donut   { grid-column: 1 / -1; }
}
@media (max-width: 900px) {
  .rh             { padding: 14px; gap: 16px; }
  .kpi-grid       { grid-template-columns: repeat(2, 1fr); }
  .funnel         { grid-template-columns: repeat(2, 1fr); }
  .cands-grid     { grid-template-columns: 1fr; }
  .analytics-grid { grid-template-columns: 1fr; }
}
</style>