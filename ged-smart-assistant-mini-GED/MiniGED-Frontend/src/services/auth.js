import apiClient from "./api";
import userService from "./userService";
import { API_REFRESH_TOKEN_URL } from "../config/api";

class AuthService {
  async register(userData) {
    const response = await apiClient.post("/account/register", userData);
    return response.data;
  }

  async login(credentials) {
    const response = await apiClient.post("/account/login", credentials);

    if (response.data.accessToken && response.data.refreshToken) {
      // Stockage des deux tokens
      localStorage.setItem("token", response.data.accessToken);
      localStorage.setItem("refreshToken", response.data.refreshToken);

      // Récupération des infos utilisateur
      const user = await userService.getUserAuth();
      localStorage.setItem("user", JSON.stringify(user.data));

      return {
        user: user.data,
        accessToken: response.data.accessToken,
        refreshToken: response.data.refreshToken
      };
    }

    return null;
  }

  async refreshToken() {
    const refreshToken = localStorage.getItem("refreshToken");
    if (!refreshToken) throw new Error("Pas de refresh token");

    const response = await apiClient.post(API_REFRESH_TOKEN_URL, {
      refreshToken,
    });

    if (response.data.accessToken && response.data.refreshToken) {
      localStorage.setItem("token", response.data.accessToken);
      localStorage.setItem("refreshToken", response.data.refreshToken);
      return {
        accessToken: response.data.accessToken,
        refreshToken: response.data.refreshToken,
      };
    }

    throw new Error("Impossible de rafraîchir le token");
  }

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("user");
  }

  getCurrentUser() {
    const user = localStorage.getItem("user");
    return user ? JSON.parse(user) : null;
  }

  getToken() {
    return localStorage.getItem("token");
  }

  isAuthenticated() {
    return !!this.getToken();
  }
}

export default new AuthService();
