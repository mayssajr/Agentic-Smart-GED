<template>
  <div class="relative" ref="dropdownContainer">
    <!-- Dropdown button -->
    <button
      @click="toggleDropdown"
      @keydown.enter="toggleDropdown"
      @keydown.space.prevent="toggleDropdown"
      @keydown.escape="closeDropdown"
      @keydown.arrow-down.prevent="focusFirstItem"
      type="button"
      :aria-expanded="isOpen"
      aria-haspopup="true"
      :aria-label="ariaLabel"
      class="user-menu focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150"
      :disabled="disabled"
    >
      <div class="flex items-center">
        <!-- User icon -->
        <div class="flex-shrink-0">
          <i
            v-if="!userManage"
            class="fas fa-circle-user text-lg text-slate-700"
            aria-hidden="true"
          ></i>
        </div>
      </div>

      <!-- Chevron icon -->
      <i
        class="fas fa-chevron-down flex-shrink-0 text-xs text-slate-400 transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
        aria-hidden="true"
      ></i>
    </button>

    <!-- Dropdown menu -->
    <Transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <div
        v-show="isOpen"
        ref="dropdownMenu"
        role="menu"
        :aria-orientation="'vertical'"
        :aria-labelledby="buttonId"
        class="absolute z-50 w-full min-w-48 mt-2 origin-top-right bg-white border border-slate-200 divide-y divide-slate-100 rounded-lg shadow-lg ring-1 ring-slate-900/5 focus:outline-none"
        :class="dropdownPosition"
      >
        <div class="py-1">
          <a
            v-for="(item, index) in items"
            :key="item.id || item.text"
            :href="item.href || '#'"
            @click.prevent="handleItemClick(item, $event)"
            @keydown.enter.prevent="handleItemClick(item, $event)"
            @keydown.space.prevent="handleItemClick(item, $event)"
            @keydown.escape="closeDropdown"
            @keydown.arrow-down.prevent="focusNextItem(index)"
            @keydown.arrow-up.prevent="focusPreviousItem(index)"
            role="menuitem"
            :tabindex="isOpen ? 0 : -1"
            :class="[
              'group flex items-center w-full px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-950 focus:outline-none focus:bg-slate-50 focus:text-slate-950 transition-colors duration-150',
              {
                'text-red-600 hover:bg-red-50 hover:text-red-700 focus:bg-red-50 focus:text-red-700':
                  item.variant === 'danger',
                'opacity-50 cursor-not-allowed': item.disabled,
                'cursor-pointer': !item.disabled,
              },
            ]"
            :disabled="item.disabled"
            :aria-disabled="item.disabled"
          >
            <!-- Item icon (optional) -->
            <component
              v-if="item.icon"
              :is="item.icon"
              class="flex-shrink-0 w-4 h-4 mr-3 text-slate-400 group-hover:text-slate-500"
              :class="{
                'text-red-400 group-hover:text-red-500':
                  item.variant === 'danger',
              }"
              aria-hidden="true"
            />

            <span class="flex-1 truncate">{{ item.text }}</span>

            <!-- Keyboard shortcut (optional) -->
            <kbd
              v-if="item.shortcut"
              class="ml-auto text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded"
            >
              {{ item.shortcut }}
            </kbd>
          </a>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";

const props = defineProps({
  buttonText: {
    type: String,
    default: "Select option",
    userManage: false,
  },
  items: {
    type: Array,
    default: () => [
      {
        id: "dashboard",
        text: "Dashboard",
        href: "/dashboard",
        action: "dashboard",
      },
      {
        id: "settings",
        text: "Settings",
        href: "/settings",
        action: "settings",
      },
      {
        id: "earnings",
        text: "Earnings",
        href: "/earnings",
        action: "earnings",
      },
      {
        id: "signout",
        text: "Sign out",
        href: "#",
        action: "signout",
        variant: "danger",
        shortcut: "⌘Q",
      },
    ],
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  placement: {
    type: String,
    default: "bottom-start",
    validator: (value) =>
      ["bottom-start", "bottom-end", "top-start", "top-end"].includes(value),
  },
  ariaLabel: {
    type: String,
    default: "User menu",
  },
});

const emit = defineEmits([
  "item-clicked",
  "dropdown-opened",
  "dropdown-closed",
]);

const isOpen = ref(false);
const dropdownContainer = ref(null);
const dropdownMenu = ref(null);
const buttonId = "dropdown-button-" + Math.random().toString(36).substr(2, 9);

const dropdownPosition = computed(() => {
  const positions = {
    "bottom-start": "left-0",
    "bottom-end": "right-0",
    "top-start": "left-0 bottom-full mb-1",
    "top-end": "right-0 bottom-full mb-1",
  };
  return positions["bottom-end"];
});

const toggleDropdown = () => {
  if (props.disabled) return;

  if (isOpen.value) {
    closeDropdown();
  } else {
    openDropdown();
  }
};

const openDropdown = async () => {
  isOpen.value = true;
  emit("dropdown-opened");

  // await nextTick();
  // focusFirstItem();
};

const closeDropdown = () => {
  isOpen.value = false;
  emit("dropdown-closed");

  // Return focus to button
  // const button = dropdownContainer.value?.querySelector('button');
  // if (button) {
  //   button.focus();
  // }
};

const handleItemClick = (item, event) => {
  if (item.disabled) {
    event.preventDefault();
    return;
  }

  emit("item-clicked", {
    action: item.action,
    item: item,
    originalEvent: event,
  });

  closeDropdown();

  // Only prevent default if no href or href is '#'
  if (!item.href || item.href === "#") {
    event.preventDefault();
  }
};

const focusFirstItem = () => {
  const firstItem = dropdownMenu.value?.querySelector(
    '[role="menuitem"]:not([disabled])',
  );
  if (firstItem) {
    firstItem.focus();
  }
};

const focusNextItem = (currentIndex) => {
  const items = dropdownMenu.value?.querySelectorAll(
    '[role="menuitem"]:not([disabled])',
  );
  if (!items) return;

  const nextIndex = (currentIndex + 1) % items.length;
  items[nextIndex]?.focus();
};

const focusPreviousItem = (currentIndex) => {
  const items = dropdownMenu.value?.querySelectorAll(
    '[role="menuitem"]:not([disabled])',
  );
  if (!items) return;

  const prevIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
  items[prevIndex]?.focus();
};

const handleClickOutside = (event) => {
  if (isOpen.value && !dropdownContainer.value?.contains(event.target)) {
    closeDropdown();
  }
};

const handleEscapeKey = (event) => {
  if (event.key === "Escape" && isOpen.value) {
    closeDropdown();
  }
};

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
  document.addEventListener("keydown", handleEscapeKey);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside);
  document.removeEventListener("keydown", handleEscapeKey);
});

// Expose methods for parent component
defineExpose({
  open: openDropdown,
  close: closeDropdown,
  toggle: toggleDropdown,
  isOpen: computed(() => isOpen.value),
});
</script>
<style scoped>
.user-menu {
  padding: 0.625rem 0.75rem;
  gap: 0.5rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.user-menu:hover {
  background-color: #f1f5f9;
  border-color: #cbd5e1;
}
</style>
