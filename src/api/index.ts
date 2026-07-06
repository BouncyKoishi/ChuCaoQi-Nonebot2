import type { GValue, Item, KusaField, UserInfo, WarehouseInfo } from '@/types'
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.PROD ? '/kusa/api' : '/api',
  timeout: 10000
})

api.interceptors.request.use(
  config => {
    const sessionToken = localStorage.getItem('sessionToken') || ''
    if (sessionToken) {
      config.headers['X-Session-Token'] = sessionToken
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  response => {
    // blob 响应直接返回，不走 JSON 解包（供图片等二进制下载使用）
    if (response.config.responseType === 'blob') {
      return response.data
    }

    const data = response.data

    if (data && typeof data === 'object') {
      if ('success' in data) {
        if (!data.success) {
          const error = new Error(data.error || '请求失败')
          error.response = response
          throw error
        }
        if ('data' in data) {
          return data.data
        }
      }
    }
    return data
  },
  error => {
    console.error('API Error:', error)
    console.error('Error response:', error.response)
    console.error('Error data:', error.response?.data)
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (qq: string, token?: string) => api.post<UserInfo>('/auth/login', { qq, token }),
  logout: () => {
    const sessionToken = localStorage.getItem('sessionToken')
    if (sessionToken) {
      api.post('/auth/logout', { sessionToken })
    }
    localStorage.removeItem('sessionToken')
    return Promise.resolve()
  },
  verifySession: () => {
    const sessionToken = localStorage.getItem('sessionToken')
    if (!sessionToken) return Promise.reject(new Error('No session token'))
    return api.post<UserInfo>('/auth/verify-session', { sessionToken })
  }
}

export const userApi = {
  getInfo: () => api.get<UserInfo>('/user/info'),
  updateName: (name: string) => api.post('/user/name', { name })
}

export const warehouseApi = {
  getWarehouse: () => api.get<WarehouseInfo>('/warehouse'),
  getItemsByType: (type: string) => api.get<Item[]>(`/warehouse/items/${type}`),
  updateTitle: (title: string) => api.post('/warehouse/title', { title }),
  updateName: (name: string) => api.post('/warehouse/name', { name }),
  getDailyProduction: () => api.get<any>('/warehouse/daily-production'),
  getUserStats: () => api.get<any>('/warehouse/stats/user'),
  getKusaRank: (sortBy?: 'kusa' | 'advKusa') => api.get<any[]>('/rank/kusa', { params: { sort_by: sortBy } }),
  getTotalAdvKusaRank: (limit?: number, levelMax?: number) => api.get<any[]>('/rank/total-adv-kusa', { params: { limit, level_max: levelMax } }),
  getGrassStatsPersonal: (period: string) => api.get<any>('/warehouse/stats/grass/personal', { params: { period } }),
  getGrassStatsTotal: (period: string) => api.get<any>('/warehouse/stats/grass/total', { params: { period } }),
  getGMarketStats: () => api.get<any>('/warehouse/stats/gmarket'),
  getGMarketRecords: (page: number, pageSize: number) => api.get<any>('/warehouse/stats/gmarket/records', { params: { page, pageSize } }),
  compressKusa: (amount: number) => api.post<{ success: boolean; message: string; advKusaGained?: number; kusaUsed?: number }>('/warehouse/compress-kusa', { amount })
}

export const itemApi = {
  toggleItem: (itemName: string, allowUse: boolean) => api.post('/item/toggle', { itemName, allowUse }),
  getItemAmount: (itemName: string) => api.get('/item/amount', { params: { item_name: itemName } }),
  composeTicket: (target: string, amount: number) => api.post<{ success: boolean; message: string }>('/item/compose-ticket', { target, amount })
}

export const farmApi = {
  getField: () => api.get<KusaField>('/farm'),
  plantKusa: (kusaType: string, overload: boolean = false) => api.post<{ success: boolean; message: string; kusaType: string; kusaFinishTs: number; growTime: number }>('/farm/plant', { kusaType, overload }),
  weedKusa: () => api.post<{ success: boolean; kusa: number; advKusa: number; kusaType: string }>('/farm/weed'),
  getHistory: () => api.get<any[]>('/farm/history'),
  getAvailableKusaTypes: () => api.get<any[]>('/farm/available-kusa-types'),
  releaseSpareCapacity: () => api.post<{ success: boolean; message: string; newCapacity: number }>('/farm/release-spare-capacity'),
  checkOverloadMagic: () => api.get<{ hasOverloadMagic: boolean }>('/farm/overload-magic')
}

export const shopApi = {
  getShopItems: () => api.get<Item[]>('/shop/items'),
  buyItem: (itemName: string, amount: number, useAdvKusa: boolean) =>
    api.post('/shop/buy', { itemName, amount, useAdvKusa }),
  sellItem: (itemName: string, amount: number, useAdvKusa: boolean) =>
    api.post('/shop/sell', { itemName, amount, useAdvKusa })
}

export const gMarketApi = {
  getGValue: () => api.get<GValue>('/gmarket'),
  getGValueHistory: () => api.get<{ history: any[] }>('/gmarket/history'),
  buyG: (gType: string, amount: number) =>
    api.post('/gmarket/buy', { gType, amount }),
  sellG: (gType: string, amount: number) =>
    api.post('/gmarket/sell', { gType, amount })
}

export const lotteryApi = {
  getPools: () => api.get<string[]>('/lottery/pools'),
  getStorage: (rare?: string, pool?: string) =>
    api.get('/lottery/storage', { params: { rare, pool } }),
  getItem: (itemName: string) =>
    api.get(`/lottery/item/${encodeURIComponent(itemName)}`),
  searchItems: (keyword: string, page?: number, pageSize?: number) =>
    api.get('/lottery/search', { params: { keyword, page, pageSize } }),
  getMyItems: (rare?: string, pool?: string) => api.get('/lottery/my-items', { params: { rare, pool } }),
  addItem: (itemName: string, rareRank: number, pool: string, detail?: string) =>
    api.post('/lottery/add', { itemName, rareRank, pool, detail }),
  updateItem: (itemName: string, detail: string) =>
    api.post('/lottery/update', { itemName, detail }),
  deleteItem: (itemName: string) =>
    api.delete(`/lottery/item/${encodeURIComponent(itemName)}`),
  draw: (pool?: string) =>
    api.post('/lottery/draw', { pool }),
  drawTen: (baseLevel?: number, pool?: string) =>
    api.post('/lottery/draw-ten', { baseLevel, pool })
}

export const vipApi = {
  upgrade: () => api.post<{ success: boolean; message: string; newLevel: number; costKusa: number }>('/warehouse/vip/upgrade'),
  advancedUpgrade: () => api.post<{ success: boolean; message: string; newLevel: number; costAdvPoint: number }>('/warehouse/vip/advanced-upgrade')
}

export const donateApi = {
  getRecords: () => api.get<{ amount: number; date: string; source: string; remark: string | null }[]>('/donate/records'),
  getTotal: () => api.get<{ total: number }>('/donate/total')
}

export const analyticsApi = {
  recordPageview: (path: string, pageName: string) =>
    api.post('/analytics/pageview', { path, pageName }),
  getStats: (days?: number) =>
    api.get('/analytics/stats', { params: { days } })
}

export const spellcardApi = {
  getDiceSeed: () => api.get<{ seed: number }>('/spellcard/dice-seed'),
}

export const adminApi = {
  // 用户管理
  getUsers: (page: number, pageSize: number, searchId?: string, searchName?: string) =>
    api.get<{ list: any[]; total: number; page: number; pageSize: number }>('/admin/users', {
      params: { page, pageSize, searchId, searchName }
    }),
  getUserWarehouse: (userId: number) =>
    api.get<any>(`/admin/users/${userId}/warehouse`),
  updateUserName: (userId: number, name: string) =>
    api.post(`/admin/users/${userId}/name`, { name }),
  giveUserTitle: (userId: number, title: string) =>
    api.post(`/admin/users/${userId}/title`, { title }),
  setUserDonation: (userId: number, amount: number, source?: string) =>
    api.post<any>(`/admin/users/${userId}/donation`, { amount, source }),
  getUserDonations: (userId: number) =>
    api.get<{ total: number; records: { id: number; amount: number; donateDate: string; source: string }[] }>(`/admin/users/${userId}/donations`),
  deleteUserDonation: (userId: number, recordId: number) =>
    api.delete(`/admin/users/${userId}/donations/${recordId}`),
  getUserTitles: (userId: number) =>
    api.get<{ currentTitle: string | null; titles: { name: string; detail: string; amount: number; inUse: boolean }[] }>(`/admin/users/${userId}/titles`),
  getTitleOwners: (titleName: string) =>
    api.get<{ owners: any[] }>(`/admin/titles/${encodeURIComponent(titleName)}/owners`),
  getUserChatPermission: (userId: number) =>
    api.get<{ success: boolean; data: any }>(`/admin/users/${userId}/chat-permission`),
  updateUserChatPermission: (
    userId: number,
    payload: { allowPrivate: boolean; allowRole: boolean; allowAdvancedModel: boolean; dailyLimitMode: string }
  ) => api.post(`/admin/users/${userId}/chat-permission`, payload),
  generateUserWebToken: (userId: number) =>
    api.post<{ success: boolean; token?: string; error?: string }>(`/admin/users/${userId}/web-token`),
  generateFriendCode: (userId: number) =>
    api.post<{ success: boolean; code?: string; qq?: string; error?: string }>(`/admin/users/${userId}/friend-code`),
  getAccountMarks: (userId: number) =>
    api.get<{ success: boolean; relatedUserId?: number | null; relatedUser?: any; isRobot?: boolean; error?: string }>(`/admin/users/${userId}/account-marks`),
  updateAccountMarks: (userId: number, data: { relatedUserId: number | null; isRobot: boolean }) =>
    api.post(`/admin/users/${userId}/account-marks`, data),

  // 称号管理
  getTitles: () => api.get<any[]>('/admin/titles'),
  createTitle: (name: string, detail?: string) =>
    api.post('/admin/titles', { name, detail }),
  deleteTitle: (titleName: string) =>
    api.delete(`/admin/titles/${encodeURIComponent(titleName)}`),

  // 自定义排行榜
  generateCustomRank: (payload: {
    dimension: 'kusa' | 'advKusa' | 'totalAdvKusa' | 'item'
    limit?: number
    levelMax?: number
    showInactive?: boolean
    showSubaccount?: boolean
    itemName?: string
  }) => api.post<{ success: boolean; data?: any[]; columns?: string[]; error?: string }>('/admin/rank/custom', payload),
  getItemsList: () => api.get<{ name: string; type: string }[]>('/admin/items/list'),

  // 图片审核
  getPicCategories: () => api.get<{ key: string; name: string }[]>('/admin/pic-review/categories'),
  getPendingPics: () => api.get<{ filename: string; size: number; sizeStr: string; uploaderQQ: string | null }[]>('/admin/pic-review/pending'),
  fetchPicImage: (filename: string) =>
    api.get<Blob>(`/admin/pic-review/image/${encodeURIComponent(filename)}`, { responseType: 'blob' }),
  classifyPic: (filename: string, category: string) =>
    api.post('/admin/pic-review/classify', { filename, category }),
  savePic: (filename: string) =>
    api.post('/admin/pic-review/save', { filename }),
  skipPic: (filename: string) =>
    api.post('/admin/pic-review/skip', { filename }),
  deletePic: (filename: string) =>
    api.delete(`/admin/pic-review/image/${encodeURIComponent(filename)}`)
}

export { farmWebSocket } from './websocket'

export default api
