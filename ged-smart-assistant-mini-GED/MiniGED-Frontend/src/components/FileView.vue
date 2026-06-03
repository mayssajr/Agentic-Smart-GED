<template>
  <main class="container border-gray-200 border-2 rounded-lg p-4">
    <div class="tool-bar">
      <img src="../assets/images/Logo1.png" class="w-8 h-8" alt="" />
      <span class="page-info">
        <span id="page-num"></span> <span id="page-count"></span>
      </span>
      <div class="middle-bar">
        <div class="text-blue-950 font-semibold rounded-md px-2 py-1 text-sm">
          {{ Math.round(scale * 100) }}%
        </div>
        <button
          @click="scale = scale < 2 ? scale + 0.25 : scale"
          class="btn btn-link text-primary px-2 mb-0 mx-2"
        >
          <i class="fas fa-magnifying-glass-plus size-6"></i>
        </button>
        <button
          @click="scale = scale > 0.25 ? scale - 0.25 : scale"
          class="btn btn-link text-primary px-2 mb-0 mx-2"
        >
          <i class="fas fa-magnifying-glass-minus size-6"></i>
        </button>
        <button
          @click="scale = 1.88"
          class="btn btn-link text-primary px-2 mb-0 mx-2"
        >
          <i class="fas fa-expand size-6"></i>
        </button>
        <button
          @click="scale = 1"
          class="btn btn-link text-primary px-2 mb-0 mx-2"
        >
          <i class="fas fa-compress size-6"></i>
        </button>
      </div>

      <div>
        <button
          @click="downloadDocument"
          class="btn flex btn-link text-secondary px-1 mb-0 mx-2"
        >
          <i class="fas fa-download size-6"></i>
          Télécharger
        </button>
      </div>
    </div>
    <div class="file-container" id="file-container">
      <div v-if="selected == null">
        <h1>Aucun PDF disponible</h1>
      </div>
      <!-- <div v-else v-for="(page,index) in pages" :key="index"> -->
      <div
        v-for="(page, index) in pages"
        :id="`page-${index}`"
        :key="index + 1"
      >
        <PageViewComponent
          :page="page"
          :scale="scale"
          :pdf="pdf"
          :src="src"
          :fit-parent="fitParent"
          @refresh-annotation="refresh"
          @page-loaded="onPageRendered"
          :highlight-text="highlightText"
        />
        <div class="text-gray-500 text-xs font-medium mt-2 mb-1 text-center">
          page {{ index + 1 }} sur {{ pages }}
        </div>
      </div>
    </div>

    <!-- share a document modal -->
    <!-- <div class="modal fade dark" id="exampleModalMessage" tabindex="-1" role="dialog"
      aria-labelledby="exampleModalMessageTitle" aria-hidden="true" data-bs-backdrop="false">
      <div class="modal-dialog modal-dialog-centered" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="exampleModalLabel">
              Share This Document
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close">
              <span aria-hidden="true">×</span>
            </button>
          </div>
          <div class="modal-body">
            <form>
              <div class="form-group">
                <label for="recipient-name" class="col-form-label">Share With</label>
                <input type="text" class="form-control" placeholder="Write a valid Username" id="recipient-name"
                  v-model="username" />
              </div>
              <div class="form-group">
                <label for="message-text" class="col-form-label">Message:</label>
                <textarea class="form-control" id="message-text"></textarea>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn bg-gradient-secondary" data-bs-dismiss="modal">
              Close
            </button>
            <button @click="sharedocument" type="button" class="btn bg-gradient-primary">
              Share
            </button>
          </div>
        </div>
      </div>
    </div> -->
  </main>
</template>

<script setup>
import PageViewComponent from "./PageViewComponent.vue";

import { ref, computed, onMounted } from "vue";
import { usePDF } from "@tato30/vue-pdf";
import { DOCUMENT_PDF_URL } from "../config/api";
const src = ref(DOCUMENT_PDF_URL(8016));
// const showModal = ref(false);
const props = defineProps({
  selected: Number,
  pageNumber: Number,
  highlightText: String,
});
const { pdf, pages } = usePDF(src);
import { watch } from "vue";
onMounted(async () => {
  if (props.selected) {
    src.value = DOCUMENT_PDF_URL(props.selected);
  } else {
  }
});

watch(
  () => props.selected,
  (newValue) => {
    src.value = DOCUMENT_PDF_URL(newValue);
  },
);
const refresh = () => {
  // force a component rerender
  src.value = DOCUMENT_PDF_URL(props.selected);
};

const scrollToPage = (pageNumber) => {
  const pageNumber1 = pageNumber - 1;
  const container = document.getElementById("file-container");
  const el = document.getElementById(`page-${pageNumber1}`);
  if (container && el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

function onPageRendered(page) {
  if (props.pageNumber && page === props.pageNumber) {
    scrollToPage(page);
  } else {
  }
}

const scale = ref(1);
const fitParent = ref(false);
const pageNumber = ref(props.pageNumber || 1);
// const SignatureToolbar = ref(false);
//   const showShareModal = (index) => {
//     showModal.value = true;

//   };
// const sharedocument = async () => {
//   try {
//     const ShareRequest = {
//       username: username.value,
//       documentId: documentId.value,
//     };

//     const response =
//       await BaseApiService(`Document/Share`).create(ShareRequest);

//     router.push("/shared-documents");
//   } catch (e) {
//     console.error(e);
//   }
// };
// const showSignatureToolbar = () => {
//   SignatureToolbar.value = !SignatureToolbar.value;
// }; -->
const emit = defineEmits(["close-button"]);

const closeTab = () => {
  emit("close-button");
};
const downloadDocument = async () => {
  try {
    const response = await BaseApiService("Document/Download").get(
      documentId.value,
      {
        responseType: "blob",
      },
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "document.pdf");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Error downloading document:", error);
  }
};
</script>

<style scoped>
.container {
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 70vh;
  margin: 0;
  padding: 0;
  background-color: #f8f9fa;
  overflow: hidden;
}

.tool-bar {
  background: #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  color: #495057;
  padding: 0.75rem 1.5rem;
  width: 100%;
  height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e9ecef;
}

.middle-bar {
  display: flex;
  justify-content: center;
  align-items: center;

  border-radius: 8px;
  padding: 0.25rem;
}

.btn {
  transition: all 0.2s ease;
}

.btn:hover {
  background-color: #f1f3f5;
  padding: 0.5rem 1rem;
  opacity: 0.85;
  transform: translateY(-1px);
}

.btn:active {
  transform: translateY(0);
}

.page-info {
  font-weight: 500;
  color: #495057;
  font-size: 0.9rem;
}

.file-container {
  background: #e9ecef;
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  overflow: auto;
  height: calc(100vh - 64px);
  padding: 1.5rem 0;
}

.file-container::-webkit-scrollbar {
  width: 8px;
  background-color: #f8f9fa;
}

.file-container::-webkit-scrollbar-thumb {
  background-color: #adb5bd;
  border-radius: 4px;
}

.file-container::-webkit-scrollbar-thumb:hover {
  background-color: #6c757d;
}

.file-container > div {
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  background-color: #fff;
}

.text-primary {
  color: #0d6efd !important;
}

.text-secondary {
  color: #6c757d !important;
}

/* Empty state styling */
.file-container h1 {
  color: #6c757d;
  font-weight: 400;
  font-size: 1.5rem;
  margin-top: 2rem;
}
</style>
