<template>
  <div class="warehouse-container">
    <el-card v-if="warehouseInfo" class="warehouse-card">
      <template #header>
        <div class="card-header">
          <h2>仓库</h2>
          <div class="header-actions">
            <el-button @click="refreshWarehouse" circle size="default" style="width: 32px; height: 32px;">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button @click="showUpgradeDialog" type="primary" size="small">
              <el-icon><Star /></el-icon>
              信息员升级
            </el-button>
          </div>
        </div>
      </template>

      <div class="user-summary">
        <el-descriptions :column="2" border class="responsive-descriptions">
          <el-descriptions-item label="QQ号">{{ warehouseInfo.user.qq }}</el-descriptions-item>
          <el-descriptions-item label="昵称">
            {{ warehouseInfo.user.name || '未设置' }}
            <el-button type="primary" size="small" @click="showRenameDialog" style="margin-left: 8px">改名</el-button>
          </el-descriptions-item>
          <el-descriptions-item label="称号">
            {{ warehouseInfo.user.title || '无' }}
            <el-button 
              v-if="availableTitles.length > 1" 
              type="primary" 
              size="small" 
              @click="showTitleDialog" 
              style="margin-left: 8px"
            >
              切换称号
            </el-button>
          </el-descriptions-item>
          <el-descriptions-item label="信息员等级">
            {{ getVipTitle(warehouseInfo.user.vipLevel) }} Lv{{ warehouseInfo.user.vipLevel }}
          </el-descriptions-item>
          <el-descriptions-item label="草数量" :span="2">
            <div class="kusa-display-row">
              <span>{{ formatNumber(warehouseInfo.user.kusa) }}</span>
              <el-button
                v-if="warehouseInfo.user.kusa > 0"
                type="primary"
                size="small"
                @click="showTransferKusaDialog"
              >
                转让
              </el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item v-if="warehouseInfo.user.advKusa > 0" label="草之精华">
            {{ formatNumber(warehouseInfo.user.advKusa) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <el-divider />

      <div class="items-section">
        <h3>财产</h3>
        <div v-if="propertyItems.length > 0" class="items-grid">
          <el-card v-for="item in propertyItems" :key="item.item.name" class="item-card">
            <div class="item-name">{{ item.item.name }}</div>
            <div class="item-amount">× {{ item.amount }}</div>
            <div v-if="item.item.detail" class="item-detail">{{ item.item.detail }}</div>
            <el-button
              v-if="item.item.isTransferable"
              type="primary"
              size="small"
              style="margin-top: 8px"
              @click="showTransferItemDialog(item)"
            >
              转让
            </el-button>
          </el-card>
        </div>
        <el-empty v-else description="暂无财产" />
      </div>

      <el-divider />

      <div class="items-section">
        <h3>道具</h3>
        <div v-if="useableItems.length > 0" class="items-grid">
          <el-card v-for="item in useableItems" :key="item.item.name" class="item-card">
            <div class="item-name">{{ item.item.name }}</div>
            <div class="item-amount">× {{ item.amount }}</div>
            <div v-if="item.item.detail" class="item-detail">{{ item.item.detail }}</div>
            <el-button
              v-if="item.item.isTransferable"
              type="primary"
              size="small"
              style="margin-top: 8px"
              @click="showTransferItemDialog(item)"
            >
              转让
            </el-button>
          </el-card>
        </div>
        <el-empty v-else description="暂无道具" />
      </div>
    </el-card>

    <el-dialog v-model="upgradeDialogVisible" title="信息员升级" width="500px">
      <div v-if="warehouseInfo">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="当前等级">
            {{ getVipTitle(warehouseInfo.user.vipLevel) }} Lv{{ warehouseInfo.user.vipLevel }}
          </el-descriptions-item>
          <el-descriptions-item label="下一等级">
            {{ getVipTitle(warehouseInfo.user.vipLevel + 1) }} Lv{{ warehouseInfo.user.vipLevel + 1 }}
          </el-descriptions-item>
          <el-descriptions-item label="升级消耗">
            <div v-if="warehouseInfo.user.vipLevel < 4">
              <span class="total-label">总价:</span>
              <span class="total-value">{{ formatNumber(getUpgradeCost(warehouseInfo.user.vipLevel + 1)) }}</span>
              <span class="price-type">草</span>
            </div>
            <div v-else-if="warehouseInfo.user.vipLevel < 8">
              <span class="total-label">总价:</span>
              <span class="total-value">{{ formatNumber(getAdvancedUpgradeCost(warehouseInfo.user.vipLevel + 1)) }}</span>
              <span class="price-type">草之精华</span>
            </div>
            <div v-else>
              <el-tag type="info">已达到最高等级</el-tag>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="生草加成">
            <el-tag type="info">+{{ getKusaBonus(warehouseInfo.user.vipLevel) }} → +{{ getKusaBonus(warehouseInfo.user.vipLevel + 1) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="upgradeDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            @click="handleUpgrade"
            :loading="upgrading"
            :disabled="warehouseInfo?.user.vipLevel >= 8 || (warehouseInfo?.user.vipLevel < 4 && warehouseInfo?.user.kusa < getUpgradeCost(warehouseInfo.user.vipLevel + 1)) || (warehouseInfo?.user.vipLevel >= 4 && warehouseInfo?.user.vipLevel < 8 && warehouseInfo?.user.advKusa < getAdvancedUpgradeCost(warehouseInfo.user.vipLevel + 1))"
          >
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="titleDialogVisible" title="切换称号" width="500px">
      <div v-if="availableTitles.length > 0" class="titles-grid">
        <el-card 
          v-for="title in availableTitles" 
          :key="title" 
          class="title-card"
          :class="{ 'title-selected': title === warehouseInfo?.user.title }"
          @click="handleSelectTitle(title)"
        >
          <div class="title-name">{{ title }}</div>
        </el-card>
      </div>
      <el-empty v-else description="暂无可用称号" />
      <template #footer>
        <el-button @click="titleDialogVisible = false">取消</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="renameDialogVisible" title="改名" width="400px">
      <el-form :model="renameForm" label-width="80px" @submit.prevent="handleRename">
        <el-form-item label="新名字">
          <el-input v-model="renameForm.name" placeholder="请输入新名字" maxlength="20" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="renameDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleRename" :loading="renaming">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="transferDialogVisible"
      :title="transferMode === 'kusa' ? '转让草' : '转让物品'"
      width="480px"
    >
      <el-form label-width="90px">
        <el-form-item label="转让内容">
          <el-tag v-if="transferMode === 'kusa'" type="success">草（最多 {{ formatNumber(transferMax) }}）</el-tag>
          <el-tag v-else type="success">{{ transferItemName }}（最多 {{ formatNumber(transferMax) }}）</el-tag>
        </el-form-item>
        <el-form-item label="接收方">
          <div class="transfer-target-row">
            <el-input
              v-model="transferForm.target"
              placeholder="请输入接收方QQ号"
              @input="transferTargetInfo = null"
              @keyup.enter="handleResolveTarget"
            />
            <el-button :loading="resolvingTarget" @click="handleResolveTarget">查询</el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="transferTargetInfo" label="接收方确认" class="transfer-confirm-item">
          <el-alert type="success" :closable="false">
            {{ transferTargetInfo.name || '未设置昵称' }}（QQ: {{ transferTargetInfo.qq || '未绑定' }}，ID: {{ transferTargetInfo.userId }}）
          </el-alert>
        </el-form-item>
        <el-form-item label="数量">
          <el-input
            v-if="transferMode === 'kusa'"
            v-model.number="transferForm.amount"
            type="number"
            :min="1"
            :max="transferMax"
            placeholder="请输入数量"
            @blur="clampTransferAmount"
          />
          <el-input-number
            v-else
            v-model="transferForm.amount"
            :min="1"
            :max="transferMax"
            style="width: 160px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="transferDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="transferring"
            :disabled="!transferTargetInfo"
            @click="handleTransfer"
          >
            确认转让
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { itemApi, vipApi, warehouseApi } from '@/api'
import type { WarehouseInfo } from '@/types'
import { Refresh, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

const warehouseInfo = ref<WarehouseInfo | null>(null)
const loading = ref(false)
const upgrading = ref(false)
const upgradingAdvanced = ref(false)
const upgradeDialogVisible = ref(false)
const titleDialogVisible = ref(false)
const renameDialogVisible = ref(false)
const renaming = ref(false)
const renameForm = ref({ name: '' })
const availableTitles = ref<string[]>([])

const transferDialogVisible = ref(false)
const transferMode = ref<'kusa' | 'item'>('kusa')
const transferForm = ref({ target: '', amount: 1 })
const transferTargetInfo = ref<{ userId: number; qq: string | null; name: string | null } | null>(null)
const transferItemName = ref('')
const transferMax = ref(1)
const resolvingTarget = ref(false)
const transferring = ref(false)

const propertyItems = computed(() => {
  if (!warehouseInfo.value) return []
  return warehouseInfo.value.items.filter(item => item.item.type === '财产' || item.item.type === 'G')
})

const useableItems = computed(() => {
  if (!warehouseInfo.value) return []
  return warehouseInfo.value.items.filter(item => item.item.type === '道具')
})

// 能力和图纸已移至能力页面
// const blueprintItems = computed(() => {
//   if (!warehouseInfo.value) return []
//   return warehouseInfo.value.items.filter(item => item.item.type === '图纸')
// })

// const abilityItems = computed(() => {
//   if (!warehouseInfo.value) return []
//   return warehouseInfo.value.items.filter(item => item.item.type === '能力')
// })

const formatNumber = (num: number) => {
  return num.toLocaleString()
}

const getVipTitle = (level: number) => {
  const titles = ['用户', '信息员', '高级信息员', '特级信息员', '后浪信息员', '天琴信息员', '天琴信息节点', '天琴信息矩阵', '天琴信息网络']
  return titles[level] || '用户'
}

const getUpgradeCost = (newLevel: number) => {
  return 50 * (10 ** newLevel)
}

const getAdvancedUpgradeCost = (newLevel: number) => {
  return 10 ** (newLevel - 4)
}

const getKusaBonus = (level: number) => {
  if (level === 0) return 0
  return 0.5 * (2 ** (level - 1))
}

const refreshWarehouse = async () => {
  loading.value = true
  try {
    warehouseInfo.value = await warehouseApi.getWarehouse()
    await loadTitles()
  } catch (error) {
    ElMessage.error('获取仓库信息失败')
  } finally {
    loading.value = false
  }
}

const showUpgradeDialog = () => {
  upgradeDialogVisible.value = true
}

const loadTitles = async () => {
  try {
    const response = await warehouseApi.getItemsByType('称号')
    availableTitles.value = response.map((item: any) => item.name)
  } catch (error) {
    console.error('获取称号列表失败:', error)
  }
}

const showTitleDialog = async () => {
  try {
    await loadTitles()
    titleDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取称号列表失败')
  }
}

const handleSelectTitle = async (title: string) => {
  try {
    await warehouseApi.updateTitle(title)
    ElMessage.success(`已切换为称号：${title}`)
    if (warehouseInfo.value) {
      warehouseInfo.value.user.title = title
    }
    titleDialogVisible.value = false
  } catch (error: any) {
    ElMessage.error(error.message || '切换称号失败')
  }
}

const showRenameDialog = () => {
  renameForm.value.name = warehouseInfo.value?.user.name || ''
  renameDialogVisible.value = true
}

const handleRename = async () => {
  if (!renameForm.value.name.trim()) {
    ElMessage.warning('请输入名字')
    return
  }
  
  renaming.value = true
  try {
    await warehouseApi.updateName(renameForm.value.name)
    ElMessage.success('改名成功')
    if (warehouseInfo.value) {
      warehouseInfo.value.user.name = renameForm.value.name
    }
    renameDialogVisible.value = false
  } catch (error: any) {
    ElMessage.error(error.message || '改名失败')
  } finally {
    renaming.value = false
  }
}

const handleUpgrade = async () => {
  if (!warehouseInfo.value) return

  upgrading.value = true
  try {
    if (warehouseInfo.value.user.vipLevel < 4) {
      const result = await vipApi.upgrade()
      ElMessage.success(result.message)
      warehouseInfo.value.user.vipLevel = result.newLevel
      warehouseInfo.value.user.kusa -= result.costKusa
    } else if (warehouseInfo.value.user.vipLevel < 8) {
      const result = await vipApi.advancedUpgrade()
      ElMessage.success(result.message)
      warehouseInfo.value.user.vipLevel = result.newLevel
      warehouseInfo.value.user.advKusa -= result.costAdvPoint
    }
    upgradeDialogVisible.value = false
  } catch (error: any) {
    ElMessage.error(error.message || '升级失败')
  } finally {
    upgrading.value = false
  }
}

const showTransferKusaDialog = () => {
  if (!warehouseInfo.value) return
  transferMode.value = 'kusa'
  transferItemName.value = ''
  transferMax.value = warehouseInfo.value.user.kusa
  openTransferDialog()
}

const showTransferItemDialog = (item: any) => {
  transferMode.value = 'item'
  transferItemName.value = item.item.name
  transferMax.value = item.amount
  openTransferDialog()
}

const openTransferDialog = () => {
  transferForm.value = { target: '', amount: 1 }
  transferTargetInfo.value = null
  transferDialogVisible.value = true
}

const clampTransferAmount = () => {
  let amount = Number(transferForm.value.amount)
  if (isNaN(amount) || amount < 1) amount = 1
  if (amount > transferMax.value) amount = transferMax.value
  transferForm.value.amount = amount
}

const handleResolveTarget = async () => {
  const raw = transferForm.value.target.trim()
  if (!raw) {
    ElMessage.warning('请输入接收方QQ号')
    return
  }
  if (!/^\d+$/.test(raw)) {
    ElMessage.warning('QQ号只能填数字')
    return
  }

  resolvingTarget.value = true
  try {
    transferTargetInfo.value = await warehouseApi.resolveTransferTarget({ targetQq: raw })
    ElMessage.success('接收方已确认')
  } catch (error: any) {
    transferTargetInfo.value = null
    ElMessage.error(error.message || '查询接收方失败')
  } finally {
    resolvingTarget.value = false
  }
}

const handleTransfer = async () => {
  if (!warehouseInfo.value || !transferTargetInfo.value) return

  const amount = transferForm.value.amount
  if (!amount || amount <= 0) {
    ElMessage.warning('请输入正确的数量')
    return
  }
  if (amount > transferMax.value) {
    ElMessage.warning(`最多可转让 ${transferMax.value}`)
    return
  }

  transferring.value = true
  try {
    if (transferMode.value === 'kusa') {
      await warehouseApi.transferKusa({ targetUserId: transferTargetInfo.value.userId, amount })
    } else {
      await itemApi.transferItem({
        targetUserId: transferTargetInfo.value.userId,
        itemName: transferItemName.value,
        amount
      })
    }
    ElMessage.success('转让成功')
    transferDialogVisible.value = false
    await refreshWarehouse()
  } catch (error: any) {
    ElMessage.error(error.message || '转让失败')
  } finally {
    transferring.value = false
  }
}

onMounted(() => {
  refreshWarehouse()
})
</script>

<style scoped>
.warehouse-container {
  max-width: 1000px;
  margin: 0 auto;
}

.warehouse-card {
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

.user-summary {
  margin-bottom: 20px;
}

.items-section h3 {
  margin-bottom: 16px;
  color: #333;
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.item-card {
  text-align: center;
  transition: transform 0.2s;
}

.item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.item-name {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 8px;
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

.total-label {
  color: #666;
  margin-right: 8px;
}

.transfer-target-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.warehouse-card :deep(.el-descriptions__cell) {
  vertical-align: middle;
}

.kusa-display-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kusa-display-row span {
  line-height: 1;
}

.transfer-confirm-item {
  align-items: center;
}

.transfer-confirm-item :deep(.el-alert) {
  width: 100%;
  margin: 0;
}

.total-value {
  color: #f56c6c;
  font-weight: bold;
  margin-right: 8px;
}

.price-type {
  color: #666;
}

.titles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}

.title-card {
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.title-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.title-selected {
  border: 2px solid #409eff;
  background: #ecf5ff;
}

.title-name {
  font-weight: bold;
  font-size: 14px;
  color: #333;
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
