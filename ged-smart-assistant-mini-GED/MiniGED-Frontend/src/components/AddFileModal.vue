<template>
  <!-- Modal Overlay -->
  <div class="modal-overlay">
    <!-- Modal Container -->
    <div
      class="bg-white rounded-xl border border-slate-200 shadow-2xl max-w-lg w-full px-8 py-6 relative z-50"
    >
      <!-- Close Button -->
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-base font-bold text-slate-900">
          Ajouter un ou plusieurs fichiers
        </h2>
        <button
          class="w-9 h-9 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          @click="handleCancel"
          aria-label="Close"
        >
          <i class="fas fa-xmark"></i>
        </button>
      </div>
      <!-- Modal Content -->
      <!-- Upload Complete Files -->
      <div v-for="file in FilesUploaded" :key="file.name" class="mt-4">
        <div
          class="flex justify-between items-center p-4 bg-slate-50 rounded-lg border border-slate-200 hover:border-blue-200 hover:bg-white transition-colors"
        >
          <div class="flex items-center gap-3">
            <div class="flex-shrink-0 p-2.5 bg-blue-50 rounded-lg">
              <i class="fas fa-file-lines text-blue-600"></i>
            </div>
            <div>
              <div class="font-semibold text-slate-800 text-sm">
                {{ file.name }}
              </div>
              <div class="text-xs text-slate-500 mt-0.5">
                {{ (file.size / 1024).toFixed(2) }} KB ·
                {{ file.type || "Unknown type" }}
              </div>
            </div>
          </div>
          <button
            class="p-2 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
            @click="FilesUploaded.splice(FilesUploaded.indexOf(file), 1)"
            aria-label="Remove file"
          >
            <i class="fas fa-trash-can"></i>
          </button>
        </div>
      </div>
      <!-- Upload Progress -->
      <div
        v-if="fileUploadProgress > 0 && fileUploadProgress < 100"
        class="mt-5"
      >
        <div class="text-sm font-medium text-slate-600">
          Téléchargement du fichier en cours... {{ fileUploadProgress }}%
        </div>
        <div class="w-full bg-slate-200 rounded-full h-2 mt-2">
          <div
            class="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-in-out"
            :style="{ width: fileUploadProgress + '%' }"
          ></div>
        </div>
      </div>
      <!-- Drop Zone -->
      <div
        class="mt-5 cursor-pointer p-12 flex justify-center bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl hover:border-blue-400 hover:bg-blue-50/40 transition-colors"
        @click="triggerFileSelect"
      >
        <input
          type="file"
          ref="fileInput"
          class="hidden"
          accept=".pdf,.doc,.docx,.txt"
          @change="handleFileUpload"
        />
        <div class="text-center">
          <i
            class="fas fa-cloud-arrow-up text-5xl text-blue-500"
          ></i>
          <div class="mt-4 flex flex-wrap justify-center text-sm text-slate-600">
            <span
              class="pe-1 font-medium text-slate-800"
              v-if="FilesUploaded.length === 0"
            >
              Déposez votre fichier ici ou
            </span>
            <span class="pe-1 font-medium text-slate-800" v-else>
              Déposez un autre fichier ici ou
            </span>
            <span
              class="bg-white px-2 font-semibold text-blue-600 hover:text-blue-700 rounded-lg decoration-2 hover:underline cursor-pointer"
            >
              Parcourir
            </span>
          </div>
          <p class="mt-2 text-xs text-slate-400">
            Choisissez un fichier de 2 Mo maximum.
          </p>
        </div>
      </div>
      <!-- Save & Cancel Buttons -->
      <div v-if="FilesUploaded.length > 0" class="flex justify-end gap-2 mt-8">
        <button
          class="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 font-semibold text-sm transition"
          @click="handleCancel"
        >
          Annuler
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-semibold text-sm transition disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="FilesUploaded.length === 0 || isSaving"
          @click="handleSave"
        >
          <span v-if="isSaving">Enregistrement...</span>
          <span v-else>Enregistrer</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps } from "vue";
import BaseApiService from "../services/ApiService";
const emit = defineEmits();
const props = defineProps(["documentId"]);
const FilesUploaded = ref([]);
const file = ref(null);
const fileUploadProgress = ref(0);
const fileInput = ref(null);
const isSaving = ref(false);

function triggerFileSelect() {
  fileInput.value.click();
}

function handleFileUpload(event) {
  const selectedFile = event.target.files[0];
  fileUploadProgress.value = 0;

  if (!selectedFile) return;

  // Validate size (max 2MB)
  if (selectedFile.size > 2 * 1024 * 1024) {
    alert("File size must be under 2MB");
    return;
  }

  // Validate type
  const allowedTypes = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
  ];
  if (!allowedTypes.includes(selectedFile.type)) {
    alert("Invalid file type");
    return;
  }

  file.value = selectedFile;

  // Simulate upload progress
  const interval = setInterval(() => {
    if (fileUploadProgress.value < 100) {
      fileUploadProgress.value += 10;
    } else {
      clearInterval(interval);

      // Add file to uploaded files array
      FilesUploaded.value.push(file.value);

      // Reset progress after a short delay
      setTimeout(() => {
        fileUploadProgress.value = 0;
      }, 2000);
    }
  }, 100);
}

function handleCancel() {
  FilesUploaded.value = [];
  file.value = null;
  fileUploadProgress.value = 0;
  // Optionally emit an event to close the modal from parent
  emit("close");
}
async function handleSave() {
  if (!FilesUploaded.value?.length) {
    alert("Please select at least one file");
    return;
  }

  isSaving.value = true;

  try {
    const formData = new FormData();

    // Append document ID
    formData.append("DocumentId", props.documentId);

    // Append all files to the Files array parameter
    FilesUploaded.value.forEach((file) => {
      formData.append("Files", file);
    });

    const response = await BaseApiService("document/upload").create(formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        fileUploadProgress.value = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total,
        );
      },
    });

    if (response.data.success) {
      emit("added");
      emit("close");
    } else {
      alert(response.message || "Erreur lors du téléchargement des fichiers");
      response.data;
    }
  } catch (error) {
    console.error("Upload error:", error);
    alert(
      error.response?.data?.message ||
        "Le téléchargement a échoué. Veuillez réessayer.",
    );
  } finally {
    isSaving.value = false;
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
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
</style>
