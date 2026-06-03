<template>
  <div v-if="visible" class="modal-overlay">
    <div
      class="w-full max-w-lg bg-white rounded-2xl p-8 shadow-2xl z-50 text-gray-900"
    >
      <h2 class="text-2xl font-bold mb-6 text-center">
        {{ document ? "Modifier le" : "Ajouter un nouveau" }} document
      </h2>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div>
          <label for="title" class="block text-sm font-medium mb-1"
            >Titre</label
          >
          <input
            class="border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-lg p-3 w-full transition"
            id="title"
            v-model="title"
            required
            autocomplete="off"
            placeholder="Entrez le titre du document"
          />
        </div>
        <div>
          <label for="description" class="block text-sm font-medium mb-1"
            >Description</label
          >
          <textarea
            class="border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-lg p-3 w-full transition resize-none"
            id="description"
            v-model="description"
            required
            rows="4"
            placeholder="Entrez la description du document"
          ></textarea>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button
            class="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold rounded-lg px-6 py-3 transition"
            type="button"
            @click="closeModal"
          >
            Annuler
          </button>
          <button
            class="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-400 hover:to-purple-400 text-white font-semibold rounded-lg px-6 py-3 transition disabled:opacity-60 disabled:cursor-not-allowed"
            type="submit"
            :disabled="loading"
          >
            <span
              v-if="loading"
              class="animate-spin mr-2 inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"
            ></span>
            Ajouter
          </button>
        </div>
        <div v-if="error" class="text-red-600 text-sm mt-2 text-center">
          {{ error }}
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { createDocument, updateDocument } from "../services/documentService";
const props = defineProps({
  visible: Boolean,
  document: Object,
});
const emits = defineEmits(["close", "added", "updated"]);

const title = ref("");
const description = ref("");
const loading = ref(false);
const error = ref("");

// Watch for document prop changes to populate form
watch(
  () => props.document,
  (newDocument) => {
    if (newDocument) {
      title.value = newDocument.title || "";
      description.value = newDocument.description || "";
    } else {
      title.value = "";
      description.value = "";
    }
  },
  { immediate: true },
);

function closeModal() {
  title.value = "";
  description.value = "";
  error.value = "";
  emits("close");
}

async function handleSubmit() {
  loading.value = true;
  error.value = "";
  try {
    const documentData = {
      Title: title.value,
      Description: description.value,
    };

    if (props.document) {
      // Update existing document
      await updateDocument(props.document.id, documentData);
      emits("updated", documentData);
    } else {
      // Create new document
      await createDocument(documentData);
      emits("added");
    }
    closeModal();
  } catch (e) {
    error.value = e?.message || "Failed to save document.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
</style>
