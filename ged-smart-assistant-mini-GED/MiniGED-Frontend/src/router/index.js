import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import RegisterView from "../views/RegisterView.vue";
import DashboardView from "../views/DashboardView.vue";
import DocumentsList from "../components/DocumentsList.vue";
import PresentationView from "../views/PresentationView.vue";
import UsersList from "../components/UsersList.vue";
import DocumentDetails from "../components/DocumentDetails.vue";
import { useAuthStore } from "../stores/auth";
import UserDetails from "../components/UserDetails.vue";
import HomeView from "../components/HomeView.vue";
import ProfileView from "../views/ProfileView.vue";
import TasksView from "../views/TasksView.vue";
import { useUiStore } from "../stores/ui";

const routes = [
  { path: "/login", component: LoginView },
  { path: "/register", component: RegisterView },
  {
    path: "",
    component: DashboardView,
    children: [
      { path: "", component: HomeView },
      { path: "documents", component: DocumentsList },
      { path: "document/:id", component: DocumentDetails },
      { path: "users", component: UsersList },
      { path: "user/:id", component: UserDetails },
      { path: "profile", component: ProfileView },
      { path: "tasks", component: TasksView },
      {
        path: '/recruitment',
        name: 'Recruitment',
        component: () => import('../views/RecruitmentView.vue'),
        meta: { requiresAuth: true }
      }
    ],
  },
  {
    path: "/presentation",
    component: PresentationView,
  },
  { path: "/", redirect: "/login" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();

  if (
    !authStore.isAuthenticated &&
    to.path !== "/login" &&
    to.path !== "/register"
  ) {
    // Save the full path user was trying to access
    authStore.returnUrl = to.fullPath;
    next("/login");
  } else if (
    (to.path === "/login" || to.path === "/register") &&
    authStore.isAuthenticated
  ) {
    next("/");
  } else {
    next();
  }
});

router.afterEach((to) => {
  const uiStore = useUiStore();
  const pageMap = {
    "/login": "Connexion",
    "/register": "Inscription",
    "/presentation": "Présentation",
    "/": "Accueil",
    "/documents": "Documents",
    "/users": "Utilisateurs",
    "/user/": "Utilisateur",
    "/document/": "Document",
  };
  let page = "Accueil";
  if (to.path in pageMap) {
    page = pageMap[to.path];
  } else {
    for (const [key, value] of Object.entries(pageMap)) {
      if (to.path.startsWith(key)) {
        page = value;
        break;
      }
    }
  }
  uiStore.setPage(page);
});

export default router;
