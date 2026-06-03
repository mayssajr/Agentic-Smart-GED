<template>
  <!-- Message utilisateur -->
  <div v-if="message.isUser" class="row row-user">
    <div class="bubble bubble-user">
      <p class="msg-text">{{ message.text }}</p>
      <span class="msg-time">{{ message.time }}</span>
    </div>
  </div>

  <!-- Message assistant -->
  <div v-else class="row row-assistant">
    <div class="assistant-dot"><i class="pi pi-sparkles"></i></div>
    <div class="assistant-col">

      <!-- Texte standard -->
      <div v-if="!message.type || message.type === 'text'" class="bubble bubble-assistant">
        <p class="msg-text" v-html="formatText(message.text)"></p>
        <span class="msg-time">{{ message.time }}</span>
      </div>

      <!-- Erreur -->
      <div v-else-if="message.type === 'error'" class="bubble bubble-error">
        <div class="bubble-icon-row">
          <i class="pi pi-exclamation-triangle"></i>
          <p class="msg-text">{{ message.text }}</p>
        </div>
        <span class="msg-time">{{ message.time }}</span>
      </div>

      <!-- Résultats de recherche -->
      <div v-else-if="message.type === 'documents'" class="bubble bubble-assistant doc-card">
        <p class="msg-text mb-2" v-html="formatText(message.text)"></p>
        <div class="doc-list">
          <div v-for="(doc, i) in message.documents" :key="i" class="doc-item" @click="$emit('open-file', doc)">
            <div class="doc-icon">
              <i :class="doc.type === 'pdf' ? 'pi pi-file-pdf' : 'pi pi-file'"></i>
            </div>
            <div class="doc-info">
              <span class="doc-name">{{ doc.name }}</span>
              <span v-if="doc.subtitle" class="doc-sub">{{ doc.subtitle }}</span>
            </div>
            <button v-if="doc.fileId || doc.documentId" class="doc-open-btn" @click.stop="$emit('open-file', doc)">
              <i class="pi pi-external-link"></i>
            </button>
          </div>
        </div>
        <div class="doc-actions">
          <button
            class="doc-summarize-btn"
            @click="$emit('action', { action: 'Résume le document actuel', message })"
          >
            <i class="pi pi-file-edit"></i> Résumer ce document
          </button>
        </div>
        <span class="msg-time">{{ message.time }}</span>
      </div>

      <!-- Action card -->
      <div v-else-if="message.type === 'action_card'" class="bubble bubble-assistant action-card">
        <div class="action-header">
          <i class="pi pi-bolt action-icon"></i>
          <p class="msg-text">{{ message.text }}</p>
        </div>
        <span class="msg-time">{{ message.time }}</span>
      </div>

      <!-- ── Brouillon email éditable ──────────────────────────────────── -->
      <div v-else-if="message.type === 'email_draft'" class="bubble bubble-assistant email-card">
        <div class="email-header-bar">
          <i class="pi pi-envelope"></i>
          <span>Brouillon d'email</span>
          <span v-if="localDraft.HasAttachment" class="attach-badge">
            <i class="pi pi-paperclip"></i> {{ localDraft.Filename || 'pièce jointe' }}
          </span>
          <span v-else class="attach-badge attach-badge--warn">
            <i class="pi pi-exclamation-triangle"></i> sans pièce jointe
          </span>
        </div>

        <!-- Champ À -->
        <div class="email-field-row">
          <label class="email-field-label">À</label>
          <input
            class="email-field-input"
            v-model="localDraft.To"
            placeholder="destinataire@email.com"
            @input="emitUpdate"
          />
        </div>

        <!-- Champ Objet -->
        <div class="email-field-row">
          <label class="email-field-label">Objet</label>
          <input
            class="email-field-input"
            v-model="localDraft.Subject"
            placeholder="Objet de l'email"
            @input="emitUpdate"
          />
        </div>

        <!-- Corps éditable -->
        <div class="email-body-area">
          <textarea
            class="email-body-input"
            v-model="localDraft.Body"
            rows="6"
            @input="emitUpdate"
          />
        </div>

        <span class="msg-time">{{ message.time }}</span>

        <!-- FIX: buttons always rendered, onSendClick uses local actionId -->
        <div class="draft-actions">
          <button class="draft-btn draft-btn--send" :disabled="sending" @click="onSendClick">
            <i :class="sending ? 'pi pi-spin pi-spinner' : 'pi pi-send'"></i>
            {{ sending ? 'Envoi…' : 'Envoyer' }}
          </button>
          <button class="draft-btn draft-btn--cancel" :disabled="sending" @click="onCancelClick">
            <i class="pi pi-times"></i> Annuler
          </button>
        </div>
      </div>

      <!-- Boutons d'action génériques -->
      <div v-if="message.actionButtons?.length && message.type !== 'email_draft'" class="action-buttons">
        <button
          v-for="btn in message.actionButtons" :key="btn.action || btn.Action"
          class="action-btn" :class="btnClass(btn.severity || btn.Severity)"
          @click="$emit('action', { action: btn.action || btn.Action, message })"
        >{{ btn.label || btn.Label }}</button>
      </div>

      <!-- Suggestions -->
      <div v-if="message.suggestions?.length" class="suggestions">
        <button
          v-for="s in message.suggestions" :key="s.action || s.Action"
          class="suggestion-chip"
          @click="$emit('action', { action: s.action || s.label || s.Action, message })"
        >{{ s.label || s.Label }}</button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  message:  { type: Object, required: true },
  msgIndex: { type: Number, default: -1 },
})

const emit = defineEmits(['action', 'open-file', 'send-email', 'update-draft'])

const sending = ref(false)

// Copie locale du brouillon pour l'édition
const localDraft = ref({
  To:            '',
  Subject:       '',
  Body:          '',
  Filename:      '',
  HasAttachment: false,
})

// Synchroniser depuis message.emailDraft (supporte les deux casings)
const syncDraft = (d) => {
  if (!d) return
  localDraft.value = {
    To:            d.To      || d.to      || '',
    Subject:       d.Subject || d.subject || '',
    Body:          d.Body    || d.body    || '',
    Filename:      d.Filename || d.filename || '',
    HasAttachment: d.HasAttachment ?? d.hasAttachment ?? d.has_attachment ?? false, // ← ajout hasAttachment
  }
}

watch(() => props.message.emailDraft, syncDraft, { immediate: true, deep: true })

const emitUpdate = () => {
  emit('update-draft', { msgIndex: props.msgIndex, draft: { ...localDraft.value } })
}

// FIX: get actionId from message directly (not from a prop that might be stale)
const getActionId = () =>
  props.message.emailActionId
  || props.message.email_action_id
  || ''

const onSendClick = () => {
  const actionId = getActionId()
  if (!actionId) {
    // No pending action stored — should not happen, but guard anyway
    console.warn('[MessageBubble] No actionId found on message:', props.message)
    return
  }
  sending.value = true
  emit('send-email', {
    actionId,
    draft: { ...localDraft.value },
    msgIndex: props.msgIndex,
  })
}

const onCancelClick = () => {
  emit('action', { action: 'cancel_email', message: props.message })
}

// Reset sending state if parent re-renders (e.g. after success/error message pushed)
watch(() => props.message, () => { sending.value = false })

const formatText = (text) => {
  if (!text) return ''
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/`(.+?)`/g,'<code>$1</code>')
    .replace(/\n/g,'<br>')
}

const btnClass = (severity) => ({
  'btn-primary':   severity === 'primary',
  'btn-secondary': severity === 'secondary' || !severity,
  'btn-danger':    severity === 'danger',
})
</script>

<style scoped>
.row { display:flex; align-items:flex-end; gap:.5rem; margin:0 .25rem; }
.row-user      { justify-content:flex-end; }
.row-assistant { justify-content:flex-start; }
.assistant-col { display:flex; flex-direction:column; gap:.4rem; max-width:76%; }
.assistant-dot {
  width:28px; height:28px; flex-shrink:0;
  background:linear-gradient(135deg,#6366f1,#8b5cf6);
  border-radius:8px; color:white;
  display:flex; align-items:center; justify-content:center;
  font-size:12px; margin-bottom:2px;
}
.bubble { border-radius:18px; padding:12px 16px; position:relative; }
.bubble-user {
  background:linear-gradient(135deg,#6366f1,#7c3aed); color:white;
  border-radius:18px 18px 4px 18px; max-width:68vw;
}
.bubble-assistant {
  background:white; border:1px solid #e5e7eb;
  border-radius:4px 18px 18px 18px; color:#111;
  box-shadow:0 1px 4px rgba(0,0,0,.05);
}
.bubble-error { background:#fef2f2; border:1px solid #fecaca; border-radius:4px 18px 18px 18px; color:#b91c1c; }
.msg-text { font-size:14px; line-height:1.6; margin:0; }
.msg-text :deep(strong) { font-weight:600; }
.msg-text :deep(code) { background:rgba(0,0,0,.07); padding:1px 5px; border-radius:4px; font-family:monospace; font-size:13px; }
.msg-time { font-size:10px; opacity:.5; display:block; text-align:right; margin-top:6px; }
.bubble-icon-row { display:flex; align-items:flex-start; gap:.5rem; }
.bubble-icon-row .pi { font-size:14px; margin-top:2px; }

/* ── Documents ── */
.doc-card { min-width:300px; }
.mb-2 { margin-bottom:.5rem; }
.doc-list { display:flex; flex-direction:column; gap:.35rem; }
.doc-item { display:flex; align-items:center; gap:.6rem; padding:.5rem .75rem; background:#f9fafb; border-radius:10px; border:1px solid #f3f4f6; cursor:pointer; transition:background .12s; }
.doc-item:hover { background:#f0f9ff; border-color:#bae6fd; }
.doc-icon { font-size:18px; color:#6366f1; }
.doc-info { flex:1; display:flex; flex-direction:column; }
.doc-name { font-size:13px; font-weight:500; color:#111; }
.doc-sub  { font-size:11px; color:#9ca3af; }
.doc-open-btn { border:none; background:transparent; color:#6366f1; cursor:pointer; font-size:14px; padding:2px 4px; border-radius:6px; transition:background .12s; }
.doc-open-btn:hover { background:#ede9fe; }

/* Bouton Résumer sous les documents */
.doc-actions { margin-top:.6rem; }
.doc-summarize-btn {
  display:inline-flex; align-items:center; gap:.35rem;
  font-size:12px; padding:5px 14px;
  border:1px solid #e0e7ff; border-radius:20px;
  background:#f5f3ff; color:#4f46e5;
  cursor:pointer; font-weight:500; transition:all .15s;
}
.doc-summarize-btn:hover { background:#ede9fe; border-color:#a5b4fc; }

/* ── Action card ── */
.action-header { display:flex; align-items:flex-start; gap:.6rem; }
.action-icon   { color:#6366f1; font-size:15px; margin-top:2px; }

/* ── Email brouillon éditable ── */
.email-card { min-width:320px; padding:14px 16px; }

.email-header-bar {
  display:flex; align-items:center; gap:.5rem; flex-wrap:wrap;
  font-size:12px; font-weight:600; color:#6366f1;
  text-transform:uppercase; letter-spacing:.05em;
  padding-bottom:.6rem; border-bottom:1px solid #e5e7eb; margin-bottom:.75rem;
}

.attach-badge {
  display:inline-flex; align-items:center; gap:.3rem;
  font-size:11px; font-weight:500; text-transform:none; letter-spacing:0;
  background:#ecfdf5; color:#059669; border:1px solid #d1fae5;
  border-radius:12px; padding:2px 8px; margin-left:auto;
}
.attach-badge--warn { background:#fffbeb; color:#d97706; border-color:#fde68a; }

.email-field-row {
  display:flex; align-items:center; gap:.6rem; margin-bottom:.5rem;
}
.email-field-label {
  font-size:11px; font-weight:600; color:#9ca3af;
  text-transform:uppercase; min-width:40px; flex-shrink:0;
}
.email-field-input {
  flex:1; font-size:13px; color:#111;
  border:1px solid #e5e7eb; border-radius:8px;
  padding:6px 10px; outline:none; transition:border-color .15s;
  background:white; font-family:inherit;
}
.email-field-input:focus { border-color:#6366f1; box-shadow:0 0 0 3px rgba(99,102,241,.1); }

.email-body-area { margin:.5rem 0 .75rem; }
.email-body-input {
  width:100%; font-size:13px; color:#374151; line-height:1.6;
  background:#f9fafb; border:1px solid #e5e7eb; border-radius:10px;
  padding:.6rem .75rem; resize:vertical; min-height:120px;
  font-family:inherit; outline:none; transition:border-color .15s;
  box-sizing:border-box;
}
.email-body-input:focus { border-color:#6366f1; box-shadow:0 0 0 3px rgba(99,102,241,.1); background:white; }

.draft-actions { display:flex; gap:.5rem; margin-top:.25rem; }
.draft-btn {
  flex:1; font-size:13px; font-weight:500; padding:8px 16px;
  border-radius:10px; border:none; cursor:pointer; transition:all .15s;
  display:flex; align-items:center; justify-content:center; gap:.4rem;
}
.draft-btn:disabled { opacity:.6; cursor:not-allowed; }
.draft-btn--send   { background:#6366f1; color:white; }
.draft-btn--send:hover:not(:disabled) { background:#4f46e5; }
.draft-btn--cancel { background:#f3f4f6; color:#374151; border:1px solid #e5e7eb; }
.draft-btn--cancel:hover:not(:disabled) { background:#e5e7eb; }

/* ── Boutons génériques ── */
.action-buttons { display:flex; gap:.4rem; flex-wrap:wrap; padding-left:.25rem; }
.action-btn { font-size:13px; font-weight:500; padding:6px 14px; border-radius:20px; border:1px solid transparent; cursor:pointer; transition:all .15s; }
.btn-primary   { background:#6366f1; color:white; }
.btn-primary:hover { background:#4f46e5; }
.btn-secondary { background:#f3f4f6; color:#374151; border-color:#e5e7eb; }
.btn-secondary:hover { background:#e5e7eb; }
.btn-danger    { background:#fef2f2; color:#dc2626; border-color:#fecaca; }
.btn-danger:hover { background:#fee2e2; }

/* ── Suggestions ── */
.suggestions { display:flex; gap:.35rem; flex-wrap:wrap; padding-left:.25rem; }
.suggestion-chip {
  font-size:12px; padding:4px 12px;
  border:1px solid #e0e7ff; border-radius:20px;
  background:#f5f3ff; color:#4f46e5; cursor:pointer; transition:all .12s;
}
.suggestion-chip:hover { background:#ede9fe; border-color:#a5b4fc; }
</style>