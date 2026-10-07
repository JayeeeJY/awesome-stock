import { defineStore } from 'pinia'
import { useBusinessStore } from './business'
import { request } from '@/api/owner'
export const useAuthStore = defineStore('auth', {
  state: () => ({ authenticated: false, initialized: false, checked: false, bootstrapError: '', user: null as null | {username: string; avatar?: string} }),
  actions: {
    async check() {
      const result = await request<{initialized: boolean; authenticated: boolean}>('/api/v1/owner/status')
      this.initialized = result.initialized; this.authenticated = result.authenticated; this.checked = true
      if (this.authenticated && !this.user) this.user = { username: '本地所有者' }
    },
    async login(username: string, password: string) {
      if (!this.initialized) { await request('/api/v1/owner/setup', 'POST', {username, password}); this.initialized = true }
      await request('/api/v1/auth/login', 'POST', {username, password})
      this.authenticated = true; this.user = {username}
    },
    async logout() {
      await request('/api/v1/auth/logout', 'POST', {})
      this.authenticated = false; this.user = null; useBusinessStore().reset()
    },
  },
})
