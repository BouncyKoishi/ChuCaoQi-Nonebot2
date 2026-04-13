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
          <el-input
            v-model="loginForm.qq"
            placeholder="请输入QQ号"
            size="large"
          />
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
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" native-type="submit">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-tip">
        <el-text type="info" size="small">
          Token获取方式：在Bot中发送 /生成token
        </el-text>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const userStore = useUserStore()

const loginForm = ref({
  qq: '',
  token: ''
})

const loading = ref(false)

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

.login-tip {
  text-align: center;
  margin-top: 20px;
}
</style>
