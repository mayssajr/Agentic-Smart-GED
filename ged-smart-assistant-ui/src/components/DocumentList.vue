<template>
  <Card class="max-w-sm">
    <template #header>
      <div class="flex items-center gap-2 px-4 pt-3">
        <i class="pi pi-folder text-purple-500"></i>
        <h3 class="font-semibold text-gray-900">{{ message.text }}</h3>
      </div>
    </template>
    <template #content>
      <DataView :value="message.documents" :paginator="false" class="w-full">
        <template #list="slotProps">
          <div class="space-y-2">
            <div 
              v-for="(doc, index) in slotProps.items" 
              :key="index"
              class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors border border-gray-100"
            >
              <div class="flex items-center gap-3">
                <i 
                  :class="resolveIcon(doc)"
                  class="text-lg"
                ></i>
                <div class="flex flex-col">
                  <span class="text-sm font-medium text-gray-700">{{ doc.name }}</span>
                  <span v-if="doc.subtitle" class="text-xs text-gray-500">{{ doc.subtitle }}</span>
                  <Tag 
                    :value="(doc.type || 'result').toUpperCase()" 
                    :severity="resolveSeverity(doc)"
                    class="text-xs"
                  />
                </div>
              </div>
              <Button 
                icon="pi pi-chevron-right" 
                severity="secondary" 
                text 
                size="small"
                class="p-1"
              />
            </div>
          </div>
        </template>
      </DataView>
    </template>
  </Card>
</template>

<script setup>
import { defineProps } from 'vue'
import Card from 'primevue/card'
import DataView from 'primevue/dataview'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const resolveIcon = (doc) => {
  if (doc.type === 'pdf') return 'pi pi-file-pdf text-red-500'
  if (doc.type === 'excel') return 'pi pi-file-excel text-green-500'
  if (doc.type === 'document') return 'pi pi-file text-blue-500'
  return 'pi pi-file text-slate-500'
}

const resolveSeverity = (doc) => {
  if (doc.type === 'pdf') return 'danger'
  if (doc.type === 'excel') return 'success'
  return 'info'
}
</script>
