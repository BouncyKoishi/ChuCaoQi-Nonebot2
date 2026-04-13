<template>
  <div class="about-container">
    <el-card class="about-card">
      <template #header>
        <div class="card-header">
          <h2>关于</h2>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="相关链接" name="links">
          <div class="section">
            <el-row :gutter="16">
              <el-col :xs="24" :sm="12" v-for="link in links" :key="link.title">
                <el-card shadow="hover" class="link-card" @click="openLink(link.url)">
                  <div class="link-content">
                    <el-icon :size="24" :color="link.color">
                      <component :is="link.icon" />
                    </el-icon>
                    <div class="link-info">
                      <h4>{{ link.title }}</h4>
                      <p>{{ link.desc }}</p>
                    </div>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>

        <el-tab-pane label="投喂除草器" name="support">
          <div class="section">
            <h3>支持方式</h3>
            <el-row :gutter="16">
              <el-col :xs="24" :sm="12">
                <el-card shadow="hover" class="support-card" @click="openLink('https://afdian.com/a/chu-chu')">
                  <div class="support-content">
                    <el-icon :size="32" color="#ff6b6b"><Present /></el-icon>
                    <div class="support-info">
                      <h4>爱发电</h4>
                      <p>投喂留言请注明QQ号</p>
                    </div>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-card class="support-card">
                  <div class="support-content">
                    <el-icon :size="32" color="#12b7f5"><ChatDotRound /></el-icon>
                    <div class="support-info">
                      <h4>QQ红包</h4>
                      <p>主群内私聊作者发送红包</p>
                    </div>
                  </div>
                </el-card>
              </el-col>
            </el-row>

            <el-divider />

            <h3>专有称号</h3>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="猫粮供应商">
                大额投喂用户可获得专属称号
              </el-descriptions-item>
              <el-descriptions-item label="投喂者">
                累计投喂满20元可获得专属称号
              </el-descriptions-item>
              <el-descriptions-item label="疯狂信息员">
                爱发电"疯狂信息员"方案（￥50）可获得专属称号
              </el-descriptions-item>
            </el-descriptions>
            <p class="donate-thanks">任意金额投喂均可在 !仓库 页面得到除除的感谢！</p>

            <el-divider />

            <h3>我的投喂记录</h3>
            <div v-if="paginatedRecords.length > 0">
              <el-table :data="paginatedRecords" style="width: 100%">
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column prop="amount" label="金额" width="100">
                  <template #default="scope">
                    ￥{{ scope.row.amount.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="source" label="来源" width="100" />
                <el-table-column prop="remark" label="备注" />
              </el-table>
              <el-pagination
                v-if="donateRecords.length > pageSize"
                layout="prev, pager, next"
                :total="donateRecords.length"
                :page-size="pageSize"
                :current-page="currentPage"
                @current-change="handlePageChange"
                style="margin-top: 16px; text-align: center"
              />
              <div class="donate-total">
                累计投喂：<span class="total-amount">￥{{ donateTotal.toFixed(2) }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无投喂记录" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { donateApi } from '@/api'
import { ChatDotRound, Collection, Connection, Document, Present } from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'

const activeTab = ref('links')
const donateRecords = ref<{ amount: number; date: string; source: string; remark: string | null }[]>([])
const donateTotal = ref(0)
const currentPage = ref(1)
const pageSize = 10

const paginatedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return donateRecords.value.slice(start, start + pageSize)
})

const links = [
  { 
    title: '代码仓库', 
    desc: 'GitHub 开源仓库，查看源码和提交 Issue',
    url: 'https://github.com/BouncyKoishi/ChuCaoQi-Bot',
    icon: Connection,
    color: '#333'
  },
  { 
    title: '简明攻略', 
    desc: '生草系统使用攻略，快速上手',
    url: 'https://www.bilibili.com/opus/1029642903728685075',
    icon: Document,
    color: '#00a1d6'
  },
  { 
    title: '指令文档(杂项)', 
    desc: 'Bot端指令使用文档',
    url: 'https://rinkastone.com/2024/05/13/archives/409',
    icon: Collection,
    color: '#67c23a'
  },
  { 
    title: '指令文档(抽奖)', 
    desc: 'Bot端抽奖系统使用文档',
    url: 'https://rinkastone.com/2024/11/27/archives/429',
    icon: Present,
    color: '#e6a23c'
  },
  { 
    title: 'QQ主群', 
    desc: '加入主群 738721109，交流讨论',
    url: 'https://qm.qq.com/cgi-bin/qm/qr?k=tOFecPJ9Dva9ovRtWEVa9ugOAczkRUn8&jump_from=webapi&authKey=kzi/sfxXgf4NJDnXWFTdVw79Lk9llWNvwd7Loz+onqK4/X8x5KQXSMJFvvwTuOjA',
    icon: ChatDotRound,
    color: '#12b7f5'
  }
]

const openLink = (url: string) => {
  window.open(url, '_blank')
}

const handlePageChange = (page: number) => {
  currentPage.value = page
}

const fetchDonateRecords = async () => {
  try {
    const records = await donateApi.getRecords()
    donateRecords.value = (records || []).reverse()
    
    const totalData = await donateApi.getTotal()
    donateTotal.value = totalData?.total || 0
  } catch (error) {
    console.error('获取投喂记录失败:', error)
  }
}

onMounted(() => {
  fetchDonateRecords()
})
</script>

<style scoped>
.about-container {
  max-width: 800px;
  margin: 0 auto;
}

.about-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card-header h2 {
  margin: 0;
  color: #333;
}

.section h3 {
  margin-bottom: 16px;
  color: #333;
  font-size: 16px;
}

.link-card {
  cursor: pointer;
  margin-bottom: 16px;
  transition: transform 0.2s;
}

.link-card:hover {
  transform: translateY(-2px);
}

.link-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.link-info h4 {
  margin: 0 0 4px;
  color: #333;
  font-size: 15px;
}

.link-info p {
  margin: 0;
  color: #909399;
  font-size: 13px;
  line-height: 1.4;
}

.support-card {
  cursor: pointer;
  margin-bottom: 16px;
  transition: transform 0.2s;
}

.support-card:hover {
  transform: translateY(-2px);
}

.support-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.support-info h4 {
  margin: 0 0 4px;
  color: #333;
}

.support-info p {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.donate-thanks {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
}

.donate-total {
  margin-top: 16px;
  text-align: right;
  color: #606266;
}

.total-amount {
  color: #f56c6c;
  font-weight: bold;
  font-size: 18px;
}
</style>
