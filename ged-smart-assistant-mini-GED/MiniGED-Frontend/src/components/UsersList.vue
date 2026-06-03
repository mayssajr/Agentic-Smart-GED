<template>
  <div class="p-6">
    <h2 class="text-2xl font-bold mb-6 text-gray-800">
      Gestion des utilisateurs
    </h2>

    <!-- Search and add new user controls -->
    <div class="flex justify-between mb-6">
      <div class="relative w-64">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="Recherche des utilisateurs..."
          @input="filterUsers"
          class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button class="absolute right-3 top-2 text-gray-500">
          <i class="fas fa-search"></i>
        </button>
      </div>
      <!-- <button 
                @click="openAddUserModal"

                class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition duration-200"

            >
                Add New User
            </button> -->
    </div>

    <!-- Users table -->
    <div class="overflow-x-auto bg-white rounded-lg shadow">
      <table
        v-if="filteredUsers.length > 0"
        class="min-w-full divide-y divide-gray-200"
      >
        <thead class="bg-gray-50">
          <tr>
            <th
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Nom d'utilisateur
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Nom complet
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Email
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Rôle
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Numéro de téléphone
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="user in filteredUsers"
            :key="user.id"
            class="hover:bg-gray-50"
          >
            <td class="px-6 py-4 whitespace-nowrap">{{ user.username }}</td>
            <td class="px-6 py-4 whitespace-nowrap">{{ user.fullName }}</td>
            <td class="px-6 py-4 whitespace-nowrap">{{ user.email }}</td>
            <td class="px-6 py-4 whitespace-nowrap">{{ user.role }}</td>
            <td class="px-6 py-4 whitespace-nowrap">{{ user.phoneNumber }}</td>
            <td class="px-6 py-4 whitespace-nowrap space-x-2">
              <button
                @click="OpenUserDetails(user)"
                class="text-blue-600 hover:text-blue-900"
              >
                <i class="fas fa-eye size-5"></i>
              </button>
              <button
                @click="editUser(user)"
                class="text-amber-600 hover:text-amber-900"
              >
                <i class="fas fa-pen-to-square size-5"></i>
              </button>
              <button
                @click="confirmDelete(user)"
                class="text-red-600 hover:text-red-900"
              >
                <i class="fas fa-trash-can size-5"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="py-10 text-center text-gray-500">
        Aucun utilisateur trouvé
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import BaseApiService from "../services/ApiService";
import { useRoute, useRouter } from "vue-router";
const route = useRoute();

const router = useRouter();

// Sample data - replace with your actual data source

const users = ref([
  {
    id: 1,
    username: "johndoe",
    fullName: "John Doe",
    email: "john@example.com",
    role: "Admin",
    phoneNumber: "555-1234",
  },
]);
const searchQuery = ref("");
const filteredUsers = ref([]);

onMounted(() => {
  // Initialize filtered users with all users
  loadUsers();
  filteredUsers.value = [...users.value];
});

const loadUsers = () => {
  BaseApiService("/user")
    .list()
    .then((response) => {
      users.value = response.data;
      filteredUsers.value = [...users.value];
    })
    .catch((error) => {
      console.error("Error fetching users:", error);
    });
};

const filterUsers = () => {
  // Filter users based on search query
  const query = searchQuery.value.toLowerCase();
  filteredUsers.value = users.value.filter(
    (user) =>
      user.username.toLowerCase().includes(query) ||
      user.fullName.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      user.role.toLowerCase().includes(query),
  );
};

const OpenUserDetails = (user) => {
  // Implement user details viewing functionality
  router.push(`user/${user.id}`);
};
</script>
