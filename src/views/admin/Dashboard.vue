<template>
  <div class="dashboard">
    <!-- 页面访问统计 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-header">
          <span class="section-title">页面访问统计</span>
          <div class="stats-controls">
            <el-select v-model="statsDays" size="small" style="width: 130px" @change="fetchStats">
              <el-option :value="1" label="最近 1 天" />
              <el-option :value="7" label="最近 7 天" />
              <el-option :value="30" label="最近 30 天" />
              <el-option :value="90" label="最近 90 天" />
            </el-select>
            <el-button size="small" @click="fetchStats" :loading="statsLoading">刷新</el-button>
          </div>
        </div>
      </template>

      <div v-loading="statsLoading">
        <div v-if="statsData" class="stats-content">
          <el-row :gutter="16" style="margin-bottom: 16px">
            <el-col :xs="24" :sm="8">
              <el-statistic title="总访问量 (PV)" :value="statsData.totalPv" />
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-statistic title="独立用户 (UV)" :value="statsData.totalUv" />
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-statistic title="统计天数" :value="statsData.days" />
            </el-col>
          </el-row>

          <h4>页面访问排行</h4>
          <el-table :data="statsData.pages" size="small" style="margin-bottom: 16px">
            <el-table-column prop="path" label="路径" min-width="150" />
            <el-table-column prop="pageName" label="页面" width="120">
              <template #default="{ row }">
                {{ row.pageName || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="pv" label="PV" width="80" />
          </el-table>

          <h4>每日趋势</h4>
          <div ref="chartRef" style="height: 300px; width: 100%"></div>
        </div>
        <el-empty v-else-if="!statsLoading" description="暂无统计数据" />
      </div>
    </el-card>

    <!-- 自定义排行榜生成器 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-header">
          <span class="section-title">自定义排行榜生成器</span>
        </div>
      </template>

      <el-form :inline="true" size="small" class="rank-form">
        <el-form-item label="排序维度">
          <el-select v-model="rankForm.dimension" style="width: 140px">
            <el-option label="当前草数" value="kusa" />
            <el-option label="当前草精数" value="advKusa" />
            <el-option label="累计草精" value="totalAdvKusa" />
            <el-option label="单次生草打分" value="kusaOnce" />
            <el-option label="单次草精打分" value="advKusaOnce" />
            <el-option label="物品持有量" value="item" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="rankForm.dimension === 'item'" label="物品">
          <el-select
            v-model="rankForm.itemName"
            filterable
            placeholder="选择物品"
            style="width: 220px"
          >
            <el-option
              v-for="it in itemsList"
              :key="it.name"
              :label="`${it.name} (${it.type})`"
              :value="it.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="前N名">
          <el-input-number v-model="rankForm.limit" :min="1" :max="500" />
        </el-form-item>

        <el-form-item label="最大等级">
          <el-input-number v-model="rankForm.levelMax" :min="1" :max="10" />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="rankForm.showInactive">显示不活跃用户</el-checkbox>
          <el-checkbox v-model="rankForm.showSubaccount">显示小号</el-checkbox>
        </el-form-item>
      </el-form>

      <div v-loading="rankLoading">
        <div v-if="rankResult && rankResult.length > 0">
          <el-table :data="rankResult" border size="small" max-height="500" style="width: auto; max-width: 100%">
            <el-table-column prop="rank" label="排名" width="70" />
            <el-table-column label="名称" width="200" show-overflow-tooltip>
              <template #default="{ row }">
                {{ formatName(row) }}
              </template>
            </el-table-column>
            <el-table-column
              v-for="col in dynamicColumns"
              :key="col.key"
              :prop="col.key"
              :label="col.label"
              :width="col.width"
            >
              <template #default="{ row }">
                {{ formatCol(col.key, row[col.key]) }}
              </template>
            </el-table-column>
            <el-table-column prop="vipLevel" :label="vipLevelLabel" width="70" />
          </el-table>
        </div>
        <el-empty v-else-if="rankGenerated && !rankLoading" description="无数据" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { adminApi, analyticsApi } from '@/api'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

// ==================== 页面访问统计（从 About.vue 迁移） ====================
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

const updateChart = () => {
  if (!chartInstance || !statsData.value) return
  const daily = statsData.value.daily
  const isHourly = statsDays.value === 1
  const xLabels = isHourly
    ? daily.map(d => d.date.slice(11, 16))
    : daily.map(d => d.date.slice(5))

  if (isHourly) {
    chartInstance.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['PV'], top: 0 },
      grid: { top: 30, right: 20, bottom: 30, left: 50 },
      xAxis: { type: 'category', data: xLabels, boundaryGap: false, axisLabel: { interval: 2 } },
      yAxis: { type: 'value', name: 'PV', minInterval: 1 },
      series: [
        { name: 'PV', type: 'line', data: daily.map(d => d.pv), smooth: true, itemStyle: { color: '#409eff' }, areaStyle: { color: 'rgba(64,158,255,0.1)' } }
      ]
    }, true)
  } else {
    chartInstance.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['PV', 'UV'], top: 0 },
      grid: { top: 30, right: 50, bottom: 30, left: 50 },
      xAxis: { type: 'category', data: xLabels, boundaryGap: false },
      yAxis: [
        { type: 'value', name: 'PV', minInterval: 1, position: 'left' },
        { type: 'value', name: 'UV', minInterval: 1, position: 'right' }
      ],
      series: [
        { name: 'PV', type: 'line', yAxisIndex: 0, data: daily.map(d => d.pv), smooth: true, itemStyle: { color: '#409eff' }, areaStyle: { color: 'rgba(64,158,255,0.1)' } },
        { name: 'UV', type: 'line', yAxisIndex: 1, data: daily.map(d => d.uv), smooth: true, itemStyle: { color: '#67c23a' }, areaStyle: { color: 'rgba(103,194,58,0.1)' } }
      ]
    }, true)
  }
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
  } catch (e: any) {
    ElMessage.error(e.message || '获取统计数据失败')
  } finally {
    statsLoading.value = false
  }
}

// ==================== 自定义排行榜 ====================
const itemsList = ref<{ name: string; type: string }[]>([])
const rankLoading = ref(false)
const rankGenerated = ref(false)
const rankResult = ref<any[]>([])
const rankColumns = ref<string[]>([])

const rankForm = reactive({
  dimension: 'kusa' as 'kusa' | 'advKusa' | 'totalAdvKusa' | 'kusaOnce' | 'advKusaOnce' | 'item',
  limit: 25,
  levelMax: 10,
  showInactive: false,
  showSubaccount: true,
  itemName: '' as string
})

const columnLabels: Record<string, string> = {
  rank: '排名',
  name: '名称',
  kusa: '草数',
  advKusa: '草精数',
  totalAdvKusa: '累计草精',
  nowAdvKusa: '当前草精',
  titleAdvKusa: '称号草精',
  itemAdvKusa: '物品草精',
  kusaResult: '单次草数',
  advKusaResult: '单次草精',
  createTimeTs: '时间',
  amount: '数量',
  vipLevel: '等级'
}

// 需要在表格中动态展示的列（排除固定的 rank/name/vipLevel）
const dynamicColumns = computed(() => {
  return rankColumns.value
    .filter(c => !['rank', 'name', 'vipLevel'].includes(c))
    .map(c => ({
      key: c,
      label: columnLabels[c] || c,
      width: c === 'amount' ? 100 : (c === 'createTimeTs' ? 160 : 120)
    }))
})

// 单次打分维度下，等级列标题改为"用户等级"以更明确
const vipLevelLabel = computed(() => {
  return (rankForm.dimension === 'kusaOnce' || rankForm.dimension === 'advKusaOnce') ? '用户等级' : '等级'
})

const formatCol = (key: string, value: any) => {
  if (value === undefined || value === null) return '-'
  if (key === 'createTimeTs') {
    // 时间戳（秒）→ YY-MM-DD HH:mm
    const d = new Date(value * 1000)
    const yy = String(d.getFullYear()).slice(-2)
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mi = String(d.getMinutes()).padStart(2, '0')
    return `${yy}-${mm}-${dd} ${hh}:${mi}`
  }
  if (typeof value === 'number') return value.toLocaleString()
  return value
}

// 名称栏：有昵称显示"昵称(qq号)"，无昵称直接显示qq号
const formatName = (row: any) => {
  const { name, qq } = row
  if (name && name !== qq) return `${name}(${qq})`
  return qq || name || '-'
}

const fetchItemsList = async () => {
  try {
    const data = await adminApi.getItemsList()
    itemsList.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '获取物品列表失败')
  }
}

const generateRank = async () => {
  if (rankForm.dimension === 'item' && !rankForm.itemName) {
    return
  }

  rankLoading.value = true
  rankGenerated.value = true
  try {
    const res: any = await adminApi.generateCustomRank({
      dimension: rankForm.dimension,
      limit: rankForm.limit,
      levelMax: rankForm.levelMax,
      showInactive: rankForm.showInactive,
      showSubaccount: rankForm.showSubaccount,
      itemName: rankForm.dimension === 'item' ? rankForm.itemName : undefined
    })
    rankResult.value = res.list || []
    rankColumns.value = res.columns || []
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    rankLoading.value = false
  }
}

defineExpose({ refresh: () => { fetchStats(); fetchItemsList(); generateRank() } })

// 自动生成：配置变化时触发（前N名/最大等级为空时不触发）
watch(
  () => ({ ...rankForm }),
  () => {
    if (rankForm.limit == null || rankForm.levelMax == null) return
    generateRank()
  },
  { deep: true }
)

// ==================== 初始化 ====================
onMounted(() => {
  fetchStats()
  fetchItemsList()
  generateRank()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-card {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.stats-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.stats-content h4 {
  margin: 16px 0 8px;
  color: #333;
  font-size: 14px;
}

.rank-form {
  margin-bottom: 8px;
}

.rank-form :deep(.el-form-item) {
  margin-bottom: 8px;
}
</style>
