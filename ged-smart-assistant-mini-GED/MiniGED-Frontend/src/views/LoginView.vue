<template>
  <div class="auth-container">
    <div class="auth-left">
      <div class="brand">
        <div>
          <img class="brand-icon" src="../assets/images/logo1.png" alt="Logo" />
        </div>
        <h2>Mini GED</h2>
      </div>

      <div class="illustration">
        <div class="illustration-circle">
          <img class="w-1/2" src="../assets/images/logo1.png" />
        </div>
      </div>

      <div class="left-content">
        <h3>Plateforme GED intelligente avec IA intégrée</h3>
        <p>
          Gérez, classez et retrouvez vos documents en un clic grâce à
          l'intelligence artificielle
        </p>
      </div>
    </div>

    <div class="auth-right">
      <div class="form-container">
        <div class="form-header">
          <h2>Commencez à gérer vos documents</h2>
        </div>

        <form @submit.prevent="handleLogin" class="auth-form">
          <div class="form-group">
            <input
              v-model="credentials.email"
              type="email"
              placeholder="Email"
              required
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <input
              v-model="credentials.password"
              type="password"
              placeholder="Mot de passe"
              required
              :disabled="loading"
            />
          </div>

          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <button type="submit" :disabled="loading" class="submit-btn">
            {{ loading ? "Connexion..." : "CONNEXION" }}
          </button>
        </form>

        <div class="form-footer">
          <p>
            Vous n'avez pas encore de compte ?
            <router-link to="/register" class="link"
              >Créer un compte</router-link
            >
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const credentials = ref({
  email: "",
  password: "",
});

const loading = ref(false);
const error = ref(null);

const handleLogin = async () => {
  try {
    loading.value = true;
    error.value = null;

    await authStore.login(credentials.value);

    // Redirect to saved returnUrl or fallback to /documents
    const redirectTo = authStore.returnUrl || "/documents";
    authStore.returnUrl = null; // clear it
    router.push(redirectTo);
  } catch (err) {
    error.value = authStore.error;
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.auth-container {
  display: flex;
  min-height: 100vh;
  background: #f8fafc;
}

.auth-left {
  flex: 1;
  background: linear-gradient(135deg, #1d4ed8 0%, #0f172a 100%);
  color: white;
  display: flex;
  flex-direction: column;
  padding: 3rem;
  position: relative;
  overflow: hidden;
}

.auth-left::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    135deg,
    rgba(37, 99, 235, 0.88) 0%,
    rgba(15, 23, 42, 0.88) 100%
  );
}

.brand {
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 2;
  position: relative;
  color: #f8fafc;
}

.brand-icon {
  font-size: 2rem;
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
}

.brand h2 {
  font-size: 1.8rem;
  font-weight: 800;
  margin: 0;
}

.illustration {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  position: relative;
}

.illustration-circle {
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  backdrop-filter: blur(10px);
}

.person-icon {
  color: rgba(255, 255, 255, 0.95);
  font-size: 8rem;
}

.left-content {
  z-index: 2;
  position: relative;
  text-align: center;
}

.left-content h3 {
  font-size: 1.8rem;
  margin-bottom: 1rem;
  font-weight: 800;
  line-height: 1.3;
}

.left-content p {
  font-size: 1.1rem;
  opacity: 0.88;
  line-height: 1.5;
}

.auth-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  background: #ffffff;
}

.form-container {
  width: 100%;
  max-width: 400px;
  padding: 2rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
}

.form-header h2 {
  font-size: 1.75rem;
  color: #0f172a;
  margin-bottom: 2rem;
  font-weight: 800;
  line-height: 1.3;
}

.auth-form {
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group input {
  width: 100%;
  padding: 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 1rem;
  transition: all 0.2s ease;
  background: #f8fafc;
  color: #0f172a;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
  background: white;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.error-message {
  color: #b91c1c;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  font-size: 0.9rem;
}

.submit-btn {
  width: 100%;
  padding: 1rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  background: #1d4ed8;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.24);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.form-footer {
  text-align: center;
  color: #64748b;
  font-size: 0.95rem;
}

.form-footer .link {
  color: #2563eb;
  text-decoration: none;
  font-weight: 700;
}

.form-footer .link:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .auth-container {
    flex-direction: column;
  }

  .auth-left {
    min-height: 40vh;
    padding: 2rem;
  }

  .illustration-circle {
    width: 180px;
    height: 180px;
  }

  .person-icon {
    font-size: 5rem;
  }

  .left-content h3 {
    font-size: 1.5rem;
  }

  .auth-right {
    padding: 2rem;
  }
}
</style>
