import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '../api/client'
import type { User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref(localStorage.getItem('poa_token') || '')

  async function login(username: string, password: string) {
    const res: any = await http.post('/auth/login', { username, password })
    token.value = res.token
    user.value = res.user
    localStorage.setItem('poa_token', res.token)
    return res
  }

  async function register(username: string, email: string, password: string) {
    const res: any = await http.post('/auth/register', { username, email, password })
    token.value = res.token
    user.value = res.user
    localStorage.setItem('poa_token', res.token)
    return res
  }

  async function fetchMe() {
    try {
      user.value = await http.get('/auth/me')
    } catch { user.value = null }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('poa_token')
  }

  return { user, token, login, register, fetchMe, logout }
})