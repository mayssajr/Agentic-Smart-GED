<template>
  <div
    class="border border-gray-200 rounded-lg cursor-pointer p-4 mb-4 bg-white shadow-sm hover:shadow-md transition-shadow"
    @click="directToDocumentView"
  >
    <div class="flex justify-between items-start mb-3 gap-3">
      <div class="flex-1">
        <div class="flex items-center gap-2 mb-1">
          <i class="fas fa-folder w-4 h-4 text-blue-600"></i>
          <h3 class="m-0 text-lg text-gray-800 font-medium">
            {{ result.documentTitle }}
          </h3>
        </div>
        <p
          v-if="result.documentDescription"
          class="text-sm text-gray-600 line-clamp-2"
        >
          {{ result.documentDescription }}
        </p>
      </div>
      <span class="text-xs text-gray-400 bg-gray-50 px-2 py-1 rounded">
        Doc ID: {{ result.documentId }}
      </span>
    </div>

    <div class="bg-gray-50 rounded-md p-3 mb-3">
      <div class="flex items-center justify-between mb-2 gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <i class="fas fa-file-lines w-4 h-4 text-gray-600"></i>
          <span class="text-sm font-medium text-gray-700 truncate">
            {{ result.fileName }}
          </span>
          <span
            class="text-xs text-white px-2 py-1 rounded border"
            :class="statusBadgeClass"
          >
            {{ statusLabel }}
          </span>
        </div>
        <span class="text-xs text-gray-500">Rank: {{ formattedRank }}</span>
      </div>
      <div class="text-xs text-gray-500">
        Uploaded: {{ formatDate(result.uploadedAt) }}
      </div>
    </div>

    <div class="border-l-4 border-blue-200 pl-4">
      <div
        class="text-sm leading-relaxed text-gray-700 whitespace-pre-line bg-blue-50 p-3 rounded"
      >
        <span v-html="result.snippet || emptySnippet"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
});

const statusMap = {
  0: { label: "Pending", className: "bg-amber-400 border-amber-300" },
  1: { label: "Processing", className: "bg-blue-400 border-blue-300" },
  2: { label: "Completed", className: "bg-green-500 border-green-400" },
  3: { label: "Failed", className: "bg-red-500 border-red-400" },
};

const statusLabel = computed(
  () => statusMap[props.result.fileStatus]?.label || "Unknown",
);

const statusBadgeClass = computed(
  () => statusMap[props.result.fileStatus]?.className || "bg-slate-500 border-slate-400",
);

const formattedRank = computed(() =>
  Number(props.result.rank || 0).toFixed(3),
);

const emptySnippet = "No snippet available.";

const formatDate = (dateString) => {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const directToDocumentView = () => {
  router.push({
    path: `/document/${props.result.documentId}`,
    query: {
      FileId: props.result.fileId,
    },
  });
};
</script>
