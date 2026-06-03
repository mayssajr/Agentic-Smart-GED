<template>
  <Transition name="qc-panel">
    <div v-if="commands.length > 0 && !hidden" class="qc-panel">

      <div class="qc-head">
        <div class="qc-head-left">
          <div class="qc-icon-wrap">
            <i class="pi pi-bolt"></i>
          </div>
          <span class="qc-title">Actions rapides</span>
          <span v-if="docTypeLabel" class="qc-ctx-badge">{{ docTypeLabel }}</span>
        </div>
        <div class="qc-head-right">
          <button class="qc-toggle" @click="collapsed = !collapsed">
            <i :class="collapsed ? 'pi pi-chevron-down' : 'pi pi-chevron-up'"></i>
          </button>
          <button class="qc-close" @click="hidden = true" title="Masquer">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>

      <Transition name="qc-chips">
        <div v-if="!collapsed" class="qc-chips-wrap">
          <TransitionGroup name="chip-stagger" tag="div" class="qc-chips">
            <button
              v-for="(cmd, i) in commands"
              :key="cmd.action"
              class="qc-chip"
              :style="{ '--i': i }"
              :disabled="disabled"
              @click="$emit('send', cmd.action)">
              <span class="chip-icon-wrap">
                <i :class="cmd.icon || 'pi pi-comment'"></i>
              </span>
              <span class="chip-label">{{ cmd.label }}</span>
            </button>
          </TransitionGroup>

          <!-- Suggestion cross-doc si contexte RH -->
          <div v-if="showCrossDoc" class="cross-doc-strip">
            <div class="cross-doc-strip-left">
              <i class="pi pi-users"></i>
              <span>Comparer tous les candidats</span>
            </div>
            <button class="cross-doc-cta" @click="$emit('send', crossDocQuery)">
              Analyse globale →
            </button>
          </div>
        </div>
      </Transition>

    </div>
  </Transition>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  commands:     { type: Array,   default: () => [] },
  documentType: { type: String,  default: '' },
  disabled:     { type: Boolean, default: false },
})
defineEmits(['send'])

const collapsed = ref(false)
const hidden    = ref(false)

const RH_TYPES = ['CV', 'Lettre de motivation', 'Candidature', 'Dossier RH', 'Dossier RH complet']
const showCrossDoc  = computed(() => RH_TYPES.includes(props.documentType))
const crossDocQuery = 'Quel est le meilleur candidat parmi tous les dossiers analysés ?'

const DOC_LABELS = {
  'CV': 'CV', 'Lettre de motivation': 'Motivation', 'Offre d\'emploi': 'Offre',
  'Contrat de travail': 'Contrat', 'Juridique': 'Juridique', 'Technique': 'Technique',
}
const docTypeLabel = computed(() => DOC_LABELS[props.documentType] || '')

// Reset hidden quand les commandes changent
import { watch } from 'vue'
watch(() => props.commands, () => { hidden.value = false }, { deep: true })
</script>

<style scoped>
.qc-panel {
  background: white;
  border: 1px solid #e4e4f0;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,.05);
}

.qc-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: .55rem .75rem;
  background: linear-gradient(90deg, #f5f3ff 0%, #fafbff 100%);
  border-bottom: 1px solid #e8e8f5;
}
.qc-head-left { display: flex; align-items: center; gap: .4rem; }

.qc-icon-wrap {
  width: 22px; height: 22px; border-radius: 6px;
  background: #eef0ff; color: #5b5bd6;
  display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0;
}

.qc-title { font-size: 11.5px; font-weight: 700; color: #0d0d0d; }

.qc-ctx-badge {
  font-size: 10px; font-weight: 600; color: #5b5bd6;
  background: #eef0ff; border-radius: 10px; padding: 1px 7px;
  text-transform: uppercase; letter-spacing: .04em;
}

.qc-head-right { display: flex; align-items: center; gap: .25rem; }
.qc-toggle, .qc-close {
  width: 22px; height: 22px; border: none; background: transparent;
  color: #9ca3af; cursor: pointer; border-radius: 6px; font-size: 10px;
  display: flex; align-items: center; justify-content: center; transition: all .15s;
}
.qc-toggle:hover, .qc-close:hover { background: #eef0ff; color: #5b5bd6; }

/* Chips */
.qc-chips-wrap { padding: .6rem .65rem; display: flex; flex-direction: column; gap: .4rem; }
.qc-chips { display: flex; flex-wrap: wrap; gap: .35rem; }

.qc-chip {
  display: inline-flex; align-items: center; gap: .35rem;
  padding: 5px 11px 5px 8px;
  background: #f9f9fc; border: 1px solid #e4e4f0;
  border-radius: 20px; cursor: pointer; transition: all .15s;
  font-size: 12px; color: #374151; font-family: inherit;
  animation: chipIn .25s cubic-bezier(.34,1.56,.64,1) calc(var(--i, 0) * 0.04s) both;
}
.qc-chip:hover:not(:disabled) {
  background: #eef0ff; border-color: #a5b4fc; color: #5b5bd6;
  transform: translateY(-2px); box-shadow: 0 3px 10px rgba(91,91,214,.15);
}
.qc-chip:active:not(:disabled) { transform: translateY(0); }
.qc-chip:disabled { opacity: .4; cursor: not-allowed; }

.chip-icon-wrap {
  width: 18px; height: 18px; border-radius: 5px;
  background: #eef0ff; color: #5b5bd6;
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; flex-shrink: 0; transition: background .15s;
}
.qc-chip:hover .chip-icon-wrap { background: #5b5bd6; color: white; }
.chip-label { font-weight: 500; line-height: 1; }

@keyframes chipIn {
  from { transform: scale(.7) translateY(4px); opacity: 0; }
  to   { transform: scale(1) translateY(0); opacity: 1; }
}

/* Cross-doc strip */
.cross-doc-strip {
  display: flex; align-items: center; justify-content: space-between;
  padding: .45rem .6rem;
  background: linear-gradient(90deg, #f0fdf4, #fafffe);
  border: 1px solid #bbf7d0; border-radius: 10px;
  font-size: 11.5px; gap: .5rem;
}
.cross-doc-strip-left {
  display: flex; align-items: center; gap: .35rem; color: #15803d; font-weight: 500;
}
.cross-doc-strip-left .pi { font-size: 11px; }
.cross-doc-cta {
  background: #16a34a; color: white; border: none; border-radius: 8px;
  padding: 4px 10px; font-size: 11px; font-weight: 600; cursor: pointer;
  transition: opacity .15s; flex-shrink: 0; font-family: inherit;
}
.cross-doc-cta:hover { opacity: .88; }

/* Transitions panel */
.qc-panel-enter-active, .qc-panel-leave-active { transition: all .25s cubic-bezier(.4,0,.2,1); }
.qc-panel-enter-from, .qc-panel-leave-to { opacity: 0; transform: translateY(8px); }

.qc-chips-enter-active, .qc-chips-leave-active { transition: all .2s ease; }
.qc-chips-enter-from, .qc-chips-leave-to { opacity: 0; max-height: 0; }

.chip-stagger-enter-active { transition: all .2s cubic-bezier(.34,1.56,.64,1); }
.chip-stagger-enter-from   { transform: scale(.8); opacity: 0; }
</style>
