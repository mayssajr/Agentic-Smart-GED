<template>
  <div class="tasks-tab">

    <!-- Barre d'outils -->
    <div class="toolbar">
      <div class="toolbar-left">
        <div class="filter-group">
          <!-- Filtre statut -->
          <button
            v-for="f in STATUS_FILTERS" :key="f.key"
            class="filter-chip"
            :class="{ 'filter-chip--active': statusFilter === f.key }"
            @click="statusFilter = f.key"
          >
            {{ f.label }}
            <span class="chip-count">{{ countByStatus(f.key) }}</span>
          </button>
        </div>

        <div class="divider-v"></div>

        <!-- Filtre priorité -->
        <div class="filter-group">
          <button
            v-for="p in PRIORITY_FILTERS" :key="p.key"
            class="filter-chip filter-chip--priority"
            :class="{ 'filter-chip--active': priorityFilter === p.key }"
            :style="priorityFilter === p.key ? { background: p.color + '18', color: p.color, borderColor: p.color + '40' } : {}"
            @click="priorityFilter = priorityFilter === p.key ? null : p.key"
          >
            <span class="priority-dot" :style="{ background: p.color }"></span>
            {{ p.label }}
          </button>
        </div>
      </div>

      <button class="btn-new" @click="$emit('new-task')">
        <i class="fas fa-plus"></i> Nouvelle tâche
      </button>
    </div>

    <!-- Résumé stats -->
    <div class="stats-strip" v-if="tasks.length">
      <div class="stat-pill">
        <span class="stat-n">{{ overdueCount }}</span>
        <span class="stat-l" style="color:#ef4444">En retard</span>
      </div>
      <div class="stat-pill">
        <span class="stat-n">{{ pendingCount }}</span>
        <span class="stat-l">En attente</span>
      </div>
      <div class="stat-pill">
        <span class="stat-n">{{ inProgressCount }}</span>
        <span class="stat-l" style="color:#2563eb">En cours</span>
      </div>
      <div class="stat-pill">
        <span class="stat-n">{{ completedCount }}</span>
        <span class="stat-l" style="color:#059669">Terminées</span>
      </div>
    </div>

    <!-- Tâches en retard — section épinglée -->
    <div v-if="overdueTasks.length && statusFilter === 'all'" class="overdue-section">
      <div class="overdue-header">
        <i class="fas fa-triangle-exclamation"></i>
        {{ overdueTasks.length }} tâche(s) en retard
      </div>
      <div class="task-list">
        <DocumentTaskItem
          v-for="t in overdueTasks" :key="t.id" :task="t"
          @status-change="$emit('status-change', $event)"
          @edit="$emit('edit', $event)"
          @delete="$emit('delete', $event)"
        />
      </div>
    </div>

    <!-- Liste principale -->
    <div v-if="filteredTasks.length" class="task-list">
      <DocumentTaskItem
        v-for="t in filteredTasks" :key="t.id" :task="t"
        @status-change="(id, s) => $emit('status-change', id, s)"
        @edit="(t) => $emit('edit', t)"
        @delete="(id) => $emit('delete', id)"
      />
    </div>

    <!-- Vide -->
    <div v-else class="empty-state">
      <div class="empty-icon"><i class="fas fa-list-check"></i></div>
      <p class="empty-title">{{ tasks.length ? 'Aucune tâche ne correspond aux filtres' : 'Aucune tâche' }}</p>
      <button v-if="!tasks.length" class="btn-new" @click="$emit('new-task')">
        <i class="fas fa-plus"></i> Créer une tâche
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import DocumentTaskItem from './DocumentTaskItem.vue'

const props = defineProps({ tasks: { type: Array, default: () => [] } })
defineEmits(['new-task', 'status-change', 'edit', 'delete'])

// ── Filtres ───────────────────────────────────────────────────────────────────
const STATUS_FILTERS = [
  { key: 'all',        label: 'Toutes'     },
  { key: 'active',     label: 'Actives'    },
  { key: 'completed',  label: 'Terminées'  },
]
const PRIORITY_FILTERS = [
  { key: 0, label: 'Basse',   color: '#10b981' },
  { key: 1, label: 'Moyenne', color: '#f59e0b' },
  { key: 2, label: 'Haute',   color: '#ef4444' },
  { key: 3, label: 'Urgente', color: '#7c3aed' },
]

const statusFilter   = ref('all')
const priorityFilter = ref(null)

// ── Computed ──────────────────────────────────────────────────────────────────
const now = new Date()

const isOverdue = (t) =>
  t.dueDate && t.status !== 2 && t.status !== 3 && new Date(t.dueDate) < now

const overdueTasks = computed(() =>
  props.tasks.filter(isOverdue)
    .sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate))
)

const overdueIds     = computed(() => new Set(overdueTasks.value.map(t => t.id)))
const overdueCount   = computed(() => overdueTasks.value.length)
const pendingCount   = computed(() => props.tasks.filter(t => t.status === 0).length)
const inProgressCount = computed(() => props.tasks.filter(t => t.status === 1).length)
const completedCount = computed(() => props.tasks.filter(t => t.status === 2).length)

const filteredTasks = computed(() => {
  let list = props.tasks

  // Exclure les tâches "en retard" déjà affichées en haut
  if (statusFilter.value === 'all') {
    list = list.filter(t => !overdueIds.value.has(t.id))
  }

  if (statusFilter.value === 'active') {
    list = list.filter(t => t.status !== 2 && t.status !== 3)
  } else if (statusFilter.value === 'completed') {
    list = list.filter(t => t.status === 2)
  }

  if (priorityFilter.value !== null) {
    list = list.filter(t => t.priority === priorityFilter.value)
  }

  return [...list].sort((a, b) => {
    // Urgentes d'abord, puis par priorité, puis par date
    if (b.priority !== a.priority) return b.priority - a.priority
    if (a.dueDate && b.dueDate) return new Date(a.dueDate) - new Date(b.dueDate)
    return new Date(b.createdAt) - new Date(a.createdAt)
  })
})

function countByStatus(key) {
  if (key === 'all')       return props.tasks.length
  if (key === 'active')    return props.tasks.filter(t => t.status !== 2 && t.status !== 3).length
  if (key === 'completed') return props.tasks.filter(t => t.status === 2).length
  return 0
}
</script>

<style scoped>
.tasks-tab { display: flex; flex-direction: column; gap: 12px; padding: 16px; }

/* ── Toolbar ── */
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  gap: 10px; flex-wrap: wrap;
}
.toolbar-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.filter-group { display: flex; gap: 4px; flex-wrap: wrap; }

.filter-chip {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 11px; border-radius: 20px;
  border: 1px solid #e2e8f0; background: white;
  font-size: 12px; font-weight: 600; color: #475569;
  cursor: pointer; transition: all .15s;
}
.filter-chip:hover { border-color: #cbd5e1; background: #f8fafc; }
.filter-chip--active {
  background: #6366f1; color: white; border-color: #6366f1;
}
.filter-chip--active .chip-count { background: rgba(255,255,255,.25); }

.chip-count {
  background: #f1f5f9; color: #64748b;
  padding: 1px 6px; border-radius: 10px; font-size: 10.5px; font-weight: 700;
}

.priority-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}

.divider-v { width: 1px; height: 20px; background: #e2e8f0; }

.btn-new {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: 9px;
  background: #6366f1; color: white; border: none;
  font-size: 12.5px; font-weight: 700; cursor: pointer; transition: all .15s;
  white-space: nowrap;
}
.btn-new:hover { background: #4f46e5; }

/* ── Stats ── */
.stats-strip {
  display: flex; gap: 8px; flex-wrap: wrap;
}
.stat-pill {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 20px;
  background: #f8fafc; border: 1px solid #e2e8f0; font-size: 12px;
}
.stat-n { font-weight: 800; color: #0f172a; font-size: 13px; }
.stat-l { color: #64748b; font-weight: 600; }

/* ── Overdue ── */
.overdue-section { border-radius: 10px; border: 1px solid #fca5a5; overflow: hidden; }
.overdue-header {
  display: flex; align-items: center; gap: 7px;
  padding: 8px 14px; background: #fef2f2;
  font-size: 12.5px; font-weight: 700; color: #dc2626;
}
.overdue-section .task-list { padding: 8px; display: flex; flex-direction: column; gap: 6px; }

/* ── Liste ── */
.task-list { display: flex; flex-direction: column; gap: 6px; }

/* ── Empty ── */
.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 40px 20px; text-align: center;
}
.empty-icon {
  width: 52px; height: 52px; border-radius: 14px;
  background: #f1f5f9; display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: #cbd5e1;
}
.empty-title { font-size: 14px; color: #64748b; font-weight: 600; margin: 0; }
</style>
