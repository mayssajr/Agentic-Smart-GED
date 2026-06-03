// On importe Axios (bibliothèque pour faire des requêtes HTTP)
import axios from "axios";

// On importe le service d'authentification
// Il permet de récupérer le token ou de faire logout
import AuthService from "./auth";
import { API_BASE_URL } from "../config/api";

// Création d’une instance personnalisée d’Axios
// Cela permet d’avoir une configuration centralisée
const apiClient = axios.create({

  // URL de base utilisée pour toutes les requêtes
  baseURL: API_BASE_URL,

  // Headers envoyés avec chaque requête
  headers: {

    // Indique que les données envoyées sont en JSON
    "Content-Type": "application/json",

  },
});


// ===============================
// INTERCEPTEUR DE REQUÊTE
// ===============================

// Intercepte chaque requête AVANT qu'elle soit envoyée au serveur
apiClient.interceptors.request.use(

  // Fonction exécutée avant l’envoi de la requête
  (config) => {

    // On récupère le token JWT depuis AuthService
    const token = AuthService.getToken();

    // Si un token existe
    if (token) {

      // On ajoute le token dans le header Authorization
      // Format standard : "Bearer <token>"
      config.headers.Authorization = `Bearer ${token}`;
    }

    // On retourne la configuration modifiée
    return config;
  },

  // Gestion des erreurs avant l’envoi
  (error) => {

    // On propage l’erreur
    return Promise.reject(error);
  }
);


// ===============================
// INTERCEPTEUR DE RÉPONSE
// ===============================

// Intercepte chaque réponse après réception du serveur
apiClient.interceptors.response.use(

  // Si la réponse est correcte (status 2xx)
  (response) => {

    // On retourne simplement la réponse
    return response;
  },

  // Si la réponse contient une erreur
  (error) => {

    // Si le serveur renvoie une erreur 401 (Non autorisé)
    if (error.response?.status === 401) {

      // Cela signifie généralement :
      // - Token expiré
      // - Token invalide

      // On déconnecte l’utilisateur
      AuthService.logout();

      // On redirige vers la page login
      window.location.href = "/login";
    }

    // On propage l’erreur pour qu’elle soit gérée ailleurs si besoin
    return Promise.reject(error);
  }
);


// On exporte l’instance personnalisée
// Elle sera utilisée dans tous les services API
export default apiClient
