<template>
  <div
    class="min-h-screen bg-gradient-to-br from-blue-50 to-violet-50 text-gray-900 overflow-hidden relative"
  >
    <div class="absolute inset-0 overflow-hidden">
      <div
        class="absolute -top-40 -right-40 w-80 h-80 bg-blue-200/20 rounded-full blur-3xl animate-pulse"
      ></div>
      <div
        class="absolute -bottom-40 -left-40 w-80 h-80 bg-violet-200/20 rounded-full blur-3xl animate-pulse delay-1000"
      ></div>
      <div
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-300/10 rounded-full blur-3xl animate-pulse delay-500"
      ></div>
    </div>

    <div
      class="relative z-10 min-h-screen flex flex-col items-center justify-center px-6 py-12"
    >
      <div class="mb-8">
        <img src="/src/images/Logo1.png" class="w-32 h-32" />
      </div>

      <div class="text-center max-w-2xl mb-12">
        <h1
          class="text-5xl md:text-6xl font-bold mb-6 tracking-tight text-gray-900"
        >
          L'assistant intelligent <span class="text-blue-600">multimodal</span>
        </h1>

        <p class="text-lg md:text-xl text-gray-700 mb-8 leading-relaxed">
          L'avenir de la GED/ECM est vocal, visuel et intelligent. Transformez
          votre manière d'interagir avec des systèmes documentaires complexes
          grâce au langage naturel et à l'automatisation par l'IA.
        </p>

        <Button
          label="Commencer"
          icon="pi pi-arrow-right"
          iconPos="right"
          rounded
          size="large"
          @click="goToChat"
        />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl w-full">
        <Card v-for="feature in features" :key="feature.title">
          <template #content>
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-xl font-semibold mb-2 text-gray-900">
                {{ feature.title }}
              </h3>
              <div class="mb-4">
                <Avatar size="large" :icon="`pi pi-${feature.icon}`" />
              </div>
            </div>
            <p class="text-gray-600 text-md">{{ feature.description }}</p>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import Button from "primevue/button";
import Avatar from "primevue/avatar";
import Card from "primevue/card";

const router = useRouter();

const features = [
  {
    title: "Entrées Multimodales",
    description:
      "Supporte à la fois le mode texte (chatbot classique) et le mode vocal (reconnaissance vocale) pour une interaction flexible.",
    icon: "comments",
  },
  {
    title: "Analyse d'Intention",
    description:
      "Utilise des LLM pour extraire des entités et identifier si l'utilisateur souhaite chercher, créer ou modifier un document.",
    icon: "lightbulb",
  },
  {
    title: "Orchestration d'API",
    description:
      "Exécute des appels API REST (GET, POST, PUT) pour interagir directement avec le backend de la GED",
    icon: "sort-alt",
  },
];

const goToChat = () => {
  router.push("/chat");
};
</script>
