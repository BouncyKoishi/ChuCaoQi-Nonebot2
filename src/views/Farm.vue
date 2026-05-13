<template>
  <div class="farm-container">
    <el-card v-if="kusaField" class="farm-card">
      <template #header>
        <div class="card-header">
          <h2>百草园</h2>
          <el-button @click="refreshField" circle size="default" style="width: 32px; height: 32px;">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="field-info">
        <el-descriptions :column="2" border class="responsive-descriptions">
          <el-descriptions-item label="承载力">
            {{ kusaField.soilCapacity }} / 25
            <el-button v-if="isDev" type="primary" size="small" @click="handleRecoverCapacity" style="margin-left: 8px">恢复承载力</el-button>
          </el-descriptions-item>
          <el-descriptions-item label="后备承载力">
            {{ kusaField.spareCapacity }}
            <el-button type="primary" size="small" @click="handleReleaseSpareCapacity" style="margin-left: 8px" :disabled="kusaField.spareCapacity <= 0">释放后备承载力</el-button>
          </el-descriptions-item>
          <el-descriptions-item label="草地数量">
            {{ kusaField.fieldAmount }}
          </el-descriptions-item>
          <el-descriptions-item label="信息员等级">
            Lv{{ kusaField.vipLevel }} (加成 +{{ kusaField.vipBonus }})
          </el-descriptions-item>
          <el-descriptions-item label="加成效果" :span="2">
            <template v-if="!kusaField.isGrowing">
              <div class="bonus-tags">
                <el-tooltip v-if="kusaField.kelaAvailable" content="生长时间×0.5，产量×2" placement="top">
                  <el-tag type="success">金坷垃</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.doubleMagic" content="产量×2" placement="top">
                  <el-tag type="success">双生</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.spiritualSign" content="产量×2，草之精华×2（不灵草无效）" placement="top">
                  <el-tag type="success">灵性</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.biogasAvailable" :content="`产量×${kusaField.hasBlackTea ? '1.2~2.0' : '0.5~2.0'}${kusaField.hasBlackTea ? '（红茶加成）' : ''}`" placement="top">
                  <el-tag type="success">沼气</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.fallowSign > 0" :content="`产量×${kusaField.fallowSign === 1 ? 2 : 3}，草之精华×${kusaField.fallowSign === 1 ? 2 : 3}`" placement="top">
                  <el-tag type="success">休耕Lv{{ kusaField.fallowSign }}</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.kusaQualityLevel > 0" :content="`草之精华概率：${getAdvKusaProbability(kusaField.kusaQualityLevel)}%`" placement="top">
                  <el-tag type="success">生草质量Lv{{ kusaField.kusaQualityLevel }}</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.kusaTechLevel > 0" :content="`产量×${kusaField.kusaTechEffect}`" placement="top">
                  <el-tag type="success">生草数量Lv{{ kusaField.kusaTechLevel }}</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.soilCapacity <= 10" :content="`承载力过低，产量×${kusaField.soilEffect.toFixed(1)}`" placement="top">
                  <el-tag type="warning">土壤状态</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.mirrorPluginAvailable" content="50%概率触发镜映，产量×2，草之精华×2，消耗1后备承载力" placement="top">
                  <el-tag type="success">镜映</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.divinePluginAvailable" :content="`${kusaField.spiritlessDivinePluginAvailable ? '10%' : '5%'}概率触发神灵草`" placement="top">
                  <el-tag type="success">神灵草</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.mustGrow" content="保证至少获得1个草之精华" placement="top">
                  <el-tag type="success">控制论</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.chainMagic" content="生草数量出现3连号及以上时获得额外草之精华" placement="top">
                  <el-tag type="success">连锁</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.overloadMagic" content="过载生草：获得额外草之精华，但进入过载状态" placement="top">
                  <el-tag type="warning">过载</el-tag>
                </el-tooltip>
                <el-tooltip v-if="kusaField.spiritualMachineAvailable" content="没有灵性时自动选择不灵草" placement="top">
                  <el-tag type="info">自动分配</el-tag>
                </el-tooltip>
              </div>
            </template>
            <template v-else>
              <div class="bonus-tags">
                <el-tag v-if="kusaField.vipLevel > 0" type="success">信息员+{{ kusaField.vipBonus }}</el-tag>
                <el-tag v-if="kusaField.isUsingKela" type="success">金坷垃×2</el-tag>
                <el-tag v-if="kusaField.doubleMagic" type="success">双生×2</el-tag>
                <el-tag v-if="kusaField.growInfo?.spiritualSignEffective" type="success">灵性×2</el-tag>
                <el-tag v-if="kusaField.kusaTypeEffect !== 1" type="success">{{ kusaField.kusaType }}×{{ kusaField.kusaTypeEffect }}</el-tag>
                <el-tooltip v-if="kusaField.biogasEffect !== 1" :content="`本次沼气倍率`" placement="top">
                  <el-tag type="success">沼气×{{ kusaField.biogasEffect }}</el-tag>
                </el-tooltip>
                <el-tag v-if="kusaField.fallowSign > 0" type="success">休耕×{{ kusaField.fallowSign === 1 ? 2 : 3 }}</el-tag>
                <el-tag v-if="kusaField.kusaTechEffect !== 1" type="success">数量×{{ kusaField.kusaTechEffect }}</el-tag>
                <el-tag v-if="kusaField.soilEffect !== 1" type="warning">土壤×{{ kusaField.soilEffect.toFixed(1) }}</el-tag>
                <el-tooltip v-if="kusaField.isMirroring" content="镜映效果已触发" placement="top">
                  <el-tag type="success">镜映×2</el-tag>
                </el-tooltip>
                <el-tag type="success">草地×{{ kusaField.fieldAmount }}</el-tag>
              </div>
            </template>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <el-divider />

      <div class="field-status">
        <el-result
          v-if="!kusaField.isGrowing"
          icon="info"
          :title="kusaField.isOverloaded ? '土地过载中，无法生草' : '当前没有正在生长的草'"
          :sub-title="kusaField.isOverloaded ? '请等待过载状态结束后再试' : '请选择草种进行生草'"
        >
          <template #extra>
            <template v-if="!kusaField.isOverloaded && !kusaField.isGrowing && kusaField.soilCapacity > 0">
              <select v-model="selectedKusaType" style="width: 200px; padding: 8px; border-radius: 4px; border: 1px solid #dcdfe6;">
                <option v-for="type in availableKusaTypes.filter(t => t.available)" :key="type.name" :value="type.name">
                  {{ type.displayName }}
                </option>
              </select>
              <el-button type="primary" @click="handlePlant" style="margin-left: 12px" :loading="planting">
                开始生草
              </el-button>
              <el-button 
                v-if="hasOverloadMagic" 
                type="warning" 
                @click="handleOverloadPlant" 
                style="margin-left: 12px"
                :loading="planting"
              >
                过载生草
              </el-button>
            </template>
            <template v-else-if="kusaField.isOverloaded">
              <div style="color: #f56c6c; margin-bottom: 12px;">
                <el-icon><WarningFilled /></el-icon>
                <span> 土地过载中，请等待过载结束</span>
                <br v-if="kusaField.overloadEndTime" />
                <span v-if="kusaField.overloadEndTime" style="margin-left: 24px;">
                  结束时间：{{ formatOverloadEndTime(kusaField.overloadEndTime) }}
                </span>
              </div>
            </template>
            <template v-else>
              <span style="color: #909399;">
                {{ kusaField.isGrowing ? '草正在生长中，无法生草' : '承载力不足，无法生草' }}
              </span>
            </template>
          </template>
        </el-result>
        <el-result
          v-else
          icon="info"
          :title="kusaField.kusaType ? kusaField.kusaType + '正在生长中' : '草正在生长中'"
          :sub-title="kusaField.growInfo ? `预计收获时间: ${formatTime(kusaField.growInfo.finishTimestamp)}，剩余时间: ${Math.ceil(kusaField.growInfo.remainingSeconds / 60)}分钟` : `预计收获时间: ${formatTime(kusaField.kusaFinishTs)}`"
        >
          <template #extra>
            <div v-if="kusaField.growInfo && kusaField.growInfo.isPrescient">
              <div style="margin-bottom: 12px;">
                <span style="color: #67c23a;">预知产量：</span>
                <span>
                  草 {{ formatNumber(kusaField.growInfo.kusaResult) }}，草之精华 {{ formatNumber(kusaField.growInfo.advKusaResult) }}
                </span>
              </div>
            </div>
            <div v-else>
              <div style="margin-bottom: 12px;">
                <span style="color: #67c23a;">预估产量：</span>
                <span>草 {{ formatNumber(kusaField.predictKusaMin) }} - {{ formatNumber(kusaField.predictKusaMax) }}</span>
                <span v-if="kusaField.predictAdvKusa > 0" style="color: #e6a23c;">，草之精华 {{ formatNumber(kusaField.predictAdvKusa) }}</span>
              </div>
            </div>
            <el-button 
              v-if="kusaField.hasWeeder" 
              type="danger" 
              @click="handleHarvest" 
              :loading="harvesting"
              style="margin-top: 8px"
            >
              除草
            </el-button>
          </template>
        </el-result>
      </div>

      <el-divider />

      <div class="history-section">
        <h3>最近五条生草记录</h3>
        <el-table :data="histories" style="width: 100%">
          <el-table-column prop="createTime" label="时间" width="180">
            <template #default="scope">
              {{ formatHistoryTime(scope.row.createTimeTs) }}
            </template>
          </el-table-column>
          <el-table-column prop="kusaType" label="草种" width="120" />
          <el-table-column prop="kusaResult" label="草产量" width="100">
            <template #default="scope">
              <span class="kusa-amount">{{ formatNumber(scope.row.kusaResult) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="advKusaResult" label="草之精华" width="120">
            <template #default="scope">
              <span v-if="scope.row.advKusaResult > 0" class="adv-kusa-amount">{{ formatNumber(scope.row.advKusaResult) }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="histories.length === 0" description="暂无生草记录" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import api, { farmApi, farmWebSocket } from '@/api'
import type { KusaField, KusaHistory } from '@/types'
import { formatNumber } from '@/utils'
import { Refresh, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, onUnmounted, ref } from 'vue'

const kusaField = ref<KusaField | null>(null)
const histories = ref<KusaHistory[]>([])
const availableKusaTypes = ref<{name: string, displayName: string, available: boolean}[]>([])
const loading = ref(false)
const planting = ref(false)
const harvesting = ref(false)
const selectedKusaType = ref('草')
const hasOverloadMagic = ref(false)
const isDev = ref(false)

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

const formatHistoryTime = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

const formatOverloadEndTime = (isoString: string) => {
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 草之精华概率映射
const ADV_KUSA_PROBABILITY_DICT = { 0: 0, 1: 0.125, 2: 0.5, 3: 0.5, 4: 0.625 }

const getAdvKusaProbability = (level: number) => {
  const probability = ADV_KUSA_PROBABILITY_DICT[level] || 0
  const percentage = probability * 100
  return percentage
}

const refreshField = async () => {
  loading.value = true
  try {
    kusaField.value = await farmApi.getField()
    const historyData = await farmApi.getHistory()
    histories.value = historyData.slice(0, 5).map(item => ({
      kusaType: item.kusaType,
      kusaResult: item.kusaResult,
      advKusaResult: item.advKusaResult,
      createTimeTs: item.timestamp,
      createTime: new Date(item.timestamp * 1000).toISOString()
    }))
    const types = await farmApi.getAvailableKusaTypes()
    availableKusaTypes.value = types || []
    
    // 从 localStorage 读取上次选择的草种
    const lastType = localStorage.getItem('lastKusaType')
    if (lastType && availableKusaTypes.value.some(t => t.name === lastType)) {
      selectedKusaType.value = lastType
    } else if (availableKusaTypes.value.length > 0 && !availableKusaTypes.value.some(t => t.name === selectedKusaType.value)) {
      selectedKusaType.value = availableKusaTypes.value[0].name
    }
    await checkOverloadMagic()
  } catch (error: any) {
    console.error('获取生草地信息失败:', error)
    ElMessage.error('获取生草地信息失败，请检查网络连接或联系管理员')
  } finally {
    loading.value = false
  }
}

const checkOverloadMagic = async () => {
  try {
    const result = await farmApi.checkOverloadMagic()
    hasOverloadMagic.value = result.hasOverloadMagic
  } catch (error) {
    console.error('检查过载魔法失败:', error)
    hasOverloadMagic.value = false
  }
}

const checkAutoHarvest = async () => {
  if (farmWebSocket.isConnected()) {
    farmWebSocket.requestStatus()
  } else {
    await refreshField()
  }
}

const handleWebSocketMessage = (data: any) => {
  if (data) {
    console.log('收到 farm_status_update:', data)
    // 更新状态数据
    kusaField.value = { ...kusaField.value, ...data }
    console.log('更新后 isGrowing:', kusaField.value?.isGrowing)
  }
}

const handleKusaHarvested = (data: any) => {
  // 弹窗已在 websocket.ts 全局处理
  // 延迟更新以确保数据库已提交
  console.log('收到 kusa_harvested:', data)
  if (data) {
    // 立即更新显示收获结果
    kusaField.value = { ...kusaField.value, ...data }
    // 延迟500ms后刷新获取最新状态
    setTimeout(() => {
      refreshField()
    }, 500)
  }
}

const handlePlant = async () => {
  if (!selectedKusaType.value) {
    ElMessage.warning('请选择草种')
    return
  }

  planting.value = true
  try {
    const result = await farmApi.plantKusa(selectedKusaType.value, false)
    
    // 检查是否因灵性自动分配装置而改变了草种
    if (result.autoAssigned && result.kusaType === '不灵草') {
      ElMessage.success(`因灵性自动分配装置，自动选择了不灵草！预计${result.growTime}分钟后成熟`)
    } else {
      ElMessage.success(`开始生${result.kusaType}！预计${result.growTime}分钟后成熟`)
    }
    
    // 保存用户选择的草种（不是实际生的草种）
    localStorage.setItem('lastKusaType', selectedKusaType.value)
    await refreshField()
  } catch (error: any) {
    ElMessage.error(error.message || '生草失败')
  } finally {
    planting.value = false
  }
}

const handleHarvest = async () => {
  harvesting.value = true
  try {
    const result = await farmApi.harvestKusa()
    ElMessage.success('除草成功！草已清除')
    const lastType = localStorage.getItem('lastKusaType')
    if (lastType) {
      selectedKusaType.value = lastType
    }
    await refreshField()
  } catch (error: any) {
    ElMessage.error(error.message || '除草失败')
  } finally {
    harvesting.value = false
  }
}

const handleRecoverCapacity = async () => {
  try {
    const response = await api.post('/farm/test-recover-capacity', {})
    ElMessage.success(response.message || '承载力已恢复到25')
    await refreshField()
  } catch (error: any) {
    ElMessage.error(error.message || '恢复承载力失败')
  }
}

const handleReleaseSpareCapacity = async () => {
  try {
    const result = await farmApi.releaseSpareCapacity()
    ElMessage.success(result.message)
    await refreshField()
  } catch (error: any) {
    ElMessage.error(error.message || '释放后备承载力失败')
  }
}

const handleOverloadPlant = async () => {
  if (!selectedKusaType.value) {
    ElMessage.warning('请选择草种')
    return
  }

  planting.value = true
  try {
    const result = await farmApi.plantKusa(selectedKusaType.value, true)
    
    // 检查是否因灵性自动分配装置而改变了草种
    if (result.autoAssigned && result.kusaType === '不灵草') {
      ElMessage.success(`因灵性自动分配装置，自动选择了不灵草！开始过载生草！预计${result.growTime}分钟后成熟（过载中无法继续生草）`)
    } else {
      ElMessage.success(`开始过载生草！预计${result.growTime}分钟后成熟（过载中无法继续生草）`)
    }
    
    // 保存用户选择的草种（不是实际生的草种）
    localStorage.setItem('lastKusaType', selectedKusaType.value)
    await refreshField()
  } catch (error: any) {
    ElMessage.error(error.message || '过载生草失败')
  } finally {
    planting.value = false
  }
}

const fetchConfig = async () => {
  try {
    const response = await api.get('/config')
    isDev.value = response.isDev
  } catch (error) {
    console.error('获取配置失败:', error)
    isDev.value = false
  }
}

onMounted(() => {
  fetchConfig()
  refreshField()
  checkOverloadMagic()

  const userId = localStorage.getItem('userId')
  if (userId) {
    if (!farmWebSocket.isConnected()) {
      farmWebSocket.connect(userId)
    }
    farmWebSocket.on('farm_status_update', handleWebSocketMessage)
    farmWebSocket.on('farm_status', handleWebSocketMessage)
    farmWebSocket.on('kusa_harvested', handleKusaHarvested)
  }
})

onUnmounted(() => {
  // 只移除消息处理器，不断开 WebSocket 连接
  // 这样即使用户离开百草园页面，也能收到生草完毕的通知
  farmWebSocket.off('farm_status_update', handleWebSocketMessage)
  farmWebSocket.off('farm_status', handleWebSocketMessage)
  farmWebSocket.off('kusa_harvested', handleKusaHarvested)
})
</script>

<style scoped>
.farm-container {
  max-width: 800px;
  margin: 0 auto;
}

.farm-card {
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

.field-info {
  margin-bottom: 20px;
}

.field-info :deep(.el-descriptions-item__label) {
  white-space: nowrap;
  word-break: keep-all;
}

.bonus-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 4px 0;
}

.bonus-tags :deep(.el-tag) {
  margin: 0;
  line-height: 28px;
  height: 32px;
  padding: 0 14px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}

.bonus-tags :deep(.el-tag:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
}

.field-status {
  text-align: center;
}

.history-section h3 {
  margin-bottom: 16px;
  color: #333;
}

.kusa-amount {
  color: #67c23a;
  font-weight: bold;
}

.adv-kusa-amount {
  color: #e6a23c;
  font-weight: bold;
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
