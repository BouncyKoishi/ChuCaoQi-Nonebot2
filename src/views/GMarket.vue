<template>
  <div class="gmarket-container">
    <el-card v-if="gValue" class="gmarket-card">
      <template #header>
        <div class="card-header">
          <h2>G市</h2>
          <el-button @click="refreshGValue" circle size="default" style="width: 32px; height: 32px;">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="g-info">
        <el-descriptions :column="2" border class="responsive-descriptions">
            <el-descriptions-item label="当前期数">{{ gValue.turn }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatTime(gValue.createTime) }}
            </el-descriptions-item>
          </el-descriptions>
        <div v-if="!gValue.isTradingTime" class="trading-time-warning">
          <el-icon><WarningFilled /></el-icon>
          <span>当前是结算时间，无法进行交易</span>
        </div>
      </div>

      <el-divider />

      <div class="holdings-section">
        <h3>持仓信息</h3>
        <el-table :data="holdingData" style="width: 100%" border>
          <el-table-column prop="name" label="校区" min-width="80" />
          <el-table-column prop="lastPrice" label="上期" min-width="100" class-name="hide-on-mobile">
            <template #default="{ row }">
              {{ formatNumber(row.lastPrice) }}
            </template>
          </el-table-column>
          <el-table-column prop="currentPrice" label="本期" min-width="100">
            <template #default="{ row }">
              {{ formatNumber(row.currentPrice) }}
            </template>
          </el-table-column>
          <el-table-column prop="volatility" label="波动" min-width="90" class-name="hide-on-mobile">
            <template #default="{ row }">
              {{ row.volatility > 0 ? '+' : '' }}{{ formatNumber(row.volatility) }}%
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="持仓" min-width="100">
            <template #default="{ row }">
              {{ formatNumber(row.amount) }}
            </template>
          </el-table-column>
          <el-table-column prop="value" label="价值" min-width="120" class-name="hide-on-mobile">
            <template #default="{ row }">
              {{ formatNumber(row.value) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="handleBuyPopup(row.name)" :disabled="!gValue.isTradingTime">买入</el-button>
              <el-button type="danger" size="small" @click="handleSellPopup(row.name)" :disabled="!gValue.isTradingTime">卖出</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="total-value" v-if="gValue.totalValue">
          <el-descriptions :column="1" border style="margin-top: 16px">
            <el-descriptions-item label="总持仓价值">{{ formatNumber(Math.round(gValue.totalValue)) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <el-divider />

      <div class="chart-section">
        <div class="chart-header">
          <h3>G线图</h3>
          <div class="chart-controls">
            <el-select v-model="chartType" placeholder="选择图表类型">
              <el-option label="总G线图" value="all" />
              <el-option label="东校区G" value="east" />
              <el-option label="南校区G" value="south" />
              <el-option label="北校区G" value="north" />
              <el-option label="珠海校区G" value="zhuhai" />
              <el-option label="深圳校区G" value="shenzhen" />
            </el-select>
          </div>
        </div>
        <div ref="chartRef" class="chart-container"></div>
      </div>

      <el-divider />

      <div class="trade-section">
        <h3>批量交易栏</h3>
        <el-form :model="batchTradeForm" label-width="100px" class="batch-trade-form">
          <el-form-item label="当前草量">
            <span>{{ formatNumber(userInfo?.kusa || 0) }} 草</span>
          </el-form-item>
          <el-form-item label="G类型">
            <div class="form-row">
              <el-select v-model="batchTradeForm.gTypes" multiple placeholder="选择G类型" class="g-type-select">
                <el-option label="东" value="east" />
                <el-option label="南" value="south" />
                <el-option label="北" value="north" />
                <el-option label="珠" value="zhuhai" />
                <el-option label="深" value="shenzhen" />
              </el-select>
              <div class="button-row">
                <el-button @click="selectAllGTypes">全选</el-button>
                <el-button @click="deselectAllGTypes">取消全选</el-button>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="交易类型">
            <el-radio-group v-model="batchTradeForm.tradeType">
              <el-radio-button label="buy">买入</el-radio-button>
              <el-radio-button label="sell">卖出</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="交易数量">
            <div class="form-row">
              <el-input-number
                v-model="batchTradeForm.amount"
                :min="1"
                :step="1"
                :disabled="batchTradeForm.positionMode !== 'manual'"
                :placeholder="batchPositionAmountPlaceholder"
                class="amount-input"
              />
              <div class="button-row">
                <el-radio-group v-model="batchTradeForm.positionMode" :disabled="batchTradeForm.gTypes.length === 0">
                  <el-radio-button label="manual">手动</el-radio-button>
                  <el-radio-button label="full">全仓</el-radio-button>
                  <el-radio-button label="half">半仓</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="预计价格">
            <span>{{ formatNumber(Math.round(estimatedBatchPrice)) }} 草</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleBatchTrade" :loading="trading" :disabled="!gValue.isTradingTime || batchTradeForm.gTypes.length === 0">
              执行交易
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <!-- 交易确认对话框 -->
    <el-dialog
      v-model="tradeDialogVisible"
      :title="tradeDialogTitle"
      width="400px"
    >
      <el-form :model="popupTradeForm" label-width="80px">
        <el-form-item label="交易数量">
          <el-input-number v-model="popupTradeForm.amount" :min="1" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="快速选择">
          <div class="quick-select-buttons">
            <el-button @click="selectPopupFullPosition">全仓</el-button>
            <el-button @click="selectPopupHalfPosition">半仓</el-button>
          </div>
        </el-form-item>
        <el-form-item label="预计价格">
          <span>{{ formatNumber(Math.round(popupEstimatedPrice)) }} 草</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="tradeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmPopupTrade" :loading="trading">确认交易</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { gMarketApi, userApi, warehouseApi } from '@/api'
import type { GValue, GValueHistory, UserInfo, WarehouseInfo } from '@/types'
import { formatNumber } from '@/utils'
import { Refresh, WarningFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

// ==================== G市相关常量 ====================

const G_TYPES = ['east', 'south', 'north', 'zhuhai', 'shenzhen'] as const
type GType = typeof G_TYPES[number]

const G_TYPE_TO_VALUE_KEY: Record<GType, string> = {
  east: 'east_value',
  south: 'south_value',
  north: 'north_value',
  zhuhai: 'zhuhai_value',
  shenzhen: 'shenzhen_value'
}

const G_TYPE_TO_LAST_VALUE_KEY: Record<GType, string> = {
  east: 'east_value_last',
  south: 'south_value_last',
  north: 'north_value_last',
  zhuhai: 'zhuhai_value_last',
  shenzhen: 'shenzhen_value_last'
}

const G_TYPE_TO_HISTORY_KEY: Record<GType, keyof GValueHistory> = {
  east: 'eastValue',
  south: 'southValue',
  north: 'northValue',
  zhuhai: 'zhuhaiValue',
  shenzhen: 'shenzhenValue'
}

const CHINESE_TO_G_TYPE: Record<string, GType> = {
  '东': 'east',
  '南': 'south',
  '北': 'north',
  '珠': 'zhuhai',
  '深': 'shenzhen'
}

const G_TYPE_TO_CHINESE: Record<GType, string> = {
  east: '东',
  south: '南',
  north: '北',
  zhuhai: '珠',
  shenzhen: '深'
}

const G_TYPE_TO_FULL_NAME: Record<GType, string> = {
  east: '东校区G',
  south: '南校区G',
  north: '北校区G',
  zhuhai: '珠海校区G',
  shenzhen: '深圳校区G'
}

const G_TYPE_TO_COLOR: Record<GType, string> = {
  east: '#5470c6',
  south: '#91cc75',
  north: '#fac858',
  zhuhai: '#ee6666',
  shenzhen: '#73c0de'
}

const INITIAL_G_VALUES: Record<GType, number> = {
  east: 9.8,
  south: 9.8,
  north: 6.67,
  zhuhai: 32.0,
  shenzhen: 120.0
}

// ==================== 响应式状态 ====================

const gValue = ref<GValue | null>(null)
const gValueHistory = ref<GValueHistory[]>([])
const userInfo = ref<UserInfo | null>(null)
const warehouseInfo = ref<WarehouseInfo | null>(null)
const loading = ref(false)
const trading = ref(false)
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

const batchTradeForm = ref({
  gTypes: [] as string[],
  tradeType: 'buy',
  amount: 1,
  positionMode: 'manual' as 'manual' | 'full' | 'half'
})

const popupTradeForm = ref({
  gType: '',
  fullGName: '',
  amount: 1,
  tradeType: 'buy'
})

const tradeDialogVisible = ref(false)
const tradeDialogTitle = ref('交易确认')

const chartType = ref('all')

// ==================== 工具函数 ====================

const getCurrentPrice = (gType: GType): number => {
  const valueKey = G_TYPE_TO_VALUE_KEY[gType]
  return gValue.value?.values?.[valueKey] || 0
}

const getLastPrice = (gType: GType): number => {
  const valueKey = G_TYPE_TO_LAST_VALUE_KEY[gType]
  return gValue.value?.values?.[valueKey] || 0
}

const getHoldingAmount = (gName: string): number => {
  if (!gValue.value?.holdings) return 0
  const holding = gValue.value.holdings[gName]
  if (holding === undefined) return 0
  return typeof holding === 'number' ? holding : (holding?.amount || 0)
}

const getGTypeFromChinese = (chineseName: string): GType | undefined => {
  const key = chineseName.charAt(0)
  return CHINESE_TO_G_TYPE[key]
}

const computeYAxisRange = (values: number[]): { yMin: number; yMax: number } => {
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const valueRange = maxValue - minValue

  let yMin: number, yMax: number
  if (valueRange > 0) {
    yMin = minValue - valueRange * 0.1
    yMax = maxValue + valueRange * 0.1
  } else {
    yMin = maxValue * 0.9
    yMax = maxValue * 1.1
  }

  yMin = Math.max(0.1, yMin)
  yMax = Math.max(yMin + 0.1, yMax)

  return { yMin, yMax }
}

const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}

// ==================== 仓位计算函数 ====================

interface PositionCalcParams {
  tradeType: 'buy' | 'sell'
  singleGType?: GType
  fullGName?: string
  ratio: number
}

const calculatePosition = (params: PositionCalcParams): number => {
  const { tradeType, singleGType, fullGName, ratio } = params

  if (tradeType === 'buy') {
    const userKusa = userInfo.value?.kusa || 0
    if (!singleGType) return 1

    const price = getCurrentPrice(singleGType)
    if (price > 0 && userKusa > 0) {
      const maxAmount = Math.floor(userKusa / price * ratio)
      return Math.max(1, maxAmount)
    }
    return 1
  } else {
    if (fullGName) {
      const amount = getHoldingAmount(fullGName)
      return Math.max(1, Math.floor(amount * ratio))
    }
    return 1
  }
}

// ==================== 计算属性 ====================

const holdingData = computed(() => {
  if (!gValue.value) return []
  
  return G_TYPES.map(gType => {
    const currentPrice = getCurrentPrice(gType)
    const lastPrice = getLastPrice(gType)
    const change = currentPrice - lastPrice
    const volatility = lastPrice > 0 ? (change / lastPrice * 100).toFixed(2) : '0.00'
    
    const chineseName = G_TYPE_TO_CHINESE[gType]
    const amount = getHoldingAmount(chineseName)
    const value = Math.round(amount * currentPrice)
    
    return {
      name: chineseName,
      lastPrice: lastPrice.toFixed(3),
      currentPrice: currentPrice.toFixed(3),
      volatility: volatility + '%',
      amount,
      value,
      areaKey: chineseName
    }
  })
})

const getBatchAmountForType = (gType: GType): number => {
  const mode = batchTradeForm.value.positionMode
  if (mode === 'manual') return batchTradeForm.value.amount

  const ratio = mode === 'full' ? 1 : 0.5

  if (batchTradeForm.value.tradeType === 'buy') {
    const userKusa = userInfo.value?.kusa || 0
    const price = getCurrentPrice(gType)
    const typeCount = batchTradeForm.value.gTypes.length || 1
    if (price > 0 && userKusa > 0) {
      return Math.max(1, Math.floor(userKusa / typeCount / price * ratio))
    }
    return 1
  } else {
    const chineseName = G_TYPE_TO_CHINESE[gType]
    const holding = getHoldingAmount(chineseName)
    if (holding > 0) {
      return Math.max(1, Math.floor(holding * ratio))
    }
    return 0
  }
}

const batchPositionAmountPlaceholder = computed(() => {
  const mode = batchTradeForm.value.positionMode
  if (mode === 'manual') return ''
  if (batchTradeForm.value.gTypes.length === 0) return ''
  if (batchTradeForm.value.gTypes.length === 1) {
    const gType = batchTradeForm.value.gTypes[0] as GType
    return String(getBatchAmountForType(gType))
  }
  return ''
})

const estimatedBatchPrice = computed(() => {
  if (!gValue.value || !batchTradeForm.value.gTypes.length) return 0

  return batchTradeForm.value.gTypes.reduce((total, gType) => {
    const price = getCurrentPrice(gType as GType)
    const amount = getBatchAmountForType(gType as GType)
    return total + (price * amount)
  }, 0)
})

const popupEstimatedPrice = computed(() => {
  if (!gValue.value || !popupTradeForm.value.gType) return 0
  
  const price = getCurrentPrice(popupTradeForm.value.gType as GType)
  return price * popupTradeForm.value.amount
})

// ==================== 图表相关 ====================

const initChart = () => {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance || gValueHistory.value.length === 0) return

  const turns = gValueHistory.value.map(item => item.turn.toString())
  
  if (chartType.value === 'all') {
    const seriesData = G_TYPES.map(gType => ({
      name: G_TYPE_TO_FULL_NAME[gType],
      data: gValueHistory.value.map(item => 
        (item[G_TYPE_TO_HISTORY_KEY[gType]] as number) / INITIAL_G_VALUES[gType]
      )
    }))
    
    const allValues = seriesData.flatMap(s => s.data)
    const { yMin, yMax } = computeYAxisRange(allValues)

    const option = {
      tooltip: {
        trigger: 'axis',
        formatter: function(params: any) {
          let result = `${params[0].axisValue}期<br/>`
          params.forEach((param: any) => {
            result += `${param.marker}${param.seriesName}: ${param.value.toFixed(3)}<br/>`
          })
          return result
        }
      },
      legend: {
        data: G_TYPES.map(t => G_TYPE_TO_FULL_NAME[t]),
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: turns
      },
      yAxis: {
        type: 'log',
        name: 'G值/初始G值',
        min: yMin,
        max: yMax,
        axisLabel: {
          formatter: function(value: number) {
            return value.toFixed(1)
          }
        }
      },
      series: seriesData.map((s, i) => ({
        name: s.name,
        type: 'line',
        data: s.data,
        itemStyle: { color: G_TYPE_TO_COLOR[G_TYPES[i]] },
        smooth: true,
        symbol: 'none'
      }))
    }

    chartInstance.setOption(option, true)
  } else {
    const gType = chartType.value as GType
    const values = gValueHistory.value.map(
      item => item[G_TYPE_TO_HISTORY_KEY[gType]] as number
    )
    const { yMin, yMax } = computeYAxisRange(values)

    const option = {
      tooltip: {
        trigger: 'axis',
        formatter: function(params: any) {
          return `${params[0].axisValue}期<br/>${params[0].marker}${params[0].seriesName}: ${params[0].value.toFixed(3)}`
        }
      },
      legend: {
        data: [G_TYPE_TO_FULL_NAME[gType]],
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: turns
      },
      yAxis: {
        type: 'value',
        name: 'G值',
        min: yMin,
        max: yMax,
        axisLabel: {
          formatter: function(value: number) {
            const range = yMax - yMin
            if (range > 0) {
              const distanceFromMin = value - yMin
              const distanceFromMax = yMax - value
              if (distanceFromMin < range * 0.01 || distanceFromMax < range * 0.01) {
                return ''
              }
            }
            return value
          }
        }
      },
      series: [{
        name: G_TYPE_TO_FULL_NAME[gType],
        type: 'line',
        data: values,
        itemStyle: { color: G_TYPE_TO_COLOR[gType] },
        smooth: true,
        symbol: 'none'
      }]
    }

    chartInstance.setOption(option, true)
  }
}

watch(chartType, () => {
  updateChart()
})

// ==================== 数据获取 ====================

const refreshGValue = async () => {
  loading.value = true
  try {
    gValue.value = await gMarketApi.getGValue()
    const historyData = await gMarketApi.getGValueHistory()
    gValueHistory.value = historyData.history || []
    
    try {
      userInfo.value = await userApi.getInfo()
      warehouseInfo.value = await warehouseApi.getWarehouse()
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
    
    await nextTick()
    if (chartInstance) {
      updateChart()
    } else {
      initChart()
    }
  } catch (error: any) {
    ElMessage.error(error.message || '获取G市信息失败')
  } finally {
    loading.value = false
  }
}

// ==================== 批量交易相关 ====================

const selectAllGTypes = () => {
  batchTradeForm.value.gTypes = [...G_TYPES]
}

const deselectAllGTypes = () => {
  batchTradeForm.value.gTypes = []
}

const handleBatchTrade = async () => {
  if (!batchTradeForm.value.gTypes.length) {
    ElMessage.warning('请选择至少一种G类型')
    return
  }

  trading.value = true
  try {
    for (const gType of batchTradeForm.value.gTypes) {
      const amount = getBatchAmountForType(gType as GType)
      if (amount <= 0) continue

      if (batchTradeForm.value.tradeType === 'buy') {
        await gMarketApi.buyG(gType, amount)
      } else {
        await gMarketApi.sellG(gType, amount)
      }
    }
    ElMessage.success('批量交易成功')
    await refreshGValue()
  } catch (error: any) {
    ElMessage.error(error.message || '批量交易失败')
  } finally {
    trading.value = false
  }
}

// ==================== 弹窗交易相关 ====================

const handleBuyPopup = (gName: string) => {
  const gType = getGTypeFromChinese(gName)
  if (gType) {
    popupTradeForm.value = {
      gType: gType,
      fullGName: gName,
      amount: 1,
      tradeType: 'buy'
    }
    tradeDialogTitle.value = `买入 ${gName}`
    tradeDialogVisible.value = true
  }
}

const handleSellPopup = (gName: string) => {
  const gType = getGTypeFromChinese(gName)
  if (gType) {
    const currentAmount = getHoldingAmount(gName)
    popupTradeForm.value = {
      gType: gType,
      fullGName: gName,
      amount: currentAmount > 0 ? currentAmount : 1,
      tradeType: 'sell'
    }
    tradeDialogTitle.value = `卖出 ${gName}`
    tradeDialogVisible.value = true
  }
}

const selectPopupFullPosition = () => {
  const amount = calculatePosition({
    tradeType: popupTradeForm.value.tradeType as 'buy' | 'sell',
    singleGType: popupTradeForm.value.gType as GType,
    fullGName: popupTradeForm.value.fullGName,
    ratio: 1
  })
  popupTradeForm.value.amount = amount
  ElMessage.info(`已设置为全仓交易数量: ${amount}`)
}

const selectPopupHalfPosition = () => {
  const amount = calculatePosition({
    tradeType: popupTradeForm.value.tradeType as 'buy' | 'sell',
    singleGType: popupTradeForm.value.gType as GType,
    fullGName: popupTradeForm.value.fullGName,
    ratio: 0.5
  })
  popupTradeForm.value.amount = amount
  ElMessage.info(`已设置为半仓交易数量: ${amount}`)
}

const confirmPopupTrade = async () => {
  trading.value = true
  try {
    if (popupTradeForm.value.tradeType === 'buy') {
      await gMarketApi.buyG(popupTradeForm.value.gType, popupTradeForm.value.amount)
      ElMessage.success('买入成功')
    } else {
      await gMarketApi.sellG(popupTradeForm.value.gType, popupTradeForm.value.amount)
      ElMessage.success('卖出成功')
    }
    tradeDialogVisible.value = false
    await refreshGValue()
  } catch (error: any) {
    ElMessage.error(error.message || '交易失败')
  } finally {
    trading.value = false
  }
}

// ==================== 生命周期 ====================

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  refreshGValue()
  refreshTimer = setInterval(refreshGValue, 30 * 60 * 1000)
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  chartInstance?.dispose()
})
</script>

<style scoped>
.gmarket-container {
  max-width: 1000px;
  margin: 0 auto;
}

.gmarket-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: #333;
}

.g-info {
  margin-bottom: 20px;
}

.trading-time-warning {
  margin-top: 12px;
  padding: 10px;
  background-color: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 4px;
  color: #f56c6c;
  display: flex;
  align-items: center;
}

.trading-time-warning span {
  margin-left: 8px;
}

.holdings-section h3 {
  margin-bottom: 16px;
  color: #333;
}

.total-value {
  margin-top: 16px;
}

.chart-section {
  margin: 20px 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-section h3 {
  margin: 0;
  color: #333;
}

.chart-controls {
  margin: 0;
}

.chart-controls .el-select {
  width: 200px;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.trade-section h3 {
  margin-bottom: 16px;
  color: #333;
}

.quick-select-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.quick-select-buttons .el-button {
  margin-right: 8px;
}

.g-type-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.select-buttons {
  display: flex;
  gap: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.form-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.button-row {
  display: flex;
  gap: 8px;
}

.g-type-select {
  width: 300px;
}

.amount-input {
  width: 150px;
}

.batch-trade-form .el-form-item__content {
  flex-wrap: wrap;
}

@media screen and (max-width: 600px) {
  .hide-on-mobile {
    display: none !important;
  }

  .form-row {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
  }

  .g-type-select {
    width: 100%;
  }

  .amount-input {
    width: 100%;
  }

  .button-row {
    justify-content: flex-end;
  }

  .chart-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .chart-controls {
    width: 100%;
  }

  .chart-controls .el-select {
    width: 100%;
  }
}

@media screen and (max-width: 600px) {
  .responsive-descriptions {
    --el-descriptions-column: 1 !important;
  }
  
  .responsive-descriptions .el-descriptions__body .el-descriptions__table {
    table-layout: auto;
  }
  
  .responsive-descriptions .el-descriptions__body .el-descriptions__table colgroup {
    display: none;
  }
  
  .responsive-descriptions .el-descriptions__body .el-descriptions__table tr {
    display: block;
    margin-bottom: 8px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: var(--el-border-radius-base);
    overflow: hidden;
  }
  
  .responsive-descriptions .el-descriptions__body .el-descriptions__table th {
    display: inline-block;
    width: auto !important;
    min-width: 80px;
    padding-right: 12px;
    background-color: var(--el-fill-color-light);
  }
  
  .responsive-descriptions .el-descriptions__body .el-descriptions__table td {
    display: inline-block;
    width: calc(100% - 92px) !important;
  }
}
</style>
