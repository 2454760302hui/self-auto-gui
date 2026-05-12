import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // 未登录：展示欢迎页 / 登录 / 注册
    { path: '/', component: () => import('../views/Welcome.vue') },
    { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
    { path: '/register', name: 'Register', component: () => import('../views/Register.vue') },
    // 已登录：应用页面
    {
      path: '/app',
      component: () => import('../views/Layout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/app/home' },
        { path: 'home', name: 'Home', component: () => import('../views/Home.vue') },
        { path: 'project/:id', name: 'Project', component: () => import('../views/ProjectDetail.vue') },
        { path: 'environments/:projectId', name: 'Environments', component: () => import('../views/Environments.vue') },
        { path: 'suites/:projectId', name: 'Suites', component: () => import('../views/Suites.vue') },
      ],
    },
    // 老路径兼容重定向
    { path: '/home', redirect: '/app/home' },
    { path: '/workspace', redirect: '/app/home' },
  ],
})

router.beforeEach((to) => {
  const isAuth = !!localStorage.getItem('poa_token')
  // 需要认证的页面 → 登录
  if (to.meta?.requiresAuth && !isAuth) return '/login'
  // 已登录用户访问公开页 → 工作台
  if (isAuth && (to.path === '/' || to.path === '/login' || to.path === '/register')) return '/app/home'
})

export default router