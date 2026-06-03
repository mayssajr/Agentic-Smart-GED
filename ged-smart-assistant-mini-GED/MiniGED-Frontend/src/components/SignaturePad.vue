<template>
  <div class="sig-pad-overlay" @click.self="$emit('close')">
    <div class="sig-pad-modal">

      <!-- En-tête -->
      <div class="sig-pad-header">
        <div class="sig-pad-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
          Dessinez votre signature
        </div>
        <button class="sig-close-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- Indicateur de progression apprentissage -->
      <div class="sig-learning-bar">
        <div class="sig-learning-info">
          <span class="sig-learning-label">
            <span v-if="profile.auto_enabled" class="sig-auto-badge sig-auto-badge--on">
              ⚡ Mode automatique activé
            </span>
            <span v-else class="sig-auto-badge sig-auto-badge--off">
              🔒 Mode manuel
              — encore {{ Math.max(0, 2 - (profile.confirmations || 0)) }}
              confirmation(s) pour le mode automatique
            </span>
          </span>
        </div>
        <div class="sig-progress-track">
          <div
            class="sig-progress-fill"
            :class="{ 'sig-progress-fill--done': profile.auto_enabled }"
            :style="{ width: progressPct + '%' }"
          />
        </div>
        <div class="sig-progress-labels">
          <span>0</span>
          <span>{{ profile.confirmations || 0 }} / 2</span>
        </div>
      </div>

      <!-- Zone de dessin -->
      <div class="sig-canvas-wrap">
        <canvas
          ref="canvasRef"
          class="sig-canvas"
          width="560"
          height="180"
          @mousedown="startDraw"
          @mousemove="draw"
          @mouseup="stopDraw"
          @mouseleave="stopDraw"
          @touchstart.prevent="startDrawTouch"
          @touchmove.prevent="drawTouch"
          @touchend="stopDraw"
        />
        <div v-if="isEmpty" class="sig-placeholder">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5">
            <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
          <span>Signez ici avec votre souris ou votre doigt</span>
        </div>
      </div>

      <!-- Nom du signataire -->
      <div class="sig-name-row">
        <label class="sig-name-label">Nom du signataire</label>
        <input
          v-model="signerName"
          class="sig-name-input"
          placeholder="Votre nom complet"
          maxlength="80"
        />
      </div>

      <!-- Actions -->
      <div class="sig-actions">
        <button class="sig-btn sig-btn--clear" @click="clearCanvas" :disabled="isEmpty">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/>
          </svg>
          Effacer
        </button>
        <button
          class="sig-btn sig-btn--confirm"
          :disabled="isEmpty || !signerName.trim() || loading"
          @click="confirm"
        >
          <svg v-if="!loading" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <svg v-else class="sig-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg>
          {{ loading ? 'Signature en cours…' : 'Confirmer la signature' }}
        </button>
      </div>

      <!-- Message erreur -->
      <div v-if="errorMsg" class="sig-error">{{ errorMsg }}</div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

const props = defineProps({
  pdfBase64:    { type: String,  default: '' },
  filename:     { type: String,  default: '' },
  documentType: { type: String,  default: '' },
  profile:      { type: Object,  default: () => ({}) },
})

const emit = defineEmits(['close', 'signed'])

const PYTHON_API  = import.meta.env.VITE_PYTHON_API_URL || 'http://localhost:8000'

// ── State ─────────────────────────────────────────────────────────────────────
const canvasRef  = ref(null)
const isDrawing  = ref(false)
const isEmpty    = ref(true)
const signerName = ref(props.profile?.signer_name || '')
const loading    = ref(false)
const errorMsg   = ref('')

const progressPct = computed(() => {
  if (props.profile?.auto_enabled) return 100
  return Math.min(100, ((props.profile?.confirmations || 0) / 2) * 100)
})

// ── Canvas helpers ─────────────────────────────────────────────────────────────
const getCtx = () => canvasRef.value?.getContext('2d')

const getPos = (e, canvas) => {
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width  / rect.width
  const scaleY = canvas.height / rect.height
  return {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top)  * scaleY,
  }
}

const startDraw = (e) => {
  const ctx = getCtx(); if (!ctx) return
  const pos = getPos(e, canvasRef.value)
  ctx.beginPath()
  ctx.moveTo(pos.x, pos.y)
  isDrawing.value = true
  isEmpty.value   = false
}

const draw = (e) => {
  if (!isDrawing.value) return
  const ctx = getCtx(); if (!ctx) return
  const pos = getPos(e, canvasRef.value)
  ctx.lineTo(pos.x, pos.y)
  ctx.strokeStyle = '#1e3a5f'
  ctx.lineWidth   = 2.2
  ctx.lineCap     = 'round'
  ctx.lineJoin    = 'round'
  ctx.stroke()
}

const stopDraw = () => { isDrawing.value = false }

const startDrawTouch = (e) => {
  const touch  = e.touches[0]
  startDraw({ clientX: touch.clientX, clientY: touch.clientY })
}
const drawTouch = (e) => {
  const touch = e.touches[0]
  draw({ clientX: touch.clientX, clientY: touch.clientY })
}

const clearCanvas = () => {
  const ctx = getCtx(); if (!ctx) return
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  isEmpty.value = true
  errorMsg.value = ''
}

// ── Init canvas style ──────────────────────────────────────────────────────────
onMounted(() => {
  const ctx = getCtx(); if (!ctx) return
  ctx.strokeStyle = '#1e3a5f'
  ctx.lineWidth   = 2.2
  ctx.lineCap     = 'round'
  ctx.lineJoin    = 'round'
})

// ── Confirm ────────────────────────────────────────────────────────────────────
const confirm = async () => {
  if (isEmpty.value || !signerName.value.trim()) return
  errorMsg.value = ''
  loading.value  = true

  try {
    // Extraire la PNG base64 depuis le canvas
    const signaturePng = canvasRef.value
      .toDataURL('image/png')
      .replace('data:image/png;base64,', '')

    const body = {
      pdf_base64:    props.pdfBase64,
      signature_png: signaturePng,
      signer_name:   signerName.value.trim(),
      filename:      props.filename,
      document_type: props.documentType,
      page:          -1,   // dernière page
    }

    const res  = await fetch(`${PYTHON_API}/sign`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
    const data = await res.json()

    if (!res.ok || data.error) {
      errorMsg.value = data.error || data.detail || 'Erreur lors de la signature.'
      return
    }

    emit('signed', {
      ...data,
      signature_png: signaturePng,
      signer_name:   signerName.value.trim(),
    })

  } catch (e) {
    errorMsg.value = `Erreur réseau : ${e.message}`
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── Overlay ─────────────────────────────────────────────────────────────── */
.sig-pad-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  animation: sig-fade-in .15s ease;
}
@keyframes sig-fade-in { from { opacity:0 } to { opacity:1 } }

.sig-pad-modal {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  width: min(620px, 95vw);
  display: flex; flex-direction: column; gap: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,.18);
  animation: sig-slide-up .2s ease;
}
@keyframes sig-slide-up { from { transform:translateY(16px); opacity:0 } to { transform:translateY(0); opacity:1 } }

/* ── Header ──────────────────────────────────────────────────────────────── */
.sig-pad-header {
  display: flex; align-items: center; justify-content: space-between;
}
.sig-pad-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 16px; font-weight: 600; color: #111;
}
.sig-close-btn {
  background: none; border: none; cursor: pointer;
  font-size: 16px; color: #9ca3af; padding: 4px;
  border-radius: 6px; transition: background .15s;
}
.sig-close-btn:hover { background: #f3f4f6; color: #374151; }

/* ── Barre apprentissage ─────────────────────────────────────────────────── */
.sig-learning-bar {
  background: #f8f9ff;
  border: 1px solid #e0e7ff;
  border-radius: 10px;
  padding: 10px 14px;
  display: flex; flex-direction: column; gap: 6px;
}
.sig-learning-info { display: flex; align-items: center; }
.sig-learning-label { font-size: 12px; color: #4b5563; }
.sig-auto-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 500;
  padding: 3px 8px; border-radius: 20px;
}
.sig-auto-badge--on  { background: #dcfce7; color: #15803d; }
.sig-auto-badge--off { background: #fef3c7; color: #92400e; }

.sig-progress-track {
  height: 6px; background: #e5e7eb; border-radius: 99px; overflow: hidden;
}
.sig-progress-fill {
  height: 100%; background: #6366f1; border-radius: 99px;
  transition: width .4s ease;
}
.sig-progress-fill--done { background: #22c55e; }
.sig-progress-labels {
  display: flex; justify-content: space-between;
  font-size: 10px; color: #9ca3af;
}

/* ── Canvas ──────────────────────────────────────────────────────────────── */
.sig-canvas-wrap {
  position: relative;
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  background: #fafafa;
  overflow: hidden;
  cursor: crosshair;
  transition: border-color .15s;
}
.sig-canvas-wrap:hover { border-color: #6366f1; }

.sig-canvas {
  display: block;
  width: 100%; height: 180px;
  touch-action: none;
}

.sig-placeholder {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 8px; pointer-events: none;
  color: #9ca3af; font-size: 13px;
}

/* ── Nom ─────────────────────────────────────────────────────────────────── */
.sig-name-row {
  display: flex; flex-direction: column; gap: 4px;
}
.sig-name-label {
  font-size: 12px; font-weight: 500; color: #374151;
}
.sig-name-input {
  padding: 8px 12px;
  border: 1px solid #d1d5db; border-radius: 8px;
  font-size: 14px; color: #111;
  transition: border-color .15s;
  outline: none;
}
.sig-name-input:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.1); }

/* ── Actions ─────────────────────────────────────────────────────────────── */
.sig-actions {
  display: flex; gap: 10px; justify-content: flex-end;
}
.sig-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 9px 18px; border-radius: 8px;
  font-size: 14px; font-weight: 500;
  cursor: pointer; border: none; transition: all .15s;
}
.sig-btn:disabled { opacity: .5; cursor: not-allowed; }

.sig-btn--clear {
  background: #f3f4f6; color: #374151;
}
.sig-btn--clear:hover:not(:disabled) { background: #e5e7eb; }

.sig-btn--confirm {
  background: #6366f1; color: #fff;
}
.sig-btn--confirm:hover:not(:disabled) { background: #4f46e5; }

.sig-spin {
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg) } }

/* ── Erreur ──────────────────────────────────────────────────────────────── */
.sig-error {
  background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 8px; padding: 10px 14px;
  font-size: 13px; color: #dc2626;
}
</style>
