<template>
  <div class="min-h-screen bg-gray-50">
      
      <!-- Hero Section -->
    <div class="fixed top-4 left-4 z-50 flex items-center gap-2">
      <img src="../assets/images/logo1.png" alt="MINIGED Logo" class="w-15 h-15 rounded-lg object-contain" />
      <span class="font-bold font-sans text-4xl text-white" style="text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;">MiniGED</span>
    </div>
      <section class="gradient-bg min-h-screen flex items-center relative overflow-hidden">
          <div class="max-w-6xl mx-auto px-6 w-full">
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                  <div class="text-white space-y-8 fade-in" :class="{ visible: heroVisible }">
            <h1 class="text-5xl lg:text-6xl font-bold leading-tight">
              Gérez vos documents avec 
              <span class="animated-text">{{ animatedText }}</span>
            </h1>
            
            <p class="text-xl opacity-90 leading-relaxed">
              Capturez, indexez et recherchez instantanément dans tous vos documents 
              grâce à notre système intelligent de reconnaissance optique.
            </p>
            
            <button 
              @click="scrollToSection('#value')"
              class="glass-effect text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all duration-300 btn-hover inline-flex items-center gap-3"
            >
              Découvrir comment ça marche
              <span>→</span>
            </button>
          </div>

          <!-- Dashboard Mockup -->
          <div class="dashboard-3d w-180 bg-white rounded-2xl p-6 shadow-2xl fade-in" :class="{ visible: heroVisible }">
            <!-- Dashboard Header -->
            <div class="flex flex-col lg:flex-row justify-between items-center mb-6 pb-4 border-b border-gray-200">
              <div class=" flex justify-between items-center text-xl font-bold text-indigo-600 mb-4 lg:mb-0">
                 <img src="../assets/images/logo1.png" alt="MINIGED Logo" class="logo-icon" />
          <span class="logo-text" v-show="!sidebarCollapsed">Mini<span class="logo-text-highlight">GED</span></span>
              </div>
              
              <div class="flex-1 lg:mx-6 w-full lg:w-auto">
                <input 
                  type="text" 
                  class="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-indigo-500 outline-none transition-colors"
                  placeholder="Rechercher dans vos documents..."

                />
              </div>
              
              <div class="flex gap-6 text-sm text-gray-600 mt-4 lg:mt-0">
                <div class="text-center">
                  <div class="text-lg font-semibold text-gray-900">127</div>
                  <div>Documents</div>
                </div>
                <div class="text-center">
                  <div class="text-lg font-semibold text-gray-900">45</div>
                  <div>Cette semaine</div>
                </div>
                <div class="text-center">
                  <div class="text-lg font-semibold text-gray-900">98%</div>
                  <div>OCR Traité</div>
                </div>
              </div>
            </div>
            
            <!-- Documents List -->
            <div class="space-y-3">
              <div 
                v-for="doc in documents" 
                :key="doc.id" 
                class="flex items-center gap-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div class="w-10 h-10 bg-indigo-500 rounded-lg flex items-center justify-center text-white">
                  {{ doc.icon }}
                </div>
                <div class="flex-1">
                  <div class="font-medium text-gray-900 text-sm">{{ doc.name }}</div>
                  <div class="text-xs text-gray-500 flex items-center gap-1">
                    <span></span>
                    <span>{{ doc.source }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Value Comparison Section -->
    <section id="value" class="py-20">
      <div class="max-w-6xl mx-auto px-6">
        <h2 class="text-4xl font-semibold text-center text-gray-900 mb-16 fade-in" :class="{ visible: valueVisible }">
          Un système complet en deux parties
        </h2>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
          <!-- Desktop App Card -->
          <div class="value-card bg-white p-10 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 btn-hover fade-in" :class="{ visible: valueVisible }">
            <div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-t-xl"></div>
            <h3 class="text-2xl font-semibold text-gray-900 mb-8 text-center">
              🖥️ Application Bureau
            </h3>
            <ul class="space-y-4">
              <li class="flex items-center gap-4">
                <span class="text-xl">📷</span>
                <span class="text-gray-700">Capture d'écran intelligente</span>
              </li>
              <li class="flex items-center gap-4">
                <span class="text-xl">🔤</span>
                <span class="text-gray-700">OCR instantané</span>
              </li>
              <li class="flex items-center gap-4">
                <span class="text-xl">☁️</span>
                <span class="text-gray-700">Synchronisation automatique</span>
              </li>
              <li class="flex items-center gap-4">
                <span class="text-xl">⚡</span>
                <span class="text-gray-700">Traitement en temps réel</span>
              </li>
            </ul>
          </div>

          <!-- Web App Card -->
          <div class="value-card bg-white p-10 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 btn-hover fade-in" :class="{ visible: valueVisible }">
            <div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-t-xl"></div>
            <h3 class="text-2xl font-semibold text-gray-900 mb-8 text-center">
              🌐 Application Web
            </h3>
            <ul class="space-y-4">
              <li class="flex items-center gap-4">
                <span class="text-xl">🗄️</span>
                <span class="text-gray-700">Stockage sécurisé</span>
              </li>
              <li class="flex items-center gap-4">
                <span class="text-xl">🔍</span>
                <span class="text-gray-700">Recherche avancée</span>
              </li>
              <li class="flex items-center gap-4">
                <span class="text-xl">🏷️</span>
                <span class="text-gray-700">Organisation intelligente</span>
              </li>
              <li class="flex items-center gap-4">
                <span class="text-xl">🌍</span>
                <span class="text-gray-700">Accès universel</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="cta-section py-20 bg-gray-100">
      <div class="max-w-4xl mx-auto px-6 text-center">
        <div class="fade-in" :class="{ visible: ctaVisible }">
          <h2 class="text-4xl font-semibold text-gray-900 mb-6">
            Prêt à transformer votre gestion documentaire ?
          </h2>
          <p class="text-xl text-gray-600 mb-10">
            Commencez dès maintenant avec l'une de nos applications
          </p>
          
          <div class="flex flex-col sm:flex-row gap-6 justify-center items-center pb-5 ">
            <button class="btn-primary px-8 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-semibold text-lg transition-all duration-300 btn-hover shadow-lg">
              Lancer l'App Web
            </button>
            <button class="btn-secondary relative px-8 py-4 bg-white text-indigo-600 border-2 border-indigo-600 rounded-lg font-semibold text-lg transition-all duration-300 btn-hover">
              <span class="absolute -top-3 -right-2 bg-yellow-400 text-xs px-2 py-1 rounded text-gray-800 font-bold">
                ⭐ Recommandé
              </span>
              Télécharger App Bureau
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Sticky CTA -->
    <div class="sticky-cta fixed bottom-0 left-0 right-0 bg-white shadow-lg p-4 transition-transform duration-300 z-50" :class="{ 'translate-y-0': showStickyCta, 'translate-y-full': !showStickyCta }">
      <div class="max-w-4xl  mx-auto flex flex-col sm:flex-row gap-4 justify-center items-center">
        <button class="btn-primary px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-semibold transition-all duration-300 btn-hover">
          Lancer l'App Web
        </button>
        <button class="btn-secondary px-6 py-3 bg-white text-indigo-600 border-2 border-indigo-600 rounded-lg font-semibold transition-all duration-300 btn-hover">
          Télécharger App Bureau
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// Reactive state
const heroVisible = ref(true)
const valueVisible = ref(false)
const ctaVisible = ref(false)
const showStickyCta = ref(false)
const animatedText = ref('')

const textOptions = [
  'intelligence',
  'précision', 
  'rapidité',
  'efficacité'
]

let currentTextIndex = 0
let currentCharIndex = 0
let isDeleting = false

const documents = ref([
  { 
    id: 1, 
    name: 'Contrat_Location_2024.pdf', 
  
    icon: '📄' 
  },
  { 
    id: 2, 
    name: 'Facture_Electricite_Jan.pdf', 
  
    icon: '🧾' 
  },
  { 
    id: 3, 
    name: 'CV_Candidat_Marketing.pdf', 
  
    icon: '📋' 
  },
  { 
    id: 4, 
    name: 'Rapport_Mensuel_Q4.pdf', 
  
    icon: '📊' 
  }
])

// Animation functions
const typeText = () => {
  const currentText = textOptions[currentTextIndex]
  
  if (isDeleting) {
    animatedText.value = currentText.substring(0, currentCharIndex - 1)
    currentCharIndex--
  } else {
    animatedText.value = currentText.substring(0, currentCharIndex + 1)
    currentCharIndex++
  }

  if (!isDeleting && currentCharIndex === currentText.length) {
    setTimeout(() => isDeleting = true, 2000)
  } else if (isDeleting && currentCharIndex === 0) {
    isDeleting = false
    currentTextIndex = (currentTextIndex + 1) % textOptions.length
  }

  setTimeout(typeText, isDeleting ? 100 : 150)
}

const scrollToSection = (target) => {
  const element = document.querySelector(target)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}

const handleScroll = () => {
  const scrollY = window.scrollY
  const windowHeight = window.innerHeight

  // Show sticky CTA after scrolling past hero
  showStickyCta.value = scrollY > windowHeight * 0.8

  // Check section visibility with intersection observer logic
  const valueSection = document.querySelector('#value')
  const ctaSection = document.querySelector('.cta-section')

  if (valueSection) {
    const rect = valueSection.getBoundingClientRect()
    if (rect.top < windowHeight * 0.7) {
      valueVisible.value = true
    }
  }

  if (ctaSection) {
    const rect = ctaSection.getBoundingClientRect()
    if (rect.top < windowHeight * 0.7) {
      ctaVisible.value = true
    }
  }
}

// Lifecycle hooks
onMounted(() => {
  typeText()
  window.addEventListener('scroll', handleScroll)
  handleScroll() // Initial check
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.gradient-bg {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.animated-text {
  color: #ffd700;
  font-weight: 600;
  display: inline-block;
  border-right: 2px solid #ffd700;
  padding-right: 8px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { border-color: #ffd700; }
  51%, 100% { border-color: transparent; }
}

.dashboard-3d {
  transform: perspective(1000px) rotateY(-5deg) rotateX(5deg);
  transition: all 0.3s ease;
}

.dashboard-3d:hover {
  transform: perspective(1000px) rotateY(-2deg) rotateX(2deg);
}

.fade-in {
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease;
}

.fade-in.visible {
  opacity: 1;
  transform: translateY(0);
}

.btn-hover:hover {
  transform: translateY(-2px);
}

.glass-effect {
  background: rgba(255, 255, 255, 0.15);
  border: 2px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

.glass-effect:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
}

.value-card {
  position: relative;
}

.btn-secondary:hover {
  background-color: #667eea;
  color: white;
}

.sticky-cta {
  backdrop-filter: blur(10px);
}

.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: contain;
}

.logo-text {
  font-weight: bold;
  font-size: 18px;
  color: #2d3748;
  font-family: 'Inter', sans-serif;
}

.logo-text-highlight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-family: 'Inter', sans-serif;
  color: #667eea;
  /* Fallback color */
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .text-5xl {
    font-size: 2.5rem;
  }
  
  .lg\\:text-6xl {
    font-size: 3rem;
  }
  
  .dashboard-3d {
    transform: none;
  }
  
  .grid.lg\\:grid-cols-2 {
    grid-template-columns: 1fr;
  }
}
</style>