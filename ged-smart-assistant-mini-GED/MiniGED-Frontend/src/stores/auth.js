// On importe defineStore depuis Pinia (librairie de gestion d’état pour Vue)
import { defineStore } from "pinia";

// On importe le service d'authentification
// Ce service contient les appels API (login, register, refreshToken, logout, etc.)
import AuthService from "../services/auth";

// Création du store nommé "auth"
// "auth" est l'identifiant unique du store
const useAuthStore = defineStore("auth", {

  // STATE : données globales stockées dans le store
  state: () => ({

    // On initialise l'utilisateur avec la valeur stockée (localStorage par exemple)
    user: AuthService.getCurrentUser(),

    // Vérifie si l'utilisateur est déjà authentifié au chargement
    isAuthenticated: AuthService.isAuthenticated(),

    // Indique si une requête est en cours (utile pour afficher un loader)
    loading: false,

    // Contient les messages d’erreur éventuels
    error: null,

    // Stocke le timeout pour le refresh automatique du token
    refreshTokenTimeout: null
  }),

  // ACTIONS : méthodes qui modifient le state
  actions: {
    initializeAuth() {
      const accessToken = AuthService.getToken();
      if (!accessToken) {
        this.user = null;
        this.isAuthenticated = false;
        return;
      }

      this.user = AuthService.getCurrentUser();
      this.isAuthenticated = true;
      this.startRefreshTokenTimer(accessToken);
    },

    // Action pour enregistrer un nouvel utilisateur
    async register(userData) {

      // Active le mode loading
      this.loading = true;

      // Réinitialise les erreurs
      this.error = null;

      try {

        // Appel au service pour enregistrer l'utilisateur
        await AuthService.register(userData);

        // Si tout se passe bien, on retourne true
        return true;

      } catch (error) {

        // Si erreur API, on stocke le message d'erreur
        this.error = error.response?.data || "Erreur lors de l'inscription";

        // On relance l’erreur pour qu’elle puisse être gérée ailleurs
        throw error;

      } finally {

        // Désactive le loading dans tous les cas
        this.loading = false;
      }
    },

    // Action pour connecter un utilisateur
    async login(credentials) {

      // Active le loading
      this.loading = true;

      // Réinitialise les erreurs
      this.error = null;

      try {

        // Appel API login
        // On récupère l'utilisateur et le token d'accès
        const { user, accessToken } = await AuthService.login(credentials);

        // On stocke l'utilisateur dans le state
        this.user = user;

        // On marque l'utilisateur comme authentifié
        this.isAuthenticated = true;

        // On démarre le timer pour rafraîchir le token automatiquement
        this.startRefreshTokenTimer(accessToken);

      } catch (error) {

        // Stocke le message d'erreur retourné par le backend
        this.error = error.response?.data?.message || "Erreur de connexion";

        // Relance l’erreur
        throw error;

      } finally {

        // Désactive le loading
        this.loading = false;
      }
    },

    // Action pour rafraîchir le token d’accès
    async refreshToken() {

      try {

        // Appel API pour obtenir un nouveau token
        const { accessToken } = await AuthService.refreshToken();

        // Redémarre le timer avec le nouveau token
        this.startRefreshTokenTimer(accessToken);

      } catch (error) {

        // Si le refresh échoue (token expiré par exemple)
        // On déconnecte l'utilisateur
        this.logout();
      }
    },

    // Fonction qui démarre le timer de refresh automatique
    startRefreshTokenTimer(accessToken) {
      this.stopRefreshTokenTimer();

      // On récupère la partie payload du JWT (2ème partie séparée par ".")
      const jwtBase64 = accessToken.split('.')[1];

      // On décode le token (base64 → JSON)
      const jwtToken = JSON.parse(atob(jwtBase64));

      // On récupère la date d’expiration (exp est en secondes)
      const expires = new Date(jwtToken.exp * 1000);

      // Calcul du temps restant avant expiration
      // On retire 1 minute pour anticiper le refresh
      const timeout = Math.max(expires.getTime() - Date.now() - (60 * 1000), 0);

      // On programme l'appel automatique de refreshToken()
      this.refreshTokenTimeout = setTimeout(() => this.refreshToken(), timeout);
    },

    // Fonction pour arrêter le timer
    stopRefreshTokenTimer() {

      // Annule le setTimeout en cours
      clearTimeout(this.refreshTokenTimeout);
      this.refreshTokenTimeout = null;
    },

    // Action pour déconnecter l'utilisateur
    logout() {

      // Appel au service pour supprimer token / session
      AuthService.logout();

      // Réinitialise l'utilisateur
      this.user = null;

      // Marque comme non authentifié
      this.isAuthenticated = false;

      // Stoppe le timer de refresh
      this.stopRefreshTokenTimer();
    }
  }
});

// Export du store pour pouvoir l'utiliser dans les composants
export { useAuthStore };
