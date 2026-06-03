<template>
  <div class="input-wrapper" :class="{ 'input-disabled': disabled }">
    <textarea
      ref="textarea"
      v-model="input"
      :disabled="disabled"
      placeholder="Posez votre question…"
      class="chat-textarea"
      rows="1"
      @keydown.enter.exact.prevent="emitSend"
      @keydown.enter.shift.exact="newline"
      @input="autoResize"
    />
    <button
      class="mic-btn"
      :class="{ 'mic-btn--active': isRecording }"
      type="button"
      @click="toggleRecording"
      :title="isRecording ? 'Arrêter' : 'Dicter'"
    >
      <i :class="isRecording ? 'pi pi-stop-circle' : 'pi pi-microphone'"></i>
    </button>
    <div class="input-actions">
      <span class="input-hint">↵ Envoyer · ⇧↵ Saut de ligne</span>
      <button
        class="send-btn"
        :disabled="disabled || !input.trim()"
        @click="emitSend"
      >
        <i class="pi pi-send"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

defineProps({ disabled: { type: Boolean, default: false } })
const emit = defineEmits(['send', 'voice-input'])

const input        = ref('')
const textarea     = ref(null)
const isRecording  = ref(false)
const mediaRecorder = ref(null)
const audioChunks  = ref([])

const PYTHON_API = import.meta.env.VITE_PYTHON_API_URL || 'http://localhost:8000'

const toggleRecording = async () => {
  if (isRecording.value) {
    mediaRecorder.value?.stop()
    isRecording.value = false
    return
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks.value = []
    const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })

    mr.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.value.push(e.data)
    }

    mr.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(audioChunks.value, { type: 'audio/webm' })
      const formData = new FormData()
      formData.append('file', blob, 'voice.webm')
      try {
        const res  = await fetch(`${PYTHON_API}/transcribe`, { method: 'POST', body: formData })
        const data = await res.json()
        if (data.text) {
          input.value += (input.value ? ' ' : '') + data.text
          await nextTick()
          autoResize()
          // Signaler que c'était une saisie vocale (active le TTS dans ChatPage)
          emit('voice-input')
        }
      } catch (e) {
        console.error('Transcription failed', e)
      }
    }

    mediaRecorder.value = mr
    mr.start()
    isRecording.value = true
  } catch (e) {
    alert('Microphone non accessible')
  }
}

const autoResize = () => {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 140) + 'px'
}

const emitSend = () => {
  if (!input.value.trim()) return
  emit('send', input.value.trim())
  input.value = ''
  nextTick(() => {
    if (textarea.value) textarea.value.style.height = 'auto'
  })
}

const newline = () => {
  input.value += '\n'
  nextTick(autoResize)
}
</script>

<style scoped>
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: .5rem;
  background: white;
  border: 1.5px solid #e5e7eb;
  border-radius: 14px;
  padding: .6rem .75rem .6rem 1rem;
  transition: border-color .15s, box-shadow .15s;
}
.input-wrapper:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,.1);
}
.input-disabled { opacity: .55; pointer-events: none; }

.chat-textarea {
  flex: 1;
  border: none; outline: none; resize: none;
  font-size: 14px; line-height: 1.6;
  color: #111; background: transparent;
  font-family: inherit;
  max-height: 140px;
}
.chat-textarea::placeholder { color: #9ca3af; }

.input-actions {
  display: flex; align-items: center; gap: .5rem; flex-shrink: 0;
}
.input-hint {
  font-size: 11px; color: #d1d5db;
  display: none;
}
@media (min-width: 640px) { .input-hint { display: inline; } }

.send-btn {
  width: 36px; height: 36px;
  background: linear-gradient(135deg,#6366f1,#7c3aed);
  border: none; border-radius: 10px;
  color: white; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  transition: opacity .15s, transform .1s;
}
.send-btn:hover:not(:disabled) { opacity: .9; transform: scale(1.05); }
.send-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; }

.mic-btn {
  width: 36px; height: 36px;
  border: 1.5px solid #e5e7eb; border-radius: 10px;
  background: transparent; color: #9ca3af;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  font-size: 15px; transition: all .15s; flex-shrink: 0;
}
.mic-btn:hover { background: #f3f4f6; color: #6366f1; border-color: #a5b4fc; }
.mic-btn--active { background: #fef2f2; color: #ef4444; border-color: #fecaca; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:.6 } }
</style>