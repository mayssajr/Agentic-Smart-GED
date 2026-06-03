<template>
  <div id="app">
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useUiStore } from "./stores/ui.js";
import { watch, onMounted } from "vue";
const uiStore = useUiStore();
watch(
  () => uiStore.fullTitle,
  (title) => {
    document.title = title;
  },
);
onMounted(() => {
  document.title = uiStore.fullTitle;
  let favicon = document.getElementById("dynamic-favicon");
  if (!favicon) {
    favicon = document.createElement("link");
    favicon.id = "dynamic-favicon";
    favicon.rel = "icon";
    favicon.type = "image/png";
    document.head.appendChild(favicon);
  } else {
    favicon.type = "image/png";
  }
  favicon.href = uiStore.tabIcon;
});
</script>

<style scoped></style>
