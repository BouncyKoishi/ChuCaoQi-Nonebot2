export function formatNumber(num: number | string): string {
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return '0'
  return n.toLocaleString('zh-CN')
}

const SAVED_ACCOUNTS_KEY = 'savedAccounts'

export interface SavedAccount {
  qq: string
  token: string
}

export function getSavedAccounts(): SavedAccount[] {
  try {
    const raw = localStorage.getItem(SAVED_ACCOUNTS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function saveAccount(qq: string, token: string) {
  const accounts = getSavedAccounts()
  const idx = accounts.findIndex(a => a.qq === qq)
  if (idx >= 0) {
    accounts[idx].token = token
  } else {
    accounts.push({ qq, token })
  }
  localStorage.setItem(SAVED_ACCOUNTS_KEY, JSON.stringify(accounts))
}

export function removeSavedAccount(qq: string) {
  const accounts = getSavedAccounts().filter(a => a.qq !== qq)
  localStorage.setItem(SAVED_ACCOUNTS_KEY, JSON.stringify(accounts))
}

export function getTokenByQQ(qq: string): string | undefined {
  return getSavedAccounts().find(a => a.qq === qq)?.token
}
