<template>
  <div class="profile-container">
    <div class="profile-header">
      <button class="back-btn" @click="goBack">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="size-6"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"
          />
        </svg>
        Retour
      </button>
      <h1>Mon Profil</h1>
    </div>

    <div class="profile-content">
      <div class="profile-card">
        <div class="avatar-section">
          <div class="avatar">
            {{ userInitials }}
          </div>
          <button class="change-avatar-btn">Changer l'avatar</button>
        </div>

        <div class="info-section">
          <h2>Informations personnelles</h2>
          <div class="info-grid">
            <div class="info-item">
              <label>Nom d'utilisateur</label>
              <input
                v-model="profile.username"
                type="text"
                class="info-input"
              />
            </div>
            <div class="info-item">
              <label>Email</label>
              <input v-model="profile.email" type="email" class="info-input" />
            </div>
            <div class="info-item">
              <label>Nom complet</label>
              <input
                v-model="profile.fullName"
                type="text"
                class="info-input"
              />
            </div>
            <div class="info-item">
              <label>Téléphone</label>
              <input v-model="profile.phone" type="tel" class="info-input" />
            </div>
          </div>
        </div>

        <div class="security-section">
          <h2>Sécurité</h2>
          <div class="security-actions">
            <button
              class="security-btn"
              @click="showChangePasswordModal = true"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="size-6"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
                />
              </svg>
              Changer le mot de passe
            </button>
            <button class="security-btn" @click="show2FAModal = true">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="size-6"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
                />
              </svg>
              Authentification à deux facteurs
            </button>
          </div>
        </div>

        <div class="actions-section">
          <button class="save-btn" @click="saveProfile" :disabled="saving">
            {{ saving ? "Enregistrement..." : "Enregistrer les modifications" }}
          </button>
          <button class="cancel-btn" @click="cancelChanges">Annuler</button>
        </div>
      </div>

      <div class="stats-card">
        <h2>Statistiques</h2>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-number">{{ userStats.documentsCount }}</div>
            <div class="stat-label">Documents</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">{{ userStats.tasksCount }}</div>
            <div class="stat-label">Tâches</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">{{ userStats.storageUsed }}</div>
            <div class="stat-label">Espace utilisé</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">{{ userStats.lastLogin }}</div>
            <div class="stat-label">Dernière connexion</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal pour changer le mot de passe -->
    <div
      v-if="showChangePasswordModal"
      class="modal-overlay"
      @click="showChangePasswordModal = false"
    >
      <div class="modal" @click.stop>
        <h3>Changer le mot de passe</h3>
        <div class="form-group">
          <label>Mot de passe actuel</label>
          <input v-model="passwordForm.currentPassword" type="password" />
        </div>
        <div class="form-group">
          <label>Nouveau mot de passe</label>
          <input v-model="passwordForm.newPassword" type="password" />
        </div>
        <div class="form-group">
          <label>Confirmer le nouveau mot de passe</label>
          <input v-model="passwordForm.confirmPassword" type="password" />
        </div>
        <div class="modal-actions">
          <button class="confirm-btn" @click="changePassword">Confirmer</button>
          <button class="cancel-btn" @click="showChangePasswordModal = false">
            Annuler
          </button>
        </div>
      </div>
    </div>

    <!-- Modal pour 2FA -->
    <div
      v-if="show2FAModal"
      class="modal-overlay"
      @click="show2FAModal = false"
    >
      <div class="modal" @click.stop>
        <h3>Authentification à deux facteurs</h3>
        <p>
          Activez l'authentification à deux facteurs pour sécuriser votre
          compte.
        </p>
        <div class="modal-actions">
          <button class="confirm-btn">Activer 2FA</button>
          <button class="cancel-btn" @click="show2FAModal = false">
            Annuler
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const profile = ref({
  username: "",
  email: "",
  fullName: "",
  phone: "",
});

const originalProfile = ref({});
const saving = ref(false);
const showChangePasswordModal = ref(false);
const show2FAModal = ref(false);

const passwordForm = ref({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const userStats = ref({
  documentsCount: 0,
  tasksCount: 0,
  storageUsed: "0 MB",
  lastLogin: "Aujourd'hui",
});

const userInitials = computed(() => {
  if (profile.value.fullName) {
    return profile.value.fullName
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }
  return profile.value.username ? profile.value.username[0].toUpperCase() : "U";
});

const goBack = () => {
  router.go(-1);
};

const saveProfile = async () => {
  saving.value = true;
  try {
    // Simuler une sauvegarde
    await new Promise((resolve) => setTimeout(resolve, 1000));
    originalProfile.value = { ...profile.value };
  } catch (error) {
    console.error("Erreur lors de la sauvegarde:", error);
  } finally {
    saving.value = false;
  }
};

const cancelChanges = () => {
  profile.value = { ...originalProfile.value };
};

const changePassword = async () => {
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    alert("Les mots de passe ne correspondent pas");
    return;
  }

  try {
    // Simuler le changement de mot de passe
    await new Promise((resolve) => setTimeout(resolve, 1000));
    showChangePasswordModal.value = false;
    passwordForm.value = {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    };
  } catch (error) {
    console.error("Erreur lors du changement de mot de passe:", error);
  }
};

onMounted(() => {
  // Charger les données de l'utilisateur
  if (authStore.user) {
    profile.value = {
      username: authStore.user.username || "",
      email: authStore.user.email || "",
      fullName: authStore.user.fullName || "",
      phone: authStore.user.phone || "",
    };
    originalProfile.value = { ...profile.value };
  }

  // Simuler le chargement des statistiques
  userStats.value = {
    documentsCount: 42,
    tasksCount: 15,
    storageUsed: "125 MB",
    lastLogin: new Date().toLocaleDateString("fr-FR"),
  };
});
</script>

<style scoped>
.profile-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  color: #4b5563;
  cursor: pointer;
  font-size: 1rem;
  transition: color 0.2s;
}

.back-btn:hover {
  color: #1f2937;
}

.profile-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.profile-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
}

.profile-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.avatar-section {
  text-align: center;
  margin-bottom: 2rem;
}

.avatar {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  font-size: 3rem;
  font-weight: 700;
  color: white;
}

.change-avatar-btn {
  background: #f3f4f6;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  color: #4b5563;
  transition: background 0.2s;
}

.change-avatar-btn:hover {
  background: #e5e7eb;
}

.info-section,
.security-section {
  margin-bottom: 2rem;
}

.info-section h2,
.security-section h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 1rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-item label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.info-input {
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.info-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.security-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.security-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  padding: 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  color: #374151;
  transition: all 0.2s;
}

.security-btn:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.actions-section {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.save-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.save-btn:hover:not(:disabled) {
  background: #2563eb;
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cancel-btn {
  background: #f3f4f6;
  color: #4b5563;
  border: 1px solid #d1d5db;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.cancel-btn:hover {
  background: #e5e7eb;
}

.stats-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stats-card h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: #3b82f6;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 1rem;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.confirm-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.confirm-btn:hover {
  background: #2563eb;
}

@media (max-width: 768px) {
  .profile-content {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .actions-section {
    flex-direction: column;
  }
}
</style>
