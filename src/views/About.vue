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
                <el-card shadow="hover" class="link-card" @click="openLink(link.url, link.internal)">
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

        <el-tab-pane v-if="isAdmin" label="统计" name="stats">
          <div class="section">
            <div class="stats-controls">
              <el-select v-model="statsDays" size="small" style="width: 120px" @change="fetchStats">
                <el-option :value="7" label="最近 7 天" />
                <el-option :value="30" label="最近 30 天" />
                <el-option :value="90" label="最近 90 天" />
              </el-select>
              <el-button size="small" @click="fetchStats" :loading="statsLoading">刷新</el-button>
            </div>

            <div v-if="statsData" class="stats-content">
              <el-row :gutter="16" style="margin-bottom: 16px">
                <el-col :span="8">
                  <el-statistic title="总访问量 (PV)" :value="statsData.totalPv" />
                </el-col>
                <el-col :span="8">
                  <el-statistic title="独立用户 (UV)" :value="statsData.totalUv" />
                </el-col>
                <el-col :span="8">
                  <el-statistic title="统计天数" :value="statsData.days" />
                </el-col>
              </el-row>

              <h4>页面访问排行</h4>
              <el-table :data="statsData.pages" size="small" style="margin-bottom: 20px">
                <el-table-column prop="path" label="路径" />
                <el-table-column prop="pageName" label="页面" width="120" />
                <el-table-column prop="pv" label="PV" width="80" />
              </el-table>

              <h4>每日趋势</h4>
              <div ref="chartRef" style="height: 300px; width: 100%"></div>
            </div>
            <el-empty v-else-if="!statsLoading" description="暂无统计数据" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { analyticsApi, donateApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { ChatDotRound, Collection, Connection, Document, Present } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('links')
const donateRecords = ref<{ amount: number; date: string; source: string; remark: string | null }[]>([])
const donateTotal = ref(0)
const currentPage = ref(1)
const pageSize = 10

const isAdmin = computed(() => userStore.isLoggedIn && userStore.userInfo?.isSuperAdmin)

const statsDays = ref(30)
const statsLoading = ref(false)
const statsData = ref<{
  totalPv: number
  totalUv: number
  days: number
  daily: { date: string; pv: number; uv: number }[]
  pages: { path: string; pageName: string | null; pv: number }[]
} | null>(null)

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const paginatedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return donateRecords.value.slice(start, start + pageSize)
})

const links = [
  { 
    title: '代码仓库', 
    desc: 'GitHub 开源仓库，查看源码和提交 Issue',
    url: 'https://github.com/BouncyKoishi/ChuCaoQi-Nonebot2',
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
    title: '指令文档', 
    desc: 'Bot端指令使用文档',
    url: '/docs',
    icon: Collection,
    color: '#67c23a',
    internal: true
  },
  { 
    title: 'QQ主群', 
    desc: '加入主群 738721109，交流讨论',
    url: 'https://qm.qq.com/cgi-bin/qm/qr?k=tOFecPJ9Dva9ovRtWEVa9ugOAczkRUn8&jump_from=webapi&authKey=kzi/sfxXgf4NJDnXWFTdVw79Lk9llWNvwd7Loz+onqK4/X8x5KQXSMJFvvwTuOjA',
    icon: ChatDotRound,
    color: '#12b7f5'
  }
]

const openLink = (url: string, internal?: boolean) => {
  if (internal) {
    router.push(url)
  } else {
    window.open(url, '_blank')
  }
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

const updateChart = () => {
  if (!chartInstance || !statsData.value) return
  const daily = statsData.value.daily
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['PV', 'UV'], top: 0 },
    grid: { top: 30, right: 50, bottom: 30, left: 50 },
    xAxis: { type: 'category', data: daily.map(d => d.date.slice(5)), boundaryGap: false },
    yAxis: [
      { type: 'value', name: 'PV', minInterval: 1, position: 'left' },
      { type: 'value', name: 'UV', minInterval: 1, position: 'right' }
    ],
    series: [
      { name: 'PV', type: 'line', yAxisIndex: 0, data: daily.map(d => d.pv), smooth: true, itemStyle: { color: '#409eff' }, areaStyle: { color: 'rgba(64,158,255,0.1)' } },
      { name: 'UV', type: 'line', yAxisIndex: 1, data: daily.map(d => d.uv), smooth: true, itemStyle: { color: '#67c23a' }, areaStyle: { color: 'rgba(103,194,58,0.1)' } }
    ]
  })
}

const initChart = async () => {
  await nextTick()
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const fetchStats = async () => {
  statsLoading.value = true
  try {
    const data = await analyticsApi.getStats(statsDays.value)
    statsData.value = data as any
    await nextTick()
    if (chartInstance) {
      chartInstance.resize()
      updateChart()
    } else {
      await initChart()
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  } finally {
    statsLoading.value = false
  }
}

watch(activeTab, async (val) => {
  if (val === 'stats' && isAdmin.value) {
    await fetchStats()
  }
})

onMounted(() => {
  fetchDonateRecords()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
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

.stats-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  align-items: center;
}

.stats-content h4 {
  margin: 16px 0 8px;
  color: #333;
  font-size: 14px;
}
</style>
