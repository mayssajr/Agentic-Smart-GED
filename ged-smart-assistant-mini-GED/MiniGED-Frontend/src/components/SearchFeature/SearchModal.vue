<template>
  <div class="relative">
    <div
      class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-start flex-col p-6 md:p-10 overflow-auto"
      @click.self="closeModal"
    >
      <div class="bg-white z-10 rounded-2xl shadow-xl w-full max-w-4xl p-6 relative">
        <button
          @click="closeModal"
          class="absolute top-4 right-6 text-red-500 hover:text-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          x
        </button>

        <div class="space-y-4">
          <input
            ref="searchInput"
            v-model="query"
            class="w-full border rounded-lg p-3 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            placeholder="Search documents, descriptions, and extracted file text..."
          />

          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            <select
              v-model="selectedDocumentId"
              class="border rounded-lg p-3 bg-white"
            >
              <option value="">All documents</option>
              <option
                v-for="document in documents"
                :key="document.id"
                :value="String(document.id)"
              >
                {{ document.title }}
              </option>
            </select>

            <select
              v-model="selectedFileStatus"
              class="border rounded-lg p-3 bg-white"
            >
              <option value="">All file statuses</option>
              <option
                v-for="option in fileStatusOptions"
                :key="option.value"
                :value="String(option.value)"
              >
                {{ option.label }}
              </option>
            </select>

            <select
              v-model="selectedTaskStatus"
              class="border rounded-lg p-3 bg-white"
            >
              <option value="">All task statuses</option>
              <option
                v-for="option in taskStatusOptions"
                :key="option.value"
                :value="String(option.value)"
              >
                {{ option.label }}
              </option>
            </select>

            <select
              v-model="selectedTaskPriority"
              class="border rounded-lg p-3 bg-white"
            >
              <option value="">All task priorities</option>
              <option
                v-for="option in taskPriorityOptions"
                :key="option.value"
                :value="String(option.value)"
              >
                {{ option.label }}
              </option>
            </select>

            <input
              v-model="uploadedFrom"
              type="date"
              class="border rounded-lg p-3 bg-white"
              placeholder="Uploaded from"
            />

            <input
              v-model="uploadedTo"
              type="date"
              class="border rounded-lg p-3 bg-white"
              placeholder="Uploaded to"
            />

            <input
              v-model="taskDueFrom"
              type="date"
              class="border rounded-lg p-3 bg-white"
              placeholder="Task due from"
            />

            <input
              v-model="taskDueTo"
              type="date"
              class="border rounded-lg p-3 bg-white"
              placeholder="Task due to"
            />

            <select v-model="sort" class="border rounded-lg p-3 bg-white">
              <option value="0">Sort by relevance</option>
              <option value="1">Sort by uploaded date</option>
            </select>

            <button
              class="border rounded-lg p-3 bg-slate-100 hover:bg-slate-200 text-slate-700"
              @click="resetFilters"
            >
              Reset filters
            </button>
          </div>

          <div class="flex items-center justify-between text-sm text-gray-500">
            <span>{{ results.totalCount || 0 }} result(s)</span>
            <span v-if="loading">Searching...</span>
          </div>
        </div>
      </div>

      <div class="w-full max-w-4xl mt-4">
        <p
          v-if="errorMessage"
          class="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700"
        >
          {{ errorMessage }}
        </p>

        <p
          v-else-if="showEmptyState"
          class="p-6 rounded-lg bg-white border border-dashed border-slate-300 text-slate-500 text-center"
        >
          No matching files were found.
        </p>

        <SearchResultItem
          v-for="item in results.items"
          :key="item.fileId"
          :result="item"
          class="p-2 m-2 z-10"
          @click="closeModal"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import SearchResultItem from "./SearchResultItem.vue";
import { getUserDocuments } from "../../services/documentService";
import { searchDocuments } from "../../services/searchService";

const emits = defineEmits(["close"]);

const searchInput = ref(null);
const loading = ref(false);
const errorMessage = ref("");
const documents = ref([]);
const results = ref({
  items: [],
  totalCount: 0,
  page: 1,
  pageSize: 10,
});

const query = ref("");
const selectedDocumentId = ref("");
const selectedFileStatus = ref("");
const selectedTaskStatus = ref("");
const selectedTaskPriority = ref("");
const uploadedFrom = ref("");
const uploadedTo = ref("");
const taskDueFrom = ref("");
const taskDueTo = ref("");
const sort = ref("0");

const fileStatusOptions = [
  { value: 0, label: "Pending" },
  { value: 1, label: "Processing" },
  { value: 2, label: "Completed" },
  { value: 3, label: "Failed" },
];

const taskStatusOptions = [
  { value: 0, label: "Pending" },
  { value: 1, label: "In Progress" },
  { value: 2, label: "Completed" },
  { value: 3, label: "Cancelled" },
];

const taskPriorityOptions = [
  { value: 0, label: "Low" },
  { value: 1, label: "Medium" },
  { value: 2, label: "High" },
  { value: 3, label: "Urgent" },
];

let debounceId;

const closeModal = () => {
  emits("close");
};

const showEmptyState = computed(
  () => !loading.value && !errorMessage.value && results.value.items.length === 0,
);

const buildPayload = () => ({
  query: query.value.trim() || null,
  documentIds: selectedDocumentId.value ? [Number(selectedDocumentId.value)] : null,
  fileStatuses: selectedFileStatus.value ? [Number(selectedFileStatus.value)] : null,
  uploadedFrom: uploadedFrom.value || null,
  uploadedTo: uploadedTo.value || null,
  taskStatuses: selectedTaskStatus.value ? [Number(selectedTaskStatus.value)] : null,
  taskPriorities: selectedTaskPriority.value
    ? [Number(selectedTaskPriority.value)]
    : null,
  taskDueFrom: taskDueFrom.value || null,
  taskDueTo: taskDueTo.value || null,
  page: 1,
  pageSize: 10,
  sort: Number(sort.value),
});

const loadDocuments = async () => {
  try {
    documents.value = await getUserDocuments();
  } catch (error) {
    console.error("Error loading documents:", error);
  }
};

const loadResults = async () => {
  loading.value = true;
  errorMessage.value = "";

  try {
    const response = await searchDocuments(buildPayload());
    if (!response.success) {
      errorMessage.value = response.message || "Search failed.";
      results.value = { items: [], totalCount: 0, page: 1, pageSize: 10 };
      return;
    }

    results.value = response.results;
  } catch (error) {
    console.error("Error fetching search results:", error);
    errorMessage.value = "Error fetching search results.";
    results.value = { items: [], totalCount: 0, page: 1, pageSize: 10 };
  } finally {
    loading.value = false;
  }
};

const resetFilters = () => {
  selectedDocumentId.value = "";
  selectedFileStatus.value = "";
  selectedTaskStatus.value = "";
  selectedTaskPriority.value = "";
  uploadedFrom.value = "";
  uploadedTo.value = "";
  taskDueFrom.value = "";
  taskDueTo.value = "";
  sort.value = "0";
};

watch(
  [
    query,
    selectedDocumentId,
    selectedFileStatus,
    selectedTaskStatus,
    selectedTaskPriority,
    uploadedFrom,
    uploadedTo,
    taskDueFrom,
    taskDueTo,
    sort,
  ],
  () => {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      loadResults();
    }, 250);
  },
);

onMounted(async () => {
  await loadDocuments();
  await nextTick();
  if (searchInput.value) {
    searchInput.value.focus();
  }
  await loadResults();
});
</script>
