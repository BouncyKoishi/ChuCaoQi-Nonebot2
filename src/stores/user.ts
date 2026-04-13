import api from '@/api'
import type { UserInfo } from '@/types'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const isLoggedIn = ref(false)
  const userInfo = ref<UserInfo | null>(null)
  const userId = ref<number>(0)

  const login = async (qq: string, token?: string) => {
    try {
      const response = await api.post('/auth/login', { qq, token })
      isLoggedIn.value = true
      userInfo.value = response
      userId.value = response.userId
      localStorage.setItem('sessionToken', response.sessionToken)
      localStorage.setItem('userId', String(response.userId))
      return true
    } catch (error: any) {
      console.error('Login failed:', error)
      isLoggedIn.value = false
      userInfo.value = null
      userId.value = 0
      localStorage.removeItem('sessionToken')
      localStorage.removeItem('userId')
      throw error
    }
  }

  const verifySession = async () => {
    const sessionToken = localStorage.getItem('sessionToken')
    if (!sessionToken) {
      return false
    }
    try {
      const response = await api.post('/auth/verify-session', { sessionToken })
      isLoggedIn.value = true
      userInfo.value = response
      userId.value = response.userId
      localStorage.setItem('userId', String(response.userId))
      return true
    } catch (error) {
      console.error('Session verification failed:', error)
      isLoggedIn.value = false
      userInfo.value = null
      userId.value = 0
      localStorage.removeItem('sessionToken')
      localStorage.removeItem('userId')
      return false
    }
  }

  const logout = async () => {
    const sessionToken = localStorage.getItem('sessionToken')
    if (sessionToken) {
      try {
        await api.post('/auth/logout', { sessionToken })
      } catch (error) {
        console.error('Logout API failed:', error)
      }
    }
    isLoggedIn.value = false
    userInfo.value = null
    userId.value = 0
    localStorage.removeItem('sessionToken')
    localStorage.removeItem('userId')
  }

  const fetchUserInfo = async () => {
    try {
      const response = await api.get('/user/info')
      userInfo.value = response.data
      return response.data
    } catch (error) {
      console.error('Fetch user info failed:', error)
      return null
    }
  }

  return {
    isLoggedIn,
    userInfo,
    userId,
    login,
    verifySession,
    logout,
    fetchUserInfo
  }
})
