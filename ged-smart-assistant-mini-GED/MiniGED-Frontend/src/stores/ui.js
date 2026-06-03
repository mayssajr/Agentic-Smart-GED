import { defineStore } from "pinia";
import { computed } from "vue";

const useUiStore = defineStore("ui", {
  state: () => ({
    baseTitle: "MiniGED",
    currentPage: "Accueil",
    // tabIcon now computed based on isSearchActive
    isSearchActive: false,
  }),

  getters: {
    fullTitle: (state) => {
      if (state.isSearchActive) {
        return `${state.baseTitle} - Recherche`;
      }
      return `${state.baseTitle} - ${state.currentPage}`;
    },
    tabIcon: () => "/favicon.png",
  },

  actions: {
    setPage(pageName) {
      this.currentPage = pageName;
    },

    setSearchActive(active) {
      this.isSearchActive = active;
    },
  },
});

export { useUiStore };
export default useUiStore;
