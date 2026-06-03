<template>
  <article
    class="task-card"
    :class="{
      'task-card--overdue':    isOverdue,
      'task-card--completed':  task.status === 2,
      'task-card--urgent':     task.priority === 3,
    }"
  >
    <!-- Bande latérale priorité -->
    <div class="task-priority-bar" :style="{ background: priorityColor }"></div>

    <div class="task-body">
      <!-- En-tête : titre + badges -->
      <div class="task-top">
        <div class="task-title-row">
          <h4 class="task-title" :class="{ 'task-title--done': task.status === 2 }">
            {{ task.title }}
          </h4>
          <!-- Badge EN RETARD -->
          <span v-if="isOverdue" class="badge badge-overdue">
            <i class="fas fa-triangle-exclamation"></i> En retard
          </span>
        </div>
        <div class="task-badges">
          <span class="badge" :class="priorityBadgeClass">{{ priorityLabel }}</span>
          <span class="badge" :class="statusBadgeClass">{{ statusLabel }}</span>
        </div>
      </div>

      <!-- Description -->
      <p v-if="task.description" class="task-desc">{{ task.description }}</p>

      <!-- Pied : meta + actions -->
      <div class="task-foot">
        <div class="task-meta">
          <!-- Date de création -->
          <span class="meta-item">
            <i class="fas fa-calendar-plus"></i>
            {{ formatDate(task.createdAt) }}
          </span>
          <!-- Échéance -->
          <span v-if="task.dueDate" class="meta-item" :class="{ 'meta-item--red': isOverdue }">
            <i class="fas fa-clock"></i>
            Échéance : {{ formatDate(task.dueDate) }}
          </span>
          <!-- Assigné à -->
          <span v-if="task.assignedUserName" class="meta-item meta-item--assignee">
            <i class="fas fa-circle-user"></i>
            {{ task.assignedUserName }}
          </span>
        </div>

        <div class="task-actions">
          <!-- Sélecteur de statut -->
          <select
            :value="task.status"
            class="status-select"
            @change="$emit('status-change', task.id, parseInt($event.target.value))"
          >
            <option value="0">En attente</option>
            <option value="1">En cours</option>
            <option value="2">Terminée</option>
            <option value="3">Annulée</option>
          </select>
          <button class="icon-btn icon-btn--edit"  title="Modifier" @click="$emit('edit', task)">
            <i class="fas fa-pen-to-square"></i>
          </button>
          <button class="icon-btn icon-btn--delete" title="Supprimer" @click="$emit('delete', task.id)">
            <i class="fas fa-trash-can"></i>
          </button>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ task: { type: Object, required: true } })
defineEmits(['status-change', 'edit', 'delete'])

// ── Retard ────────────────────────────────────────────────────────────────────
const isOverdue = computed(() =>
  props.task.dueDate &&
  props.task.status !== 2 &&
  props.task.status !== 3 &&
  new Date(props.task.dueDate) < new Date()
)

// ── Priorité ─────────────────────────────────────────────────────────────────
const PRIORITY_COLORS  = ['#10b981', '#f59e0b', '#ef4444', '#7c3aed']
const PRIORITY_LABELS  = ['Basse', 'Moyenne', 'Haute', 'Urgente']
const PRIORITY_CLASSES = [
  'badge--green', 'badge--amber', 'badge--red', 'badge--purple',
]

const priorityColor      = computed(() => PRIORITY_COLORS[props.task.priority]  ?? PRIORITY_COLORS[1])
const priorityLabel      = computed(() => PRIORITY_LABELS[props.task.priority]  ?? 'Moyenne')
const priorityBadgeClass = computed(() => PRIORITY_CLASSES[props.task.priority] ?? 'badge--amber')

// ── Statut ────────────────────────────────────────────────────────────────────
const STATUS_LABELS  = ['En attente', 'En cours', 'Terminée', 'Annulée']
const STATUS_CLASSES = ['badge--slate', 'badge--blue', 'badge--emerald', 'badge--slate']

const statusLabel      = computed(() => STATUS_LABELS[props.task.status]  ?? 'En attente')
const statusBadgeClass = computed(() => STATUS_CLASSES[props.task.status] ?? 'badge--slate')

// ── Formatage date ────────────────────────────────────────────────────────────
const formatDate = (d) => {
  if (!d) return ''
  return new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.task-card {
  display: flex; background: white;
  border: 1px solid #e2e8f0; border-radius: 12px;
  overflow: hidden; transition: box-shadow .2s, transform .2s;
}
.task-card:hover { box-shadow: 0 4px 16px rgba(15,23,42,.07); transform: translateY(-1px); }
.task-card--overdue   { border-color: #fca5a5; }
.task-card--completed { opacity: .65; }
.task-card--urgent    { border-color: #c4b5fd; }

.task-priority-bar { width: 4px; flex-shrink: 0; }

.task-body {
  flex: 1; padding: 14px 16px;
  display: flex; flex-direction: column; gap: 8px;
}

/* ── Top ── */
.task-top { display: flex; flex-direction: column; gap: 6px; }

.task-title-row {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.task-title {
  font-size: 14px; font-weight: 600; color: #0f172a; margin: 0; flex: 1;
}
.task-title--done { text-decoration: line-through; color: #94a3b8; }

.task-badges { display: flex; gap: 5px; flex-wrap: wrap; }

/* ── Description ── */
.task-desc {
  font-size: 12.5px; color: #64748b; line-height: 1.5; margin: 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

/* ── Pied ── */
.task-foot {
  display: flex; justify-content: space-between; align-items: center;
  gap: 8px; flex-wrap: wrap; margin-top: 2px;
}
.task-meta  { display: flex; flex-wrap: wrap; gap: 10px; }
.meta-item  { display: flex; align-items: center; gap: 4px; font-size: 11.5px; color: #94a3b8; }
.meta-item i { font-size: 11px; }
.meta-item--red      { color: #ef4444; font-weight: 600; }
.meta-item--assignee { color: #7c3aed; }

.task-actions { display: flex; align-items: center; gap: 6px; }

.status-select {
  font-size: 11.5px; font-weight: 600; padding: 4px 8px; border-radius: 7px;
  border: 1px solid #e2e8f0; background: white; color: #475569; cursor: pointer;
  outline: none; transition: border-color .15s;
}
.status-select:focus { border-color: #6366f1; }

.icon-btn {
  width: 30px; height: 30px; border-radius: 7px; border: 1px solid #e2e8f0;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; font-size: 12px; transition: all .15s;
}
.icon-btn--edit   { background: #f8fafc; color: #64748b; }
.icon-btn--edit:hover   { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }
.icon-btn--delete { background: #fef2f2; color: #dc2626; border-color: #fecaca; }
.icon-btn--delete:hover { background: #fee2e2; }

/* ── Badges ── */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 20px; font-size: 10.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .3px;
}
.badge-overdue   { background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; font-size: 10px; }
.badge--green    { background: #dcfce7; color: #16a34a; }
.badge--amber    { background: #fef3c7; color: #b45309; }
.badge--red      { background: #fee2e2; color: #dc2626; }
.badge--purple   { background: #ede9fe; color: #7c3aed; }
.badge--slate    { background: #f1f5f9; color: #475569; }
.badge--blue     { background: #dbeafe; color: #1d4ed8; }
.badge--emerald  { background: #dcfce7; color: #059669; }
</style>