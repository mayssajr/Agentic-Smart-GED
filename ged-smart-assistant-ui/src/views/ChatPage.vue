<template>
  <div class="chat-shell">
    <ConversationPanel
      v-model="showConvPanel" ref="convPanelRef"
      :user-id="userId" :active-conv-id="activeConvId" :api-base="PYTHON_API"
      @select-conversation="loadConversation"
      @new-conversation="startNewConversation"
      @conversation-deleted="onConversationDeleted"
    />
    <div class="chat-main">
      <header class="chat-header">
        <div class="header-left">
          <button class="icon-btn" :class="{ 'icon-btn--active': showConvPanel }" @click="showConvPanel = !showConvPanel"><i class="pi pi-comments"></i></button>
          <button class="icon-btn" @click="goHome"><i class="pi pi-arrow-left"></i></button>
          <div class="assistant-avatar"><i class="pi pi-sparkles"></i></div>
          <div class="header-info">
            <span class="header-title">Assistant MiniGED</span>
            <span class="header-status">
              <span class="status-dot" :class="isBlocked ? 'status-off' : 'status-on'"></span>
              {{ isBlocked ? 'Déconnecté' : 'En ligne' }}
            </span>
          </div>
        </div>
        <div class="header-right">
          <button class="new-conv-btn" @click="startNewConversation"><i class="pi pi-plus"></i><span class="new-conv-label">Nouvelle</span></button>
          <span v-if="displayName" class="user-chip"><i class="pi pi-user"></i>{{ displayName }}</span>
          <button class="icon-btn danger" @click="handleLogout"><i class="pi pi-sign-out"></i></button>
        </div>
      </header>

      <main class="chat-messages" ref="messagesContainer">
        <div v-if="isBlocked" class="centered-card">
          <div class="blocked-card">
            <div class="blocked-icon"><i class="pi pi-lock"></i></div>
            <h3>Connexion requise</h3><p>{{ blockedMessage }}</p>
          </div>
        </div>
        <div v-else-if="messages.length === 0" class="centered-card">
          <div class="welcome-card">
            <div class="welcome-icon"><i class="pi pi-sparkles"></i></div>
            <h2>{{ welcomeTitle }}</h2>
            <p>Posez-moi une question sur vos documents, demandez un résumé, une recherche, ou une analyse juridique.</p>
            <div class="quick-actions">
              <button v-for="q in quickQuestions" :key="q" class="quick-btn" @click="handleSend(q)">{{ q }}</button>
            </div>
          </div>
        </div>
        <div v-else class="messages-list">
          <MessageBubble
            v-for="(msg, idx) in messages" :key="idx" :message="msg" :msg-index="idx"
            @action="handleAction" @open-file="openFile"
            @send-email="handleSendEmail" @update-draft="handleUpdateDraft"
          />
          <div v-if="isTyping" class="typing-row">
            <div class="assistant-dot"><i class="pi pi-sparkles"></i></div>
            <div class="typing-bubble"><span></span><span></span><span></span></div>
          </div>
        </div>
      </main>

      <footer class="chat-footer">
        <ChatInput :disabled="isBlocked || isBootstrapping" @send="handleSend" @voice-input="voiceMode = true" />
        <p class="footer-hint"><i class="pi pi-info-circle"></i> L'assistant peut faire des erreurs. Vérifiez les informations importantes.</p>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import MessageBubble from '../components/MessageBubble.vue'
import ChatInput from '../components/ChatInput.vue'
import ConversationPanel from '../components/ConversationPanel.vue'
import { assistantAuthService, assistantChatService } from '../services/assistantApi'
import { announceAssistantReady, ASSISTANT_MESSAGE_TYPES, isAllowedParentOrigin } from '../services/assistantEmbed'


const PYTHON_API  = import.meta.env.VITE_PYTHON_API_URL  || 'http://localhost:8000'
const MINIGED_API = import.meta.env.VITE_MINIGED_API_URL || 'http://localhost:5092'

const messages = ref([]), isTyping = ref(false), messagesContainer = ref(null)
const currentUser = ref(null), isBlocked = ref(false), isBootstrapping = ref(true)
const blockedMessage = ref('Connexion à MiniGED...')
const showConvPanel = ref(false), activeConvId = ref(''), convPanelRef = ref(null)

const userId      = computed(() => { const u = currentUser.value; return u ? String(u.id || u.userId || u.username || '') : '' })
const displayName = computed(() => currentUser.value?.username || currentUser.value?.fullName || '')
const currentDocType = ref('')
const welcomeTitle = computed(() => displayName.value ? `Bonjour, ${displayName.value} 👋` : 'Bonjour 👋')
const quickQuestions = computed(() => {
  const docType = currentDocType.value
  if (docType === 'CV' || docType === 'Candidature' || docType === 'Lettre de motivation') {
    return [
      'Résume les compétences techniques',
      'Quelles sont les lacunes de ce candidat ?',
      'Compare avec l\'offre d\'emploi',
      'Points forts et points faibles ?',
    ]
  }
  if (docType === 'Contrat de travail') {
    return [
      'Quelles sont les clauses de rupture ?',
      'Y a-t-il une clause de non-concurrence ?',
      'Quelle est la durée de préavis ?',
      'Analyse juridique du contrat',
    ]
  }
  if (docType === 'Offre d\'emploi') {
    return [
      'Résume ce poste en 3 points',
      'Quelles compétences sont requises ?',
      'Quel est le niveau d\'expérience demandé ?',
    ]
  }
  return [
    'Résume mon dernier document',
    'Recherche les contrats CDI',
    'Quels documents nécessitent une signature ?',
    'Analyse juridique du dernier contrat',
  ]
})

const goHome = () => window.history.back()
const scrollToBottom = async () => { await nextTick(); if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight }
const now = () => new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
const pushMsg = (msg) => messages.value.push({ time: now(), ...msg })

// ── Voice mode (TTS) ────────────────────────────────────────────────────────
const voiceMode = ref(false)  // activé automatiquement après dictée vocale

function speakText(text) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const clean = text.replace(/\*\*/g, '').replace(/#{1,6}\s/g, '').replace(/\n+/g, ' ').slice(0, 600)
  const utt = new SpeechSynthesisUtterance(clean)
  utt.lang = 'fr-FR'
  utt.rate = 1.05
  const voices = window.speechSynthesis.getVoices()
  const frVoice = voices.find(v => v.lang.startsWith('fr'))
  if (frVoice) utt.voice = frVoice
  utt.onend = () => { voiceMode.value = false }  // désactive après lecture
  window.speechSynthesis.speak(utt)
}
// ── Conversations ─────────────────────────────────────────────────────────────
const startNewConversation = async () => {
  activeConvId.value = ''; messages.value = []
  if (userId.value) {
    try {
      const r = await fetch(`${PYTHON_API}/conversations/new`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user_id:userId.value}) })
      if (r.ok) { const d = await r.json(); activeConvId.value = d.conv_id }
    } catch {}
  }
  pushMsg({ isUser:false, type:'text', text:'Nouvelle discussion démarrée. Comment puis-je vous aider ?' })
  convPanelRef.value?.refresh(); await scrollToBottom()
}

const loadConversation = async (convId) => {
  if (convId === activeConvId.value) return
  activeConvId.value = convId; messages.value = []
  try {
    const r = await fetch(`${PYTHON_API}/conversations/${convId}?user_id=${encodeURIComponent(userId.value)}&limit=50`)
    if (r.ok) {
      const data = await r.json()
      for (const msg of (data.messages||[])) {
        if (msg.role==='system') continue
        pushMsg({ isUser:msg.role==='user', type:'text', text:msg.content,
          time: msg.created_at ? new Date(msg.created_at).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}) : now() })
      }
      if (!messages.value.length) pushMsg({ isUser:false, type:'text', text:'Discussion vide.' })
    }
    const lastAssistantMsg = [...(data.messages||[])].reverse().find(m => m.role === 'assistant')
    if (lastAssistantMsg?.metadata?.doc_type) currentDocType.value = lastAssistantMsg.metadata.doc_type
  } catch { pushMsg({ isUser:false, type:'error', text:'Impossible de charger la discussion.' }) }
  await scrollToBottom()
}

const onConversationDeleted = (convId) => {
  if (convId === activeConvId.value) { activeConvId.value=''; messages.value=[]; pushMsg({isUser:false,type:'text',text:'Discussion supprimée.'}) }
}

// ── Envoi message ─────────────────────────────────────────────────────────────
const handleSend = async (text) => {
  if (isBlocked.value || isBootstrapping.value || !text.trim()) return
  if (!activeConvId.value && userId.value) {
    try {
      const r = await fetch(`${PYTHON_API}/conversations/new`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user_id:userId.value}) })
      if (r.ok) { const d = await r.json(); activeConvId.value=d.conv_id; convPanelRef.value?.refresh() }
    } catch {}
  }
  pushMsg({ isUser:true, text }); await scrollToBottom()
  isTyping.value = true; await scrollToBottom()
  try {
    const response = await assistantChatService.sendMessage(text)
    processResponse(response)
    setTimeout(() => convPanelRef.value?.refresh(), 1000)
  } catch (err) {
    if (err.response?.status === 401) { isBlocked.value=true; blockedMessage.value="Session expirée." }
    else pushMsg({ isUser:false, type:'error', text:err.response?.data?.message||'Une erreur est survenue.' })
  } finally { isTyping.value=false; await scrollToBottom() }
}

// ── Traitement réponse ────────────────────────────────────────────────────────
const processResponse = (response) => {
  // ── Sync doc type (toutes branches) ────────────────────────────────────
  const respDocType = response.doc_type || response.docType || response.document_type
                   || response.DocumentType
  if (respDocType) currentDocType.value = respDocType

  const tool = response.tool || response.Tool
  const replyText = response.reply || response.Reply || response.direct_answer || ''

  // ── Email draft ─────────────────────────────────────────────────────────
  const rawDraft = response.email_draft || response.emailDraft || response.EmailDraft
  const emailActionId = response.email_action_id || response.emailActionId

  const isDraftResponse =
    response.action_done === 'email_draft_ready'
    || (tool === 'send_email' && rawDraft)
    || emailActionId

  if (isDraftResponse) {
    const d = rawDraft || {}
    pushMsg({
      isUser:       false,
      type:         'email_draft',
      text:         replyText || 'Voici le brouillon d\'email :',
      emailDraft: {
        To:            d.To      || d.to      || '',
        Subject:       d.Subject || d.subject || '',
        Body:          d.Body    || d.body    || '',
        Filename:      d.Filename || d.filename || '',
        HasAttachment: d.HasAttachment ?? d.has_attachment ?? false,
      },
      emailActionId: emailActionId || '',
    })
    return
  }
  // ── Navigation document ──────────────────────────────────────────────────────
const actionDone = response.action_done || response.actionDone
const actionResult = response.action_result || response.actionResult || {}

if (actionDone === 'open_document' && actionResult.document_id) {
  const docId    = actionResult.document_id
  const docTitle = actionResult.document_title || ''

  // Notifier le parent (DashboardView) pour naviguer
  const navPayload = { type: 'NAVIGATE_DOCUMENT', payload: { documentId: docId } }

  if (window.parent !== window) {
    window.parent.postMessage(navPayload, '*')
  }
  window.postMessage(navPayload, window.location.origin)

  // Mettre à jour le contexte document de l'assistant
  assistantChatService.setDocumentContext({
    documentId: String(docId),
    filename: docTitle,
  })

  pushMsg({
    isUser: false,
    type: 'text',
    text: replyText || `Navigation vers le document **${docTitle || docId}**…`,
  })
  return
}

  // ── Résultats de recherche ──────────────────────────────────────────────
  if (tool === 'search_documents' && response.toolResult?.results?.items?.length) {
    pushMsg({
      isUser:        false,
      type:          'documents',
      text:          replyText,
      documents:     (response.toolResult.results.items || []).slice(0, 5).map(h => ({
        name:       h.documentTitle || h.fileName || 'Document',
        subtitle:   h.snippet || h.fileName || '',
        type:       'document',
        documentId: h.documentId || '',
        fileId:     h.fileId || '',
      })),
      actionButtons: response.actionButtons || response.ActionButtons,
      suggestions:   response.suggestions   || response.Suggestions,
    })
    return
  }

  // ── Action card ──────────────────────────────────────────────────────────
  const buttons = response.actionButtons || response.ActionButtons
  if (buttons?.length) {
    pushMsg({
      isUser:        false,
      type:          'action_card',
      text:          replyText,
      tool,
      actionButtons: buttons,
      suggestions:   response.suggestions || response.Suggestions,
      toolArguments: response.toolArguments || response.ToolArguments,
    })
    return
  }

  // ── Texte simple + TTS ───────────────────────────────────────────────────
  pushMsg({
    isUser:      false,
    type:        'text',
    text:        replyText,
    suggestions: response.suggestions || response.Suggestions,
  })

  // Web Speech API — lit la réponse à voix haute si voiceMode actif
  if (voiceMode.value && replyText) {
    speakText(replyText)
  }
}

// ── Envoi email confirmé ──────────────────────────────────────────────────────
// FIX: called by MessageBubble's "Envoyer" button via @send-email event
const handleSendEmail = async ({ actionId, draft, msgIndex }) => {
  // Guard: if no actionId, show an error instead of silently failing
  if (!actionId) {
    pushMsg({ isUser:false, type:'error', text:'Impossible d\'envoyer : identifiant d\'action manquant.' })
    return
  }
  isTyping.value = true
  try {
    const r = await fetch(`${PYTHON_API}/confirm-action`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
         action_id: actionId,
          confirmed: true,
          payload_override: {          
          to:      draft.To      || draft.to      || '',
          subject: draft.Subject || draft.subject || '',
          body:    draft.Body    || draft.body    || '',
          }

         })
    })
    const result = await r.json()
    if (msgIndex >= 0 && messages.value[msgIndex]) {
      messages.value[msgIndex] = { ...messages.value[msgIndex], _sent: true }
    }
    if (result.success) {
      const att = result.has_attachment ? ' avec pièce jointe' : ''
      pushMsg({ isUser:false, type:'text', text:`Email envoyé à **${result.email_to}**${att}.` })
    } else {
      pushMsg({ isUser:false, type:'error', text:`Échec : ${result.error || 'erreur inconnue'}` })
    }
  } catch (e) {
    if (msgIndex >= 0 && messages.value[msgIndex]) {
      messages.value[msgIndex] = { ...messages.value[msgIndex], _sent: true }
    }
    pushMsg({ isUser:false, type:'error', text:`Erreur réseau : ${e.message}` })
  } finally { isTyping.value=false; await scrollToBottom() }
}

const handleUpdateDraft = ({ msgIndex, draft }) => {
  if (messages.value[msgIndex]) messages.value[msgIndex].emailDraft = { ...draft }
}

const openFile = (doc) => {
  if (doc.fileId) window.open(`${MINIGED_API}/api/document/pdf/${doc.fileId}`,'_blank')
  else if (doc.documentId) window.open(`${MINIGED_API}/api/document/${doc.documentId}/download`,'_blank')
}

// FIX: handleAction — 'Résume le document actuel' must trigger handleSend not a special path
const handleAction = async ({ action, message }) => {
  if (action === 'confirm_email') {
    await handleSendEmail({ actionId: message.emailActionId || message.email_action_id, draft: message.emailDraft })
    return
  }
  if (action === 'cancel_email' || action === 'cancel') {
    const actionId = message.emailActionId || message.email_action_id
    if (actionId) {
      await fetch(`${PYTHON_API}/confirm-action`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ action_id: actionId, confirmed: false })
      }).catch(() => {})
    }
    pushMsg({ isUser:false, type:'text', text:'Email annulé.' })
    return
  }
  if (action === 'edit_email') {
    pushMsg({ isUser:false, type:'text', text:'Modifiez les champs du brouillon, puis cliquez Envoyer.' })
    return
  }
  // FIX: 'Résume le document actuel' and all other actions → send as chat message
  // This includes analyze, summarize, sign, and any suggestion chip
  await handleSend(action)
}

// ── Auth ──────────────────────────────────────────────────────────────────────
const syncSession = async () => {
  try {
    const s = await assistantAuthService.getSession()
    currentUser.value = s.user||null
    if (s.isAuthenticated && currentUser.value) { isBlocked.value=false; isBootstrapping.value=false; return true }
  } catch (e) { if (e.response?.status!==401) throw e }
  return false
}

const applyBootstrapPayload = async (payload) => {
  if (!payload?.accessToken||!payload?.refreshToken||!payload?.user) { blockedMessage.value='Session manquante.'; isBlocked.value=true; isBootstrapping.value=false; return }
  currentUser.value = payload.user
  try {
    await assistantAuthService.bootstrap(payload)
    const s = await assistantAuthService.getSession()
    currentUser.value=s.user||payload.user; isBlocked.value=false; isBootstrapping.value=false
    if (userId.value) convPanelRef.value?.refresh()
    if (!messages.value.length) { pushMsg({isUser:false,type:'text',text:`Bonjour ! Je suis votre assistant MiniGED. Comment puis-je vous aider ?`}); await scrollToBottom() }
  } catch (e) { blockedMessage.value=e.response?.data?.message||"Impossible de se connecter."; isBlocked.value=true; isBootstrapping.value=false }
}

const handleBootstrapMessage = async (e) => { if (!isAllowedParentOrigin(e.origin)||e.data?.type!==ASSISTANT_MESSAGE_TYPES.BOOTSTRAP) return; await applyBootstrapPayload(e.data.payload) }
const handleLogout = async () => { try{await assistantAuthService.logout()}catch{} currentUser.value=null; messages.value=[]; activeConvId.value=''; isBlocked.value=true; isBootstrapping.value=false; blockedMessage.value="Déconnecté." }

onMounted(async () => {
  window.addEventListener('message', handleBootstrapMessage)
  try {
    const ok = await syncSession()
    if (!ok) { blockedMessage.value="Ouvrez l'assistant depuis MiniGED."; isBlocked.value=true; announceAssistantReady(); setTimeout(()=>{ if (!currentUser.value) isBootstrapping.value=false },1500) }
  } catch { blockedMessage.value='Impossible de vérifier la session.'; isBlocked.value=true; isBootstrapping.value=false }
  finally { await scrollToBottom() }
})
onUnmounted(() => window.removeEventListener('message', handleBootstrapMessage))
</script>

<style scoped>
.chat-shell{display:flex;flex-direction:column;height:100dvh;background:#f8f7ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;position:relative}
.chat-main{display:flex;flex-direction:column;flex:1;overflow:hidden}
.chat-header{display:flex;align-items:center;justify-content:space-between;padding:.875rem 1.25rem;background:white;border-bottom:1px solid #e5e7eb;box-shadow:0 1px 3px rgba(0,0,0,.06);flex-shrink:0;z-index:10}
.header-left,.header-right{display:flex;align-items:center;gap:.6rem}
.assistant-avatar{width:36px;height:36px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:10px;display:flex;align-items:center;justify-content:center;color:white;font-size:16px}
.header-title{font-size:15px;font-weight:600;color:#111;display:block}
.header-status{font-size:12px;color:#6b7280;display:flex;align-items:center;gap:4px}
.status-dot{width:7px;height:7px;border-radius:50%}.status-on{background:#22c55e}.status-off{background:#9ca3af}
.icon-btn{width:34px;height:34px;border:none;border-radius:8px;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#6b7280;font-size:15px;transition:background .15s}
.icon-btn:hover{background:#f3f4f6}.icon-btn--active{background:#f5f3ff;color:#6366f1}.icon-btn.danger:hover{background:#fef2f2;color:#ef4444}
.new-conv-btn{display:flex;align-items:center;gap:.35rem;padding:6px 12px;border-radius:8px;border:1px solid #e0e7ff;background:#f5f3ff;color:#4f46e5;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s}
.new-conv-btn:hover{background:#ede9fe;border-color:#a5b4fc}
@media(max-width:480px){.new-conv-label{display:none}}
.user-chip{font-size:13px;color:#374151;background:#f3f4f6;border-radius:20px;padding:4px 12px;display:flex;align-items:center;gap:6px}
.chat-messages{flex:1;overflow-y:auto;padding:1.5rem 1rem;scroll-behavior:smooth}
.messages-list{display:flex;flex-direction:column;gap:1rem}
.centered-card{display:flex;align-items:center;justify-content:center;min-height:60vh}
.blocked-card,.welcome-card{text-align:center;max-width:420px;padding:2rem;background:white;border-radius:20px;border:1px solid #e5e7eb;box-shadow:0 4px 24px rgba(0,0,0,.06)}
.blocked-icon,.welcome-icon{width:56px;height:56px;border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 1rem}
.blocked-icon{background:#fef3c7;color:#d97706}.welcome-icon{background:linear-gradient(135deg,#ede9fe,#ddd6fe);color:#6366f1}
.blocked-card h3,.welcome-card h2{font-size:18px;font-weight:600;color:#111;margin-bottom:.5rem}
.blocked-card p,.welcome-card p{font-size:14px;color:#6b7280}
.quick-actions{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin-top:1.25rem}
.quick-btn{font-size:13px;padding:6px 14px;border:1px solid #e0e7ff;border-radius:20px;background:#f5f3ff;color:#4f46e5;cursor:pointer;transition:all .15s}
.quick-btn:hover{background:#ede9fe}
.typing-row{display:flex;align-items:flex-end;gap:.5rem}
.assistant-dot{width:28px;height:28px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:8px;color:white;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0}
.typing-bubble{background:white;border:1px solid #e5e7eb;border-radius:16px 16px 16px 4px;padding:12px 16px;display:flex;gap:4px;align-items:center}
.typing-bubble span{width:7px;height:7px;background:#9ca3af;border-radius:50%;animation:bounce 1.2s infinite}
.typing-bubble span:nth-child(2){animation-delay:.2s}.typing-bubble span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}
.chat-footer{border-top:1px solid #e5e7eb;padding:.75rem 1rem .5rem;background:white;flex-shrink:0}
.footer-hint{font-size:11px;color:#9ca3af;text-align:center;margin-top:.4rem;display:flex;align-items:center;justify-content:center;gap:4px}
</style>