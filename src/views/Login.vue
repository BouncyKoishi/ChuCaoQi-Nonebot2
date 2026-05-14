<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>生草系统登录</h2>
        </div>
      </template>
      <el-form :model="loginForm" label-width="80px" @submit.prevent="handleLogin">
        <el-form-item label="QQ号">
          <el-autocomplete
            v-model="loginForm.qq"
            :fetch-suggestions="querySuggestions"
            placeholder="请输入QQ号"
            size="large"
            style="width: 100%"
            clearable
            @select="onQQSelect"
          >
            <template #default="{ item }">
              <div class="qq-suggestion">
                <span>{{ item.value }}</span>
                <el-icon
                  class="qq-suggestion-delete"
                  @click.stop="handleRemoveAccount(item.value)"
                >
                  <Close />
                </el-icon>
              </div>
            </template>
          </el-autocomplete>
        </el-form-item>
        <el-form-item label="Token">
          <el-input
            v-model="loginForm.token"
            placeholder="请在Bot中使用 !查看token 获取"
            type="password"
            show-password
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="rememberAccount">记住此账号</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" native-type="submit">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-tip">
        <el-text type="info" size="small">
          Token获取方式：在Bot中发送 !生成token
        </el-text>
      </div>
      <div class="docs-link">
        <router-link to="/docs">查看Bot指令文档 →</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { getSavedAccounts, getTokenByQQ, removeSavedAccount, saveAccount } from '@/utils'
import { Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const userStore = useUserStore()

const loginForm = ref({
  qq: '',
  token: ''
})

const loading = ref(false)
const rememberAccount = ref(true)
const savedAccounts = ref(getSavedAccounts())

onMounted(() => {
  if (savedAccounts.value.length > 0) {
    const lastQQ = localStorage.getItem('lastLoginQQ')
    if (lastQQ && savedAccounts.value.some(a => a.qq === lastQQ)) {
      loginForm.value.qq = lastQQ
      const token = getTokenByQQ(lastQQ)
      if (token) {
        loginForm.value.token = token
      }
    }
  }
})

const querySuggestions = (queryString: string, cb: (results: { value: string }[]) => void) => {
  const results = savedAccounts.value
    .filter(a => a.qq.includes(queryString))
    .map(a => ({ value: a.qq }))
  cb(results)
}

const onQQSelect = (item: { value: string }) => {
  const token = getTokenByQQ(item.value)
  if (token) {
    loginForm.value.token = token
  } else {
    loginForm.value.token = ''
  }
}

const handleRemoveAccount = async (qq: string) => {
  try {
    await ElMessageBox.confirm(
      `确定删除已保存的账号 ${qq} 吗？`,
      '删除账号',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    removeSavedAccount(qq)
    savedAccounts.value = getSavedAccounts()
    if (loginForm.value.qq === qq) {
      loginForm.value.token = ''
    }
    ElMessage.success(`已删除账号 ${qq}`)
  } catch {}
}

const handleLogin = async () => {
  if (!loginForm.value.qq) {
    ElMessage.warning('请输入QQ号')
    return
  }

  if (!/^\d+$/.test(loginForm.value.qq)) {
    ElMessage.warning('QQ号必须为数字')
    return
  }

  if (loginForm.value.qq.length < 5 || loginForm.value.qq.length > 12) {
    ElMessage.warning('QQ号长度必须在5-12位之间')
    return
  }

  loading.value = true
  try {
    await userStore.login(loginForm.value.qq, loginForm.value.token || undefined)

    if (rememberAccount.value) {
      saveAccount(loginForm.value.qq, loginForm.value.token || '')
      localStorage.setItem('lastLoginQQ', loginForm.value.qq)
      savedAccounts.value = getSavedAccounts()
    }

    ElMessage.success('登录成功')
    router.push('/warehouse')
  } catch (error: any) {
    const errorMessage = error.message || error.response?.data?.error || '登录失败，请稍后重试'
    ElMessage.error(errorMessage)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  max-width: 90%;
  margin: 0 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #333;
}

.qq-suggestion {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.qq-suggestion-delete {
  color: #909399;
  font-size: 14px;
  cursor: pointer;
  transition: color 0.2s;
}

.qq-suggestion-delete:hover {
  color: #f56c6c;
}

.login-tip {
  text-align: center;
  margin-top: 20px;
}

.docs-link {
  text-align: center;
  margin-top: 12px;
}

.docs-link a {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}

.docs-link a:hover {
  color: #764ba2;
  text-decoration: underline;
}
</style>
