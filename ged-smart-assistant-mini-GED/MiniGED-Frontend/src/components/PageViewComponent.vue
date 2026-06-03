<template>
  <div style="position: relative">
    <!-- <SpeedDial :model="items" :radius="120" type="quarter-circle" direction="up-right"
            :style="{ left: 0, bottom: 0 }" /> -->

    <VuePDF
      :pdf="pdf"
      :scale="scale"
      :page="page"
      style="margin-bottom: 10px"
      :fit-parent="fitParent"
      @loaded="pageLoaded"
    >
      <div
        class="spinner-grow m-0 9-0"
        style="width: 100%; height: 100%"
        role="status"
      >
        <span class="sr-only m-0 p-0">Loading...</span>
      </div>
    </VuePDF>
  </div>
</template>

<script setup>
import { VuePDF } from "@tato30/vue-pdf";
import { ref, defineProps } from "vue";
import { defineEmits } from "vue";
const props = defineProps([
  "pdf",
  "src",
  "scale",
  "page",
  "fitParent",
  "highlightText",
]);
const emits = defineEmits(["pageLoaded"]);
function pageLoaded(viewport) {
  emits("pageLoaded", props.page);
}
</script>

<style lang="scss" scoped>
.toggleButton {
  background: #f9f9fb00;
  color: #585858;
  padding: 0px;
  width: auto;
  cursor: pointer;
  border: none;
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 100;
}
</style>
