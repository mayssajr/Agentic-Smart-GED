import apiClient from "./api";

class UserService {
  async getUserAuth() {
    try {
      const response = await apiClient.get("account/me");
      return response;
    } catch (error) {
      console.error(
        "Erreur lors de la récupération des données utilisateur :",
        error
      );
      throw error;
    }
  }
}

export default new UserService();
