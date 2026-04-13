<template>
  <div class="ability-container">
    <el-card v-if="warehouseInfo" class="ability-card">
      <template #header>
        <div class="card-header">
          <h2>能力与图纸</h2>
          <el-button @click="refreshWarehouse" circle size="default" style="width: 32px; height: 32px;">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 能力列表 -->
        <el-tab-pane label="能力列表" name="abilities">
          <div class="items-section">
            <div v-if="abilityItems.length > 0" class="items-grid">
              <el-card v-for="item in abilityItems" :key="item.item.name" class="item-card">
                <div class="item-header">
                  <div class="item-name">{{ item.item.name }}</div>
                  <el-switch 
                    v-if="item.item.isControllable" 
                    v-model="item.allowUse" 
                    active-color="#67c23a" 
                    inactive-color="#f56c6c"
                    @change="handleToggleItem(item)"
                  />
                </div>
                <div class="item-amount">× {{ item.amount }}</div>
                <div v-if="item.item.detail" class="item-detail">{{ item.item.detail }}</div>
              </el-card>
            </div>
            <el-empty v-else description="暂无能力" />
          </div>
        </el-tab-pane>

        <!-- 图纸列表 -->
        <el-tab-pane label="图纸列表" name="blueprints">
          <div class="items-section">
            <div v-if="blueprintItems.length > 0" class="items-grid">
              <el-card v-for="item in blueprintItems" :key="item.item.name" class="item-card">
                <div class="item-header">
                  <div class="item-name">{{ item.item.name }}</div>
                  <el-switch 
                    v-if="item.item.isControllable" 
                    v-model="item.allowUse" 
                    active-color="#67c23a" 
                    inactive-color="#f56c6c"
                    @change="handleToggleItem(item)"
                  />
                </div>
                <div class="item-amount">× {{ item.amount }}</div>
                <div v-if="item.item.detail" class="item-detail">{{ item.item.detail }}</div>
              </el-card>
            </div>
            <el-empty v-else description="暂无图纸" />
          </div>
        </el-tab-pane>

        <!-- 能力应用 -->
        <el-tab-pane label="能力应用" name="applications">
          <div class="applications-section">
            <!-- 草压缩 -->
            <el-card class="application-card" :class="{ 'locked': !hasCompressBase }">
              <template #header>
                <div class="app-header">
                  <span class="app-title">草压缩</span>
                  <el-tag v-if="!hasCompressBase" type="danger">未解锁</el-tag>
                  <el-tag v-else type="success">已解锁</el-tag>
                </div>
              </template>
              
              <div v-if="!hasCompressBase" class="locked-content">
                <el-empty description="需要草压缩基地才能使用此功能">
                  <template #image>
                    <el-icon :size="60" color="#909399"><Lock /></el-icon>
                  </template>
                </el-empty>
              </div>
              
              <div v-else class="app-content">
                <div class="app-description">
                  将普通草压缩成草之精华
                  <div class="cost-info">消耗：100万草 → 1草之精华</div>
                </div>
                
                <div class="current-amount">
                  当前草量：<span class="amount-value">{{ formatNumber(userKusa) }}</span>
                  <span class="max-hint">（最多可压缩 {{ formatNumber(maxCompressAmount) }} 个）</span>
                </div>
                
                <div class="app-form">
                  <div class="amount-control">
                    <el-input-number 
                      v-model="compressAmount" 
                      :min="1" 
                      :max="Math.max(1, maxCompressAmount)"
                      controls-position="right"
                      style="width: 120px"
                    />
                    <el-button 
                      type="primary" 
                      plain
                      @click="setCompressMax"
                      :disabled="maxCompressAmount < 1"
                    >
                      Max
                    </el-button>
                  </div>
                  <el-button 
                    type="primary" 
                    @click="confirmCompress"
                    :loading="compressLoading"
                    :disabled="maxCompressAmount < 1 || compressAmount > maxCompressAmount"
                  >
                    压缩
                  </el-button>
                </div>
                
                <div class="cost-preview">
                  <div class="preview-item">
                    <span class="preview-label">预计消耗：</span>
                    <span class="preview-value cost">{{ formatNumber(compressAmount * 1000000) }} 草</span>
                  </div>
                  <div class="preview-item">
                    <span class="preview-label">预计获得：</span>
                    <span class="preview-value gain">{{ compressAmount }} 草之精华</span>
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 奖券合成 -->
            <el-card class="application-card" :class="{ 'locked': !hasLotteryMachine }">
              <template #header>
                <div class="app-header">
                  <span class="app-title">奖券合成</span>
                  <el-tag v-if="!hasLotteryMachine" type="danger">未解锁</el-tag>
                  <el-tag v-else type="success">已解锁</el-tag>
                </div>
              </template>
              
              <div v-if="!hasLotteryMachine" class="locked-content">
                <el-empty description="需要奖券合成机才能使用此功能">
                  <template #image>
                    <el-icon :size="60" color="#909399"><Lock /></el-icon>
                  </template>
                </el-empty>
              </div>
              
              <div v-else class="app-content">
                <div class="app-description">
                  将低级奖券合成为高级奖券
                  <div class="cost-info">消耗：10个低级奖券 → 1个高级奖券</div>
                </div>
                
                <div class="compose-rules">
                  <div class="rule-item" :class="{ 'active': composeTarget === '高级十连券' }">
                    <div class="rule-material">
                      <span class="material-name">十连券</span>
                      <span class="material-amount" :class="{ 'insufficient': getItemAmount('十连券') < 10 }">
                        (当前: {{ getItemAmount('十连券') }})
                      </span>
                    </div>
                    <el-icon class="rule-arrow"><ArrowRight /></el-icon>
                    <div class="rule-result">高级十连券</div>
                  </div>
                  <div class="rule-item" :class="{ 'active': composeTarget === '特级十连券' }">
                    <div class="rule-material">
                      <span class="material-name">高级十连券</span>
                      <span class="material-amount" :class="{ 'insufficient': getItemAmount('高级十连券') < 10 }">
                        (当前: {{ getItemAmount('高级十连券') }})
                      </span>
                    </div>
                    <el-icon class="rule-arrow"><ArrowRight /></el-icon>
                    <div class="rule-result">特级十连券</div>
                  </div>
                  <div class="rule-item" :class="{ 'active': composeTarget === '天琴十连券' }">
                    <div class="rule-material">
                      <span class="material-name">特级十连券</span>
                      <span class="material-amount" :class="{ 'insufficient': getItemAmount('特级十连券') < 10 }">
                        (当前: {{ getItemAmount('特级十连券') }})
                      </span>
                    </div>
                    <el-icon class="rule-arrow"><ArrowRight /></el-icon>
                    <div class="rule-result">天琴十连券</div>
                  </div>
                </div>
                
                <div class="app-form">
                  <el-select v-model="composeTarget" placeholder="选择合成目标" style="width: 160px">
                    <el-option 
                      label="高级十连券" 
                      value="高级十连券" 
                      :disabled="getItemAmount('十连券') < 10"
                    />
                    <el-option 
                      label="特级十连券" 
                      value="特级十连券" 
                      :disabled="getItemAmount('高级十连券') < 10"
                    />
                    <el-option 
                      label="天琴十连券" 
                      value="天琴十连券" 
                      :disabled="getItemAmount('特级十连券') < 10"
                    />
                  </el-select>
                  
                  <div class="amount-control">
                    <el-input-number 
                      v-model="composeAmount" 
                      :min="1"
                      :max="Math.max(1, maxComposeAmount)"
                      controls-position="right"
                      style="width: 120px"
                    />
                    <el-button 
                      type="primary" 
                      plain
                      @click="setComposeMax"
                      :disabled="!composeTarget || maxComposeAmount < 1"
                    >
                      Max
                    </el-button>
                  </div>
                  
                  <el-button 
                    type="primary" 
                    @click="confirmCompose"
                    :loading="composeLoading"
                    :disabled="!composeTarget || maxComposeAmount < 1"
                  >
                    合成
                  </el-button>
                </div>
                
                <div class="cost-preview" v-if="composeTarget">
                  <div class="preview-item">
                    <span class="preview-label">预计消耗：</span>
                    <span class="preview-value cost">{{ getComposeSourceName(composeTarget) }} × {{ composeAmount * 10 }}</span>
                  </div>
                  <div class="preview-item">
                    <span class="preview-label">预计获得：</span>
                    <span class="preview-value gain">{{ composeTarget }} × {{ composeAmount }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { itemApi, warehouseApi } from '@/api'
import type { UserItem, WarehouseInfo } from '@/types'
import { ArrowRight, Lock, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'

const warehouseInfo = ref<WarehouseInfo | null>(null)
const loading = ref(false)
const activeTab = ref('abilities')

// 草压缩相关
const compressAmount = ref(1)
const compressLoading = ref(false)

// 奖券合成相关
const composeTarget = ref('')
const composeAmount = ref(1)
const composeLoading = ref(false)

const abilityItems = computed(() => {
  if (!warehouseInfo.value) return []
  return warehouseInfo.value.items.filter(item => item.item.type === '能力')
})

const blueprintItems = computed(() => {
  if (!warehouseInfo.value) return []
  return warehouseInfo.value.items.filter(item => item.item.type === '图纸')
})

// 检查是否有草压缩基地
const hasCompressBase = computed(() => {
  if (!warehouseInfo.value) return false
  const baseItem = warehouseInfo.value.items.find(item => item.item.name === '草压缩基地')
  return baseItem && baseItem.amount > 0
})

// 检查是否有奖券合成机
const hasLotteryMachine = computed(() => {
  if (!warehouseInfo.value) return false
  const machineItem = warehouseInfo.value.items.find(item => item.item.name === '奖券合成机')
  return machineItem && machineItem.amount > 0
})

// 获取用户草数量
const userKusa = computed(() => {
  if (!warehouseInfo.value || !warehouseInfo.value.user) return 0
  return warehouseInfo.value.user.kusa || 0
})

// 最大可压缩数量
const maxCompressAmount = computed(() => {
  return Math.floor(userKusa.value / 1000000)
})

// 获取物品数量
const getItemAmount = (itemName: string): number => {
  if (!warehouseInfo.value) return 0
  const item = warehouseInfo.value.items.find(i => i.item.name === itemName)
  return item ? item.amount : 0
}

// 最大可合成数量
const maxComposeAmount = computed(() => {
  if (!composeTarget.value) return 0
  const sourceMap: Record<string, string> = {
    '高级十连券': '十连券',
    '特级十连券': '高级十连券',
    '天琴十连券': '特级十连券'
  }
  const source = sourceMap[composeTarget.value]
  if (!source) return 0
  const sourceAmount = getItemAmount(source)
  return Math.floor(sourceAmount / 10)
})

// 监听合成目标变化，重置数量
watch(composeTarget, () => {
  composeAmount.value = 1
})

const refreshWarehouse = async () => {
  loading.value = true
  try {
    warehouseInfo.value = await warehouseApi.getWarehouse()
  } catch (error) {
    ElMessage.error('获取能力信息失败')
  } finally {
    loading.value = false
  }
}

const handleToggleItem = async (item: UserItem) => {
  try {
    await itemApi.toggleItem(item.item.name, item.allowUse)
    ElMessage.success(`${item.item.name}已${item.allowUse ? '启用' : '禁用'}`)
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
    item.allowUse = !item.allowUse
  }
}

// 设置草压缩数量为最大
const setCompressMax = () => {
  compressAmount.value = Math.max(1, maxCompressAmount.value)
}

// 确认草压缩
const confirmCompress = async () => {
  if (compressAmount.value > maxCompressAmount.value) {
    ElMessage.error('草不足')
    return
  }
  
  // 大规模消耗时二次确认（超过总草量的1/3）
  if (compressAmount.value * 1000000 >= userKusa.value / 3) {
    try {
      await ElMessageBox.confirm(
        `确定要压缩 ${compressAmount.value} 个草之精华吗？\n将消耗 ${formatNumber(compressAmount.value * 1000000)} 草`,
        '确认压缩',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }
  
  await handleCompress()
}

// 草压缩
const handleCompress = async () => {
  compressLoading.value = true
  try {
    const response = await warehouseApi.compressKusa(compressAmount.value)
    if (response.success) {
      ElMessage.success(response.message)
      compressAmount.value = 1
      await refreshWarehouse()
    } else {
      ElMessage.error(response.message || '压缩失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '压缩失败')
  } finally {
    compressLoading.value = false
  }
}

// 获取合成源奖券名称
const getComposeSourceName = (target: string): string => {
  const map: Record<string, string> = {
    '高级十连券': '十连券',
    '特级十连券': '高级十连券',
    '天琴十连券': '特级十连券'
  }
  return map[target] || ''
}

// 设置奖券合成数量为最大
const setComposeMax = () => {
  composeAmount.value = Math.max(1, maxComposeAmount.value)
}

// 确认奖券合成
const confirmCompose = async () => {
  if (!composeTarget.value) {
    ElMessage.warning('请选择合成目标')
    return
  }
  
  if (composeAmount.value > maxComposeAmount.value) {
    ElMessage.error(`${getComposeSourceName(composeTarget.value)}不足`)
    return
  }
  
  // 大规模合成时二次确认（超过材料总量的1/3）
  const sourceAmount = getItemAmount(getComposeSourceName(composeTarget.value))
  if (composeAmount.value * 10 >= sourceAmount / 3) {
    try {
      await ElMessageBox.confirm(
        `确定要合成 ${composeAmount.value} 个${composeTarget.value}吗？\n将消耗 ${getComposeSourceName(composeTarget.value)} × ${composeAmount.value * 10}`,
        '确认合成',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }
  
  await handleCompose()
}

// 奖券合成
const handleCompose = async () => {
  composeLoading.value = true
  try {
    const response = await itemApi.composeTicket(composeTarget.value, composeAmount.value)
    if (response.success) {
      ElMessage.success(response.message)
      composeAmount.value = 1
      await refreshWarehouse()
    } else {
      ElMessage.error(response.message || '合成失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '合成失败')
  } finally {
    composeLoading.value = false
  }
}

const formatNumber = (num: number): string => {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + '亿'
  } else if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

onMounted(() => {
  refreshWarehouse()
})
</script>

<style scoped>
.ability-container {
  max-width: 1000px;
  margin: 0 auto;
}

.ability-card {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.currency-tag {
  font-size: 14px;
}

.items-section {
  padding: 16px 0;
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.item-card {
  transition: transform 0.2s;
}

.item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-name {
  font-weight: bold;
  font-size: 16px;
  color: #333;
}

.item-amount {
  color: #409eff;
  font-size: 14px;
  margin-bottom: 8px;
}

.item-detail {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

/* 能力应用样式 */
.applications-section {
  padding: 16px;
}

.application-card {
  margin-bottom: 20px;
}

.application-card.locked {
  opacity: 0.7;
  background-color: #f5f7fa;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-title {
  font-size: 16px;
  font-weight: bold;
}

.locked-content {
  padding: 20px 0;
}

.app-content {
  padding: 10px 0;
}

.app-description {
  margin-bottom: 16px;
  color: #606266;
  line-height: 1.6;
}

.cost-info {
  color: #f56c6c;
  font-size: 13px;
  margin-top: 4px;
}

.current-amount {
  margin-bottom: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
}

.amount-value {
  font-weight: bold;
  color: #409eff;
}

.max-hint {
  color: #909399;
  margin-left: 8px;
}

.app-form {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.amount-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.amount-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  font-size: 16px;
}

.amount-input {
  width: 100px;
}

.max-btn {
  margin-left: 8px;
}

.cost-preview {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
}

.preview-item {
  margin-bottom: 4px;
}

.preview-item:last-child {
  margin-bottom: 0;
}

.preview-label {
  color: #606266;
}

.preview-value {
  font-weight: bold;
}

.preview-value.cost {
  color: #f56c6c;
}

.preview-value.gain {
  color: #67c23a;
}

/* 合成规则样式 */
.compose-rules {
  margin-bottom: 16px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
  transition: all 0.3s;
}

.rule-item.active {
  background-color: #ecf5ff;
  border-left: 4px solid #409eff;
}

.rule-material {
  flex: 1;
}

.material-name {
  font-weight: bold;
  color: #333;
}

.material-amount {
  margin-left: 8px;
  color: #67c23a;
  font-size: 13px;
}

.material-amount.insufficient {
  color: #f56c6c;
}

.rule-arrow {
  color: #909399;
}

.rule-result {
  font-weight: bold;
  color: #409eff;
}

@media screen and (max-width: 600px) {
  .items-grid {
    grid-template-columns: 1fr;
  }
  
  .app-form {
    flex-direction: column;
    align-items: stretch;
  }
  
  .amount-control {
    justify-content: center;
  }
  
  .app-form .el-button[type="primary"]:not(.amount-btn):not(.max-btn) {
    width: 100%;
  }
  
  .rule-item {
    flex-direction: column;
    text-align: center;
  }
  
  .rule-arrow {
    transform: rotate(90deg);
  }
}
</style>
