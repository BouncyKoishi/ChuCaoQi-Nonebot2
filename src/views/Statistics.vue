<template>
  <div class="statistics-container">
    <el-card class="statistics-card">
      <template #header>
        <div class="card-header">
          <h2>统计中心</h2>
          <el-button @click="refreshStats" circle size="default" style="width: 32px; height: 32px;">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="工业产量" name="production">
          <div v-if="dailyProduction" class="production-info">
            <el-descriptions :column="2" border class="responsive-descriptions">
              <el-descriptions-item label="生草产量">
                <span class="kusa-value">{{ formatNumber(dailyProduction.kusaAmount) }}</span>
                <span class="unit">草</span>
              </el-descriptions-item>
              <el-descriptions-item label="草之精华产量">
                <span class="adv-kusa-value">{{ formatNumber(dailyProduction.advKusaAmount) }}</span>
                <span class="unit">草之精华</span>
              </el-descriptions-item>
              <el-descriptions-item label="自动化核心产量">
                <span class="core-value">{{ formatNumber(dailyProduction.coreAmount) }}</span>
                <span class="unit">核心</span>
              </el-descriptions-item>
              <el-descriptions-item label="红茶产量">
                <span class="tea-value">{{ formatNumber(dailyProduction.blackTeaAmount) }}</span>
                <span class="unit">红茶</span>
              </el-descriptions-item>
            </el-descriptions>

            <el-divider />

            <div class="production-factors">
              <h4>产量加成因素</h4>
              <el-descriptions v-if="hasProductionFactors" :column="1" border>
                <el-descriptions-item v-if="productionFactors.machineAmount > 0" label="生草机器">
                  {{ productionFactors.machineAmount }}个机器 × {{ productionFactors.machineRandInt }}/天
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.machineTechLevel > 0" label="生草机器技术">
                  等级 {{ productionFactors.machineTechLevel }} ({{ productionFactors.machineTechLevel === 1 ? '8倍' : '40倍' }})
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.factoryAmount > 0" label="生草工厂">
                  {{ productionFactors.factoryAmount }}个工厂 × 640/天
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.mobileFactoryAmount > 0" label="流动生草工厂">
                  {{ productionFactors.mobileFactoryAmount }}个流动工厂 × 640/天
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.factoryNewDeviceLevel > 0" label="生草工厂新型设备">
                  等级 {{ productionFactors.factoryNewDeviceLevel }} ({{ Math.pow(2, productionFactors.factoryNewDeviceLevel) }}倍)
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.factoryTechLevel > 0" label="生草工厂效率">
                  等级 {{ productionFactors.factoryTechLevel }} ({{ Math.pow(2, productionFactors.factoryTechLevel) }}倍)
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.advFactoryAmount > 0" label="草精炼厂">
                  {{ productionFactors.advFactoryAmount }}个，+{{ productionFactors.advFactoryAmount }}草精，消耗{{ productionFactors.advFactoryAmount }} * 5000草
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.advKusaBaseAddition > 0" label="高效草精炼指南">
                  {{ productionFactors.advKusaBaseAddition }}本，每本+1草精，共+{{ Math.min(productionFactors.advKusaBaseAddition, productionFactors.advFactoryAmount) }}草精
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.sevenPlanetMagic > 0" label="七曜精炼术">
                  每7个精炼厂额外+4草精，共+{{ Math.floor(productionFactors.advFactoryAmount / 7) * 4 }}草精
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.advKusaAdditionI > 0" label="草精炼厂效率I">
                  精炼厂数量>7时，每多1个+1草精，共+{{ Math.max(0, productionFactors.advFactoryAmount - 7) }}草精
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.advKusaAdditionII > 0" label="草精炼厂效率II">
                  指南提供的额外加成：n(n-1)草精，共+{{ Math.min(productionFactors.advKusaBaseAddition, productionFactors.advFactoryAmount) * (Math.min(productionFactors.advKusaBaseAddition, productionFactors.advFactoryAmount) - 1) }}草精
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.coreFactoryAmount > 0" label="核心装配工厂">
                  {{ productionFactors.coreFactoryAmount }}个核心工厂 × {{ productionFactors.coreRandInt }}/天
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.coreTechLevel > 0" label="核心工厂效率">
                  等级 {{ productionFactors.coreTechLevel }} ({{ [1, 2, 4, 8, 12][productionFactors.coreTechLevel] }}倍)
                </el-descriptions-item>
                <el-descriptions-item v-if="productionFactors.remiProductionMagic" label="蕾米球的生产魔法">
                  额外获得{{ Math.round(productionFactors.remiBonus * 100) }}%产量
                </el-descriptions-item>
              </el-descriptions>
              <el-empty v-else description="暂无产量加成因素" />
            </div>
          </div>
          <el-empty v-else description="暂无产量信息" />
        </el-tab-pane>

        <el-tab-pane label="生草统计" name="grass">
          <div class="grass-stats">
            <el-card>
              <template #header>
                <div class="card-header">
                  <h3>个人产量统计</h3>
                  <el-radio-group v-model="grassStatsPeriod" size="small">
                    <el-radio-button label="24小时">24小时</el-radio-button>
                    <el-radio-button label="昨日">昨日</el-radio-button>
                    <el-radio-button label="上周">上周</el-radio-button>
                  </el-radio-group>
                </div>
              </template>
              <div v-if="personalGrassStats" class="grass-stats-content">
                <el-descriptions :column="2" border class="responsive-descriptions">
                  <el-descriptions-item label="总生草次数">
                    <span class="stats-value">{{ personalGrassStats.count || 0 }}</span>
                  <span class="unit">次</span>
                </el-descriptions-item>
                <el-descriptions-item label="总草产量">
                  <span class="kusa-value">{{ (personalGrassStats.sumKusa || 0).toLocaleString() }}</span>
                  <span class="unit">草</span>
                </el-descriptions-item>
                <el-descriptions-item label="总草之精华产量">
                  <span class="adv-kusa-value">{{ (personalGrassStats.sumAdvKusa || 0).toLocaleString() }}</span>
                  <span class="unit">草精</span>
                </el-descriptions-item>
                  <el-descriptions-item label="每次平均草产量">
                    <span class="avg-value">{{ personalGrassStats.avgKusa ? personalGrassStats.avgKusa.toFixed(2) : ((personalGrassStats.sumKusa || 0) / (personalGrassStats.count || 1)).toFixed(2) }}</span>
                    <span class="unit">草/次</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="每次平均草精产量">
                    <span class="avg-value">{{ personalGrassStats.avgAdvKusa ? personalGrassStats.avgAdvKusa.toFixed(2) : ((personalGrassStats.sumAdvKusa || 0) / (personalGrassStats.count || 1)).toFixed(2) }}</span>
                    <span class="unit">草精/次</span>
                  </el-descriptions-item>
                </el-descriptions>
              </div>
              <el-empty v-else description="暂无个人生草统计数据" />
            </el-card>
            
            <el-card style="margin-top: 20px;">
              <template #header>
                <div class="card-header">
                  <h3>全服产量统计</h3>
                  <el-radio-group v-model="totalGrassStatsPeriod" size="small">
                    <el-radio-button label="24小时">24小时</el-radio-button>
                    <el-radio-button label="昨日">昨日</el-radio-button>
                    <el-radio-button label="上周">上周</el-radio-button>
                  </el-radio-group>
                </div>
              </template>
              <div v-if="totalGrassStats" class="grass-stats-content">
                <el-descriptions :column="2" border class="responsive-descriptions">
                  <el-descriptions-item label="总生草次数">
                    <span class="stats-value">{{ totalGrassStats.count || 0 }}</span>
                  <span class="unit">次</span>
                </el-descriptions-item>
                <el-descriptions-item label="总草产量">
                  <span class="kusa-value">{{ (totalGrassStats.sumKusa || 0).toLocaleString() }}</span>
                  <span class="unit">草</span>
                </el-descriptions-item>
                <el-descriptions-item label="总草之精华产量">
                  <span class="adv-kusa-value">{{ (totalGrassStats.sumAdvKusa || 0).toLocaleString() }}</span>
                  <span class="unit">草精</span>
                </el-descriptions-item>
                <el-descriptions-item label="每次平均草产量">
                  <span class="avg-value">{{ totalGrassStats.avgKusa ? totalGrassStats.avgKusa.toFixed(2) : (totalGrassStats.count ? ((totalGrassStats.sumKusa || 0) / totalGrassStats.count).toFixed(2) : 0) }}</span>
                  <span class="unit">草/次</span>
                </el-descriptions-item>
                <el-descriptions-item label="每次平均草精产量">
                  <span class="avg-value">{{ totalGrassStats.avgAdvKusa ? totalGrassStats.avgAdvKusa.toFixed(2) : (totalGrassStats.count ? ((totalGrassStats.sumAdvKusa || 0) / totalGrassStats.count).toFixed(2) : 0) }}</span>
                  <span class="unit">草精/次</span>
                </el-descriptions-item>
                </el-descriptions>
              </div>
              <el-empty v-else description="暂无全服生草统计数据" />
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="G市统计" name="gmarket">
          <div class="gmarket-stats">
            <el-card>
              <div v-if="gMarketStats" class="gmarket-stats-content">
                <div class="gmarket-period">
                  <h4>本期统计</h4>
                  <el-descriptions :column="2" border class="responsive-descriptions">
                    <el-descriptions-item label="本期买入总值">
                      <span class="value">{{ (gMarketStats.currentBuyTotal || 0).toLocaleString() }}</span>
                      <span class="unit">草</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="本期卖出总值">
                      <span class="value">{{ (gMarketStats.currentSellTotal || 0).toLocaleString() }}</span>
                      <span class="unit">草</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="本期盈亏">
                      <span :class="(gMarketStats.currentProfit || 0) >= 0 ? 'profit-value' : 'loss-value'">{{ (gMarketStats.currentProfit || 0).toLocaleString() }}</span>
                      <span class="unit">草</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="当前持仓估值">
                      <span class="value">{{ (gMarketStats.currentHoldingsValue || 0).toLocaleString() }}</span>
                      <span class="unit">草</span>
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
                
                <el-divider />
                
                <div class="gmarket-period">
                  <h4>上期统计</h4>
                  <el-descriptions :column="2" border>
                    <el-descriptions-item label="上期买入总值">
                      <span class="value">{{ (gMarketStats.lastBuyTotal || 0).toLocaleString() }}</span>
                      <span class="unit">草</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="上期卖出总值">
                      <span class="value">{{ (gMarketStats.lastSellTotal || 0).toLocaleString() }}</span>
                      <span class="unit">草</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="上期盈亏" :span="2">
                      <span :class="(gMarketStats.lastProfit || 0) >= 0 ? 'profit-value' : 'loss-value'">{{ (gMarketStats.lastProfit || 0).toLocaleString() }}</span>
                      <span class="unit">草</span>
                    </el-descriptions-item>
                  </el-descriptions>
                </div>

                <el-divider />

                <div class="gmarket-records">
                  <h4>本期G市操作记录</h4>
                  <div v-if="gMarketRecords.length > 0">
                    <el-table :data="gMarketRecords" style="width: 100%">
                      <el-table-column prop="timestamp" label="时间" width="150">
                        <template #default="scope">
                          {{ scope.row.timestamp ? new Date(scope.row.timestamp * 1000).toLocaleString() : '' }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="type" label="类型" width="100">
                        <template #default="scope">
                          <el-tag :type="scope.row.type === 'buy' ? 'success' : 'danger'">{{ scope.row.type === 'buy' ? '买入' : '卖出' }}</el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column prop="gType" label="G类型" width="150" />
                      <el-table-column prop="amount" label="数量" width="100" />
                      <el-table-column prop="unitPrice" label="单价" width="100">
                        <template #default="scope">
                          {{ scope.row.unitPrice.toFixed(3) }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="totalPrice" label="总价" width="150">
                        <template #default="scope">
                          {{ (scope.row.totalPrice || 0).toLocaleString() }}
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-pagination
                      layout="prev, pager, next"
                      :total="gMarketRecordsTotal"
                      :page-size="10"
                      :current-page="gMarketPage"
                      @current-change="handleGMarketPageChange"
                      style="margin-top: 20px; text-align: center"
                    />
                  </div>
                  <el-empty v-else description="暂无G市操作记录" />
                </div>
              </div>
              <el-empty v-else description="暂无G市统计数据" />
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的统计" name="user">
          <div v-if="userStats" class="user-stats">
            <el-row :gutter="20">
              <el-col :span="24">
                <el-card>
                  <template #header>
                    <h3>草之精华统计</h3>
                  </template>
                  <el-descriptions :column="1" border>
                    <el-descriptions-item label="现有草之精华">
                      <span class="title-value">{{ userStats.nowAdvKusa }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="信息员等级消费">
                      <span class="title-value">{{ userStats.titleAdvKusa }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="道具消费">
                      <span class="item-value">{{ userStats.itemAdvKusa }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="草之精华总计">
                      <span class="adv-kusa-value">{{ userStats.totalAdvKusa }}</span>
                    </el-descriptions-item>
                  </el-descriptions>
                </el-card>
              </el-col>
            </el-row>
          </div>
          <el-empty v-else description="暂无用户统计信息" />
        </el-tab-pane>

        <el-tab-pane label="排行榜" name="rank">
          <div class="rank-section">
            <div class="rank-header">
              <h3>排行榜 TOP 25</h3>
              <div class="rank-controls">
                <el-radio-group v-model="rankType" size="small" style="margin-right: 20px">
                  <el-radio-button label="kusa">按草排序</el-radio-button>
                  <el-radio-button label="advKusa">按草精排序</el-radio-button>
                  <el-radio-button label="totalAdvKusa">按累计草精</el-radio-button>
                </el-radio-group>
              </div>
            </div>
            <!-- 按草/草精排序 -->
            <el-table v-if="rankType !== 'totalAdvKusa'" :data="kusaRank" style="width: 100%">
              <el-table-column type="index" label="排名" width="80" />
              <el-table-column prop="name" label="玩家" width="150" />
              <el-table-column :prop="rankType === 'advKusa' ? 'advKusa' : 'kusa'" :label="rankType === 'advKusa' ? '草之精华' : '草数量'" min-width="180">
                <template #default="scope">
                  <span :class="rankType === 'advKusa' ? 'adv-kusa-value' : 'kusa-value'">{{ formatNumber((rankType === 'advKusa' ? scope.row.advKusa : scope.row.kusa) || 0) }}</span>
                </template>
              </el-table-column>
              <el-table-column :prop="rankType === 'advKusa' ? 'kusa' : 'advKusa'" :label="rankType === 'advKusa' ? '草数量' : '草之精华'" min-width="150">
                <template #default="scope">
                  <span :class="rankType === 'advKusa' ? 'kusa-value' : 'adv-kusa-value'">{{ formatNumber((rankType === 'advKusa' ? scope.row.kusa : scope.row.advKusa) || 0) }}</span>
                </template>
              </el-table-column>
            </el-table>
            <!-- 累计草精排行榜 -->
            <el-table v-else :data="totalAdvKusaRank" style="width: 100%">
              <el-table-column type="index" label="排名" width="80" />
              <el-table-column prop="name" label="玩家" width="150" />
              <el-table-column prop="totalAdvKusa" label="累计草精" min-width="150">
                <template #default="scope">
                  <span class="adv-kusa-value">{{ formatNumber(scope.row.totalAdvKusa || 0) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="nowAdvKusa" label="现有草精" min-width="120">
                <template #default="scope">
                  <span class="kusa-value">{{ formatNumber(scope.row.nowAdvKusa || 0) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="titleAdvKusa" label="VIP消耗" min-width="120">
                <template #default="scope">
                  <span class="stats-value">{{ formatNumber(scope.row.titleAdvKusa || 0) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="itemAdvKusa" label="道具消费" min-width="120">
                <template #default="scope">
                  <span class="item-value">{{ formatNumber(scope.row.itemAdvKusa || 0) }}</span>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="(rankType === 'totalAdvKusa' ? totalAdvKusaRank.length === 0 : kusaRank.length === 0)" description="暂无排行数据" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { warehouseApi } from '@/api'
import { formatNumber } from '@/utils'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, ref, watch } from 'vue'

const activeTab = ref('production')
const loading = ref(false)
const dailyProduction = ref<any>(null)
const userStats = ref<any>(null)
const kusaRank = ref<any[]>([])
const productionFactors = ref<any>({})
const hasProductionFactors = ref(false)
const grassStatsPeriod = ref('24小时')
const totalGrassStatsPeriod = ref('24小时')
const personalGrassStats = ref<any>(null)
const totalGrassStats = ref<any>(null)
const gMarketStats = ref<any>(null)
const gMarketRecords = ref<any[]>([])
const gMarketRecordsTotal = ref(0)
const gMarketPage = ref(1)
const rankSortByAdvKusa = ref(false)
const rankType = ref<'kusa' | 'advKusa' | 'totalAdvKusa'>('kusa')
const totalAdvKusaRank = ref<any[]>([])

const refreshStats = async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchDailyProduction(),
      fetchUserStats(),
      fetchKusaRank(),
      fetchPersonalGrassStats(),
      fetchTotalGrassStats(),
      fetchGMarketStats(),
      fetchGMarketRecords()
    ])
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

const fetchDailyProduction = async () => {
  try {
    const response = await warehouseApi.getDailyProduction()
    dailyProduction.value = response
    
    productionFactors.value = {
      machineAmount: response.machineAmount || 0,
      machineRandInt: response.machineRandInt || 8,
      machineTechLevel: response.machineTechLevel || 0,
      factoryAmount: response.factoryAmount || 0,
      mobileFactoryAmount: response.mobileFactoryAmount || 0,
      factoryNewDeviceLevel: response.factoryNewDeviceLevel || 0,
      factoryTechLevel: response.factoryTechLevel || 0,
      advFactoryAmount: response.advFactoryAmount || 0,
      advKusaAmount: response.advKusaAmount || 0,
      advKusaBaseAddition: response.advKusaBaseAddition || 0,
      sevenPlanetMagic: response.sevenPlanetMagic || 0,
      advKusaAdditionI: response.advKusaAdditionI || 0,
      advKusaAdditionII: response.advKusaAdditionII || 0,
      coreFactoryAmount: response.coreFactoryAmount || 0,
      coreTechLevel: response.coreTechLevel || 0,
      coreRandInt: response.coreRandInt || 8,
      remiProductionMagic: response.remiProductionMagic || false,
      remiBonus: response.remiBonus || 0
    }
    
    // 判断是否有产量加成因素
    hasProductionFactors.value = Object.values(productionFactors.value).some(value => {
      return value > 0 || value === true
    })
  } catch (error) {
    dailyProduction.value = null
  }
}

const fetchUserStats = async () => {
  try {
    const response = await warehouseApi.getUserStats()
    userStats.value = response
  } catch (error) {
    userStats.value = null
  }
}

const fetchKusaRank = async () => {
  try {
    if (rankType.value === 'totalAdvKusa') {
      // 加载累计草精排行榜
      const response = await warehouseApi.getTotalAdvKusaRank(25, 10)
      totalAdvKusaRank.value = response || []
    } else {
      // 加载草/草精排行榜
      const response = await warehouseApi.getKusaRank(rankType.value)
      kusaRank.value = response || []
    }
  } catch (error) {
    console.error('加载排行榜失败:', error)
    kusaRank.value = []
    totalAdvKusaRank.value = []
  }
}

const fetchPersonalGrassStats = async () => {
  try {
    const response = await warehouseApi.getGrassStatsPersonal(grassStatsPeriod.value)
    personalGrassStats.value = response
  } catch (error) {
    personalGrassStats.value = null
  }
}

const fetchTotalGrassStats = async () => {
  try {
    const response = await warehouseApi.getGrassStatsTotal(totalGrassStatsPeriod.value)
    totalGrassStats.value = response
  } catch (error) {
    totalGrassStats.value = null
  }
}

const fetchGMarketStats = async () => {
  try {
    const response = await warehouseApi.getGMarketStats()
    gMarketStats.value = response
  } catch (error) {
    gMarketStats.value = null
  }
}

const fetchGMarketRecords = async () => {
  try {
    const response = await warehouseApi.getGMarketRecords(gMarketPage.value, 10)
    gMarketRecords.value = response.records || []
    gMarketRecordsTotal.value = response.total || 0
  } catch (error) {
    gMarketRecords.value = []
    gMarketRecordsTotal.value = 0
  }
}

const handleGMarketPageChange = (page: number) => {
  gMarketPage.value = page
  fetchGMarketRecords()
}

const handleGrassStatsPeriodChange = () => {
  fetchPersonalGrassStats()
}

const handleTotalGrassStatsPeriodChange = () => {
  fetchTotalGrassStats()
}

watch(grassStatsPeriod, handleGrassStatsPeriodChange)
watch(totalGrassStatsPeriod, handleTotalGrassStatsPeriodChange)
watch(rankType, fetchKusaRank)

onMounted(() => {
  refreshStats()
})
</script>

<style scoped>
.statistics-container {
  max-width: 1000px;
  margin: 0 auto;
}

.statistics-card {
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

.card-header h3 {
  margin: 0;
  color: #333;
  font-size: 16px;
}

.kusa-value {
  color: #67c23a;
  font-weight: bold;
  font-size: 18px;
}

.adv-kusa-value {
  color: #e6a23c;
  font-weight: bold;
  font-size: 18px;
}

.core-value {
  color: #409eff;
  font-weight: bold;
  font-size: 18px;
}

.tea-value {
  color: #f56c6c;
  font-weight: bold;
  font-size: 18px;
}

.total-value {
  color: #909399;
  font-weight: bold;
  font-size: 24px;
}

.stats-value {
  color: #409eff;
  font-weight: bold;
  font-size: 18px;
}

.avg-value {
  color: #909399;
  font-weight: bold;
  font-size: 18px;
}

.profit-value {
  color: #67c23a;
  font-weight: bold;
  font-size: 18px;
}

.loss-value {
  color: #f56c6c;
  font-weight: bold;
  font-size: 18px;
}

.value {
  color: #303133;
  font-weight: bold;
  font-size: 18px;
}

.title-value {
  color: #909399;
  font-weight: bold;
  font-size: 18px;
}

.item-value {
  color: #909399;
  font-weight: bold;
  font-size: 18px;
}

.unit {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
}

.production-factors {
  margin-top: 20px;
}

.production-factors h4 {
  margin-bottom: 12px;
  color: #333;
}

.rank-section {
  margin-top: 20px;
}

.rank-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.rank-section h3 {
  margin: 0;
  color: #333;
}

.grass-stats {
  margin-top: 20px;
}

.grass-stats-content {
  margin-top: 8px;
}

.card-header h4 {
  margin: 0;
  color: #333;
  font-size: 14px;
}

.gmarket-stats {
  margin-top: 20px;
}

.gmarket-stats-content {
  margin-top: 16px;
}

.gmarket-records {
  margin-top: 20px;
}

.gmarket-records h4 {
  margin-bottom: 12px;
  color: #333;
}

.user-stats {
  margin-top: 20px;
}

/* 统一字体样式 */
* {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 响应式布局 - 小屏幕下改为单栏 */
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
