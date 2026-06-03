<template>
  <div
    v-if="visible"
    class="modal-overlay"
    @mousedown.self="closeModal"
  >
    <div class="modal-box">
      <!-- Header -->
      <div class="modal-head">
        <div>
          <p class="modal-eye">{{ task ? 'Édition' : 'Nouvelle tâche' }}</p>
          <h2 class="modal-title">{{ task ? 'Modifier la tâche' : 'Ajouter une tâche' }}</h2>
        </div>
        <button class="modal-close" @click="closeModal">
          <i class="fas fa-xmark"></i>
        </button>
      </div>

      <!-- Form -->
      <form class="modal-form" @submit.prevent="handleSubmit">

        <!-- Titre -->
        <div class="field">
          <label class="label" for="m-title">Titre de la tâche <span class="req">*</span></label>
          <input id="m-title" v-model="title" type="text" required
            placeholder="Ex : Vérifier les références candidat"
            class="input" autocomplete="off" />
        </div>

        <!-- Description -->
        <div class="field">
          <label class="label" for="m-desc">Description</label>
          <textarea id="m-desc" v-model="description" rows="3"
            placeholder="Contexte, instructions, liens utiles..."
            class="input input--textarea"></textarea>
        </div>

        <!-- Priorité + Statut -->
        <div class="field-row">
          <div class="field">
            <label class="label" for="m-priority">Priorité</label>
            <div class="select-wrap">
              <span class="select-dot" :style="{ background: PRIORITY_COLORS[+priority] }"></span>
              <select id="m-priority" v-model="priority" class="input input--select">
                <option value="0">Basse</option>
                <option value="1">Moyenne</option>
                <option value="2">Haute</option>
                <option value="3">Urgente</option>
              </select>
            </div>
          </div>

          <div class="field" v-if="task">
            <label class="label" for="m-status">Statut</label>
            <select id="m-status" v-model="status" class="input input--select">
              <option value="0">En attente</option>
              <option value="1">En cours</option>
              <option value="2">Terminée</option>
              <option value="3">Annulée</option>
            </select>
          </div>
        </div>

        <!-- Échéance + Assigné à -->
        <div class="field-row">
          <div class="field">
            <label class="label" for="m-due">Date d'échéance</label>
            <input id="m-due" v-model="dueDate" type="date"
              :min="todayIso" class="input" />
            <!-- Warning si date dans le passé -->
            <p v-if="isPastDate" class="field-warn">
              <i class="fas fa-triangle-exclamation"></i>
              Cette date est déjà dépassée.
            </p>
          </div>

          <div class="field">
            <label class="label" for="m-assignee">Assigné à</label>
            <div class="select-wrap">
              <i class="fas fa-circle-user select-icon"></i>
              <select id="m-assignee" v-model="assignedUserId" class="input input--select input--padl">
                <option value="">— Non assigné</option>
                <option v-for="u in users" :key="u.id" :value="u.id">
                  {{ u.fullName || u.email }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <!-- Erreur -->
        <div v-if="error" class="error-bar">
          <i class="fas fa-circle-xmark"></i> {{ error }}
        </div>

        <!-- Actions -->
        <div class="modal-foot">
          <button type="button" class="btn btn--ghost" @click="closeModal">Annuler</button>
          <button type="submit" :disabled="loading" class="btn btn--primary">
            <i v-if="loading" class="fas fa-spinner fa-spin"></i>
            {{ loading ? 'Enregistrement...' : (task ? 'Mettre à jour' : 'Créer la tâche') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import { createTask, updateTask } from '../services/taskService'
import apiClient from '../services/api'

const PRIORITY_COLORS = ['#10b981', '#f59e0b', '#ef4444', '#7c3aed']

const props = defineProps({
  visible:    Boolean,
  task:       Object,
  documentId: Number,
})
const emits = defineEmits(['close', 'added', 'updated'])

// ── State ─────────────────────────────────────────────────────────────────────
const title          = ref('')
const description    = ref('')
const priority       = ref('1')
const status         = ref('0')
const dueDate        = ref('')
const assignedUserId = ref('')
const loading        = ref(false)
const error          = ref('')
const users          = ref([])

const todayIso   = new Date().toISOString().split('T')[0]
const isPastDate = computed(() => dueDate.value && dueDate.value < todayIso)

// ── Charger la liste des utilisateurs ────────────────────────────────────────
onMounted(async () => {
  try {
    const res = await apiClient.get('/user')
    users.value = Array.isArray(res.data) ? res.data : res.data?.users ?? []
  } catch {
    // pas bloquant si l'endpoint n'existe pas
  }
})

// ── Reset ─────────────────────────────────────────────────────────────────────
const resetForm = async () => {
  await nextTick()
  title.value          = ''
  description.value    = ''
  priority.value       = '1'
  status.value         = '0'
  dueDate.value        = ''
  assignedUserId.value = ''
  error.value          = ''
  loading.value        = false
}

// ── Watchers ──────────────────────────────────────────────────────────────────
watch(() => props.task, async (t) => {
  if (t) {
    await nextTick()
    title.value          = t.title          ?? ''
    description.value    = t.description    ?? ''
    priority.value       = String(t.priority ?? 1)
    status.value         = String(t.status   ?? 0)
    assignedUserId.value = t.assignedUserId  ?? ''
    dueDate.value        = t.dueDate
      ? new Date(t.dueDate).toISOString().split('T')[0] : ''
  }
}, { immediate: true })

watch(() => props.visible, async (v) => {
  if (v && !props.task) await resetForm()
})

// ── Handlers ──────────────────────────────────────────────────────────────────
function closeModal() { emits('close') }

async function handleSubmit() {
  loading.value = true
  error.value   = ''
  try {
    const assignedUser = users.value.find(u => u.id == assignedUserId.value)
    const taskData = {
      Title:            title.value,
      Description:      description.value || '',
      Priority:         parseInt(priority.value),
      DueDate:          dueDate.value ? new Date(dueDate.value).toISOString() : null,
      DocumentId:       props.documentId,
      AssignedUserId:   assignedUserId.value   ? parseInt(assignedUserId.value) : null,
      AssignedUserName: assignedUser?.fullName ?? assignedUser?.email ?? null,
    }

    if (props.task) {
      const upd = { ...taskData, Status: parseInt(status.value) }
      delete upd.DocumentId
      await updateTask(props.task.id, upd)
      emits('updated', { ...props.task, ...taskData,
        title: taskData.Title, description: taskData.Description,
        priority: taskData.Priority, dueDate: taskData.DueDate,
        status: parseInt(status.value),
        assignedUserId: taskData.AssignedUserId,
        assignedUserName: taskData.AssignedUserName,
      })
    } else {
      const result = await createTask(taskData)
      emits('added', result)
    }

    await resetForm()
    closeModal()
  } catch (e) {
    error.value = e?.response?.data?.message || e?.message || 'Erreur lors de la sauvegarde.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 99999;
  display: flex; align-items: center; justify-content: center;
  background: rgba(15,23,42,.45); backdrop-filter: blur(4px); padding: 16px;
}

.modal-box {
  width: 100%; max-width: 520px;
  background: white; border-radius: 16px;
  border: 1px solid #e2e8f0; box-shadow: 0 24px 48px rgba(15,23,42,.14);
  overflow: hidden;
}

/* ── Header ── */
.modal-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 20px 24px 16px; border-bottom: 1px solid #f1f5f9;
}
.modal-eye   { font-size: 11.5px; font-weight: 700; color: #6366f1; text-transform: uppercase; letter-spacing: .5px; margin: 0 0 3px; }
.modal-title { font-size: 18px; font-weight: 800; color: #0f172a; margin: 0; }
.modal-close {
  width: 32px; height: 32px; border-radius: 8px; border: 1px solid #e2e8f0;
  background: #f8fafc; color: #64748b; cursor: pointer; font-size: 13px;
  display: flex; align-items: center; justify-content: center; transition: all .15s;
  flex-shrink: 0;
}
.modal-close:hover { background: #fee2e2; border-color: #fca5a5; color: #dc2626; }

/* ── Form ── */
.modal-form { padding: 20px 24px; display: flex; flex-direction: column; gap: 14px; }

.field       { display: flex; flex-direction: column; gap: 5px; flex: 1; }
.field-row   { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.label       { font-size: 12.5px; font-weight: 700; color: #374151; }
.req         { color: #ef4444; margin-left: 2px; }

.input {
  padding: 9px 12px; border: 1px solid #e2e8f0; border-radius: 9px;
  font-size: 13.5px; color: #0f172a; background: white;
  transition: border-color .15s, box-shadow .15s; outline: none;
  font-family: inherit; width: 100%; box-sizing: border-box;
}
.input:focus     { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.1); }
.input--textarea { resize: vertical; min-height: 72px; }
.input--select   { appearance: none; cursor: pointer; }
.input--padl     { padding-left: 30px; }

.select-wrap { position: relative; }
.select-dot  {
  position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  width: 8px; height: 8px; border-radius: 50%;
}
.select-icon {
  position: absolute; left: 9px; top: 50%; transform: translateY(-50%);
  font-size: 13px; color: #7c3aed; pointer-events: none;
}

.field-warn {
  display: flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: #d97706; font-weight: 600; margin: 2px 0 0;
}

.error-bar {
  display: flex; align-items: center; gap: 8px;
  background: #fef2f2; border: 1px solid #fca5a5; border-radius: 9px;
  padding: 9px 12px; font-size: 12.5px; color: #dc2626; font-weight: 600;
}

/* ── Footer ── */
.modal-foot {
  display: flex; justify-content: flex-end; gap: 10px;
  padding-top: 14px; border-top: 1px solid #f1f5f9;
}
.btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 18px; border-radius: 9px;
  font-size: 13px; font-weight: 700; cursor: pointer; transition: all .15s;
  border: 1px solid transparent;
}
.btn--ghost   { background: white; border-color: #e2e8f0; color: #475569; }
.btn--ghost:hover   { background: #f8fafc; }
.btn--primary { background: #6366f1; color: white; }
.btn--primary:hover { background: #4f46e5; }
.btn--primary:disabled { opacity: .55; cursor: not-allowed; }
</style>