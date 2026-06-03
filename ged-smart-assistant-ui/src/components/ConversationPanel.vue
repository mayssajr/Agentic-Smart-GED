<template>
  <!-- Backdrop (clique pour fermer) -->
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="conv-backdrop"
      @click="$emit('update:modelValue', false)"
    />
  </Teleport>

  <!-- Drawer glissant -->
  <Teleport to="body">
    <div class="conv-drawer" :class="{ 'conv-drawer--open': modelValue }">

      <!-- Header -->
      <div class="conv-header">
        <span class="conv-title">
          <i class="pi pi-comments"></i> Discussions
        </span>
        <div class="conv-header-actions">
          <button class="new-btn" @click="$emit('new-conversation'); $emit('update:modelValue', false)">
            <i class="pi pi-plus"></i> Nouvelle
          </button>
          <button class="close-btn" @click="$emit('update:modelValue', false)" title="Fermer">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>

      <!-- Contenu -->
      <div v-if="loading" class="conv-state">
        <i class="pi pi-spin pi-spinner"></i> Chargement…
      </div>

      <div v-else-if="conversations.length === 0" class="conv-state">
        <i class="pi pi-comments" style="font-size:32px;opacity:.25"></i>
        <p>Aucune discussion.</p>
        <button class="new-btn-full" @click="$emit('new-conversation'); $emit('update:modelValue', false)">
          Démarrer une discussion
        </button>
      </div>

      <div v-else class="conv-list">
        <!-- Groupe par date -->
        <template v-for="(group, label) in groupedConversations" :key="label">
          <div class="conv-group-label">{{ label }}</div>
          <div
            v-for="conv in group"
            :key="conv.conv_id"
            class="conv-item"
            :class="{ 'conv-item--active': conv.conv_id === activeConvId }"
            @click="selectConv(conv.conv_id)"
          >
            <div class="conv-item-body">
              <p class="conv-item-title">
                {{ conv.title || conv.last_user_msg || 'Discussion' }}
              </p>
              <p class="conv-item-meta">
                <span>{{ formatDate(conv.updated_at) }}</span>
                <span v-if="conv.message_count" class="conv-badge">{{ conv.message_count }}</span>
              </p>
              <p v-if="conv.doc_context" class="conv-item-doc">
                <i class="pi pi-file"></i> {{ conv.doc_context }}
              </p>
            </div>
            <button
              class="conv-delete-btn"
              @click.stop="confirmDelete(conv.conv_id)"
              title="Supprimer"
            >
              <i class="pi pi-trash"></i>
            </button>
          </div>
        </template>
      </div>

      <!-- Confirm suppression -->
      <div v-if="deleteTarget" class="delete-overlay">
        <div class="delete-card">
          <i class="pi pi-exclamation-triangle" style="font-size:24px;color:#ef4444;margin-bottom:.5rem"></i>
          <p>Supprimer cette discussion ?</p>
          <p class="delete-sub">Cette action est irréversible.</p>
          <div class="delete-actions">
            <button class="btn-cancel" @click="deleteTarget = null">Annuler</button>
            <button class="btn-delete" @click="doDelete">Supprimer</button>
          </div>
        </div>
      </div>

    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue:   { type: Boolean, default: false },   // v-model pour open/close
  userId:       { type: String, default: '' },
  activeConvId: { type: String, default: '' },
  apiBase:      { type: String, default: 'http://localhost:8000' },
})

const emit = defineEmits([
  'update:modelValue',
  'select-conversation',
  'new-conversation',
  'conversation-deleted',
])

const conversations = ref([])
const loading       = ref(false)
const deleteTarget  = ref(null)

const load = async () => {
  if (!props.userId) return
  loading.value = true
  try {
    const r = await fetch(
      `${props.apiBase}/conversations?user_id=${encodeURIComponent(props.userId)}`
    )
    if (r.ok) {
      const d = await r.json()
      conversations.value = d.conversations || []
    }
  } catch (e) {
    console.error('[ConvPanel]', e)
  } finally {
    loading.value = false
  }
}

// Grouper par date (Aujourd'hui / Cette semaine / Plus ancien)
const groupedConversations = computed(() => {
  const groups = {}
  const now   = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const week  = new Date(today); week.setDate(week.getDate() - 7)

  for (const conv of conversations.value) {
    const d = conv.updated_at ? new Date(conv.updated_at) : new Date(0)
    let label
    if (d >= today)      label = "Aujourd'hui"
    else if (d >= week)  label = 'Cette semaine'
    else                 label = 'Plus ancien'
    if (!groups[label]) groups[label] = []
    groups[label].push(conv)
  }
  return groups
})

const selectConv = (id) => {
  emit('select-conversation', id)
  emit('update:modelValue', false)   // fermer le drawer après sélection
}

const confirmDelete = (id) => { deleteTarget.value = id }

const doDelete = async () => {
  const id = deleteTarget.value
  deleteTarget.value = null
  try {
    const r = await fetch(
      `${props.apiBase}/conversations/${id}?user_id=${encodeURIComponent(props.userId)}`,
      { method: 'DELETE' }
    )
    if (r.ok) {
      conversations.value = conversations.value.filter(c => c.conv_id !== id)
      emit('conversation-deleted', id)
    }
  } catch (e) {
    console.error('[ConvPanel] delete', e)
  }
}

const formatDate = (iso) => {
  if (!iso) return ''
  try {
    const d    = new Date(iso)
    const now  = new Date()
    const diff = now - d
    const min  = Math.floor(diff / 60000)
    const h    = Math.floor(diff / 3600000)
    const day  = Math.floor(diff / 86400000)
    if (min < 1)  return "À l'instant"
    if (min < 60) return `${min} min`
    if (h   < 24) return `${h} h`
    if (day < 7)  return `${day} j`
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })
  } catch { return '' }
}

// Charger au premier open
watch(() => props.modelValue, (open) => {
  if (open) load()
})

watch(() => props.userId, () => {
  if (props.modelValue) load()
})

defineExpose({ refresh: load })
</script>

<style scoped>
/* ── Backdrop ── */
.conv-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, .35);
  z-index: 200;
  animation: fadeIn .2s ease;
}

@keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
@keyframes slideIn { from { transform: translateX(-100%) } to { transform: translateX(0) } }

/* ── Drawer ── */
.conv-drawer {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  width: 280px;
  background: white;
  z-index: 201;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 24px rgba(0, 0, 0, .12);
  transform: translateX(-100%);
  transition: transform .25s cubic-bezier(.4, 0, .2, 1);
  overflow: hidden;
}

.conv-drawer--open {
  transform: translateX(0);
}

/* ── Header ── */
.conv-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1rem .875rem;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
  background: white;
}

.conv-title {
  font-size: 14px;
  font-weight: 600;
  color: #111;
  display: flex;
  align-items: center;
  gap: .4rem;
}

.conv-header-actions {
  display: flex;
  align-items: center;
  gap: .4rem;
}

.new-btn {
  display: flex;
  align-items: center;
  gap: .3rem;
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid #e0e7ff;
  background: #f5f3ff;
  color: #4f46e5;
  cursor: pointer;
  font-weight: 500;
  transition: all .15s;
}
.new-btn:hover { background: #ede9fe; border-color: #a5b4fc; }

.close-btn {
  width: 28px; height: 28px;
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
  transition: all .15s;
}
.close-btn:hover { background: #f3f4f6; color: #374151; }

/* ── État vide / loading ── */
.conv-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .6rem;
  padding: 2.5rem 1rem;
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
  flex: 1;
}

.new-btn-full {
  font-size: 13px;
  padding: 7px 18px;
  border-radius: 20px;
  border: 1px solid #e0e7ff;
  background: #f5f3ff;
  color: #4f46e5;
  cursor: pointer;
  margin-top: .5rem;
  font-weight: 500;
}

/* ── Liste ── */
.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: .5rem 0 1rem;
}

.conv-group-label {
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: .06em;
  padding: .75rem 1rem .25rem;
}

.conv-item {
  display: flex;
  align-items: flex-start;
  gap: .5rem;
  padding: .65rem 1rem;
  cursor: pointer;
  transition: background .12s;
  border-left: 3px solid transparent;
  position: relative;
}
.conv-item:hover { background: #f9fafb; }
.conv-item--active {
  background: #f5f3ff;
  border-left-color: #6366f1;
}

.conv-item-body { flex: 1; min-width: 0; }

.conv-item-title {
  font-size: 13px;
  font-weight: 500;
  color: #111;
  margin: 0 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.conv-item--active .conv-item-title { color: #4f46e5; }

.conv-item-meta {
  display: flex;
  align-items: center;
  gap: .35rem;
  font-size: 11px;
  color: #9ca3af;
  margin: 0;
}

.conv-badge {
  background: #e0e7ff;
  color: #4f46e5;
  border-radius: 10px;
  padding: 0 5px;
  font-size: 10px;
  font-weight: 600;
}

.conv-item-doc {
  font-size: 10px;
  color: #9ca3af;
  margin: 2px 0 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
  display: flex;
  align-items: center;
  gap: 3px;
}

.conv-delete-btn {
  opacity: 0;
  border: none;
  background: transparent;
  color: #d1d5db;
  cursor: pointer;
  font-size: 12px;
  padding: 3px 5px;
  border-radius: 5px;
  transition: all .12s;
  flex-shrink: 0;
  margin-top: 2px;
}
.conv-item:hover .conv-delete-btn { opacity: 1; }
.conv-delete-btn:hover { color: #ef4444; background: #fef2f2; }

/* ── Confirmation suppression ── */
.delete-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, .92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  backdrop-filter: blur(2px);
}

.delete-card {
  background: white;
  border-radius: 14px;
  padding: 1.5rem 1.25rem;
  max-width: 240px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0, 0, 0, .12);
  border: 1px solid #fee2e2;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.delete-card p {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 .25rem;
  color: #111;
}

.delete-sub {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 400 !important;
}

.delete-actions {
  display: flex;
  gap: .5rem;
  margin-top: 1rem;
}

.btn-cancel {
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  color: #374151;
  cursor: pointer;
  font-size: 13px;
}

.btn-delete {
  padding: 7px 14px;
  border-radius: 8px;
  border: none;
  background: #ef4444;
  color: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
}
</style>