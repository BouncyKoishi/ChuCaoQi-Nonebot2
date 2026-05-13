import { useUserStore } from '@/stores/user'
import type { RouteRecordRaw } from 'vue-router'
import { createRouter, createWebHistory } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/warehouse'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/warehouse',
    name: 'Warehouse',
    component: () => import('@/views/Warehouse.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/farm',
    name: 'Farm',
    component: () => import('@/views/Farm.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/shop',
    name: 'Shop',
    component: () => import('@/views/Shop.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/gmarket',
    name: 'GMarket',
    component: () => import('@/views/GMarket.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: () => import('@/views/Statistics.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/lottery',
    name: 'Lottery',
    component: () => import('@/views/Lottery.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ability',
    name: 'Ability',
    component: () => import('@/views/Ability.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('@/views/About.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/docs',
    name: 'Docs',
    component: () => import('@/views/Docs.vue'),
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL || '/'),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    const sessionToken = localStorage.getItem('sessionToken')
    if (sessionToken) {
      try {
        const success = await userStore.verifySession()
        if (success) {
          next()
          return
        }
      } catch (error) {
        console.error('Session verification failed in router:', error)
        localStorage.removeItem('sessionToken')
      }
    }
    next('/login')
  } else {
    next()
  }
})


router.afterEach((to) => {
  if (to.path && to.path !== '/') {
    import('@/api/index').then(({ analyticsApi }) => {
      analyticsApi.recordPageview(to.path, (to.name as string) || '').catch(() => { })
    })
  }
})

export default router
