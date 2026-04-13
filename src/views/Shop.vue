<template>
  <div class="shop-container">
    <el-card class="shop-card">
      <template #header>
        <div class="card-header">
          <h2>商店</h2>
          <div class="header-left">
            <el-switch v-model="showUnsatisfiedItems" active-text="全部展示" inactive-text="" />
          </div>
          <div class="header-actions">
            <el-tag type="success" size="default" class="currency-tag">
              草: {{ formatNumber(userInfo?.kusa || 0) }}
            </el-tag>
            <el-tag v-if="userInfo?.advKusa > 0" type="warning" size="default" class="currency-tag">
              草精: {{ formatNumber(userInfo?.advKusa || 0) }}
            </el-tag>
            <el-tag v-if="getCurrentAmount('自动化核心') > 0" type="info" size="default" class="currency-tag">
              核心: {{ formatNumber(getCurrentAmount('自动化核心')) }}
            </el-tag>
            <el-button @click="refreshShop" circle size="default" style="width: 32px; height: 32px;">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
      </template>

      <div class="shop-tabs">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="财产" name="property">
            <div class="items-grid" v-if="activeTab === 'property' && propertyItems.length > 0">
              <el-card v-for="item in propertyItems" :key="'property-' + item.name" class="shop-item" :class="{ 'at-limit': showUnsatisfiedItems && isAtLimit(item) }">
                <div class="item-header">
                  <div class="item-name">
                    {{ item.name }}
                    <span class="item-amount">({{ getCurrentAmount(item.name) }}{{ item.amountLimit ? `/${item.amountLimit}` : '' }})</span>
                    <el-tag v-if="showUnsatisfiedItems && isAtLimit(item)" type="warning" size="small" class="limit-tag">已达上限</el-tag>
                  </div>
                </div>
                <div v-if="item.detail" class="item-detail">{{ item.detail }}</div>
                <div v-if="item.shopPreItems" class="item-preitems">
                  <el-tag type="warning" size="small" v-for="preItem in getPreItems(item.shopPreItems)" :key="preItem">
                    需要: {{ preItem }}
                  </el-tag>
                </div>
                <div class="item-actions">
                  <div class="amount-control">
                    <el-input-number
                      v-model="buyAmounts[item.name]"
                      :min="1"
                      :max="Math.max(1, getMaxBuyAmount(item))"
                      :disabled="getMaxBuyAmount(item) === 0"
                      size="small"
                      style="width: 120px;"
                      @change="() => calculatePrice(item)"
                    />
                    <el-button size="small" class="max-btn" @click="setBuyAmountToMax(item)" :disabled="isAtLimit(item) || getMaxBuyAmount(item) === 0">Max</el-button>
                  </div>
                  <div class="button-group">
                    <el-button
                      type="primary"
                      size="small"
                      @click="handleBuy(item)"
                      :loading="buying[item.name]"
                      :disabled="!isSatisfied(item) || isAtLimit(item) || !hasEnoughCurrency(item) || getMaxBuyAmount(item) === 0"
                    >
                      购买
                    </el-button>
                  </div>
                </div>
                <div class="item-total-price">
                  <span class="total-label">总价:</span>
                  <span class="total-value">{{ formatNumber(getTotalPrice(item)) }}</span>
                  <span class="price-type">{{ getPriceType(item) }}</span>
                </div>
              </el-card>
            </div>
            <el-empty v-if="activeTab === 'property' && propertyItems.length === 0" description="暂无可购买的财产" />
          </el-tab-pane>

          <el-tab-pane label="道具" name="items">
            <div class="items-grid" v-if="activeTab === 'items' && useableItems.length > 0">
              <el-card v-for="item in useableItems" :key="'items-' + item.name" class="shop-item" :class="{ 'at-limit': showUnsatisfiedItems && isAtLimit(item) }">
                <div class="item-header">
                  <div class="item-name">
                    {{ item.name }}
                    <span class="item-amount">({{ getCurrentAmount(item.name) }}{{ item.amountLimit ? `/${item.amountLimit}` : '' }})</span>
                    <el-tag v-if="showUnsatisfiedItems && isAtLimit(item)" type="warning" size="small" class="limit-tag">已达上限</el-tag>
                  </div>
                </div>
                <div v-if="item.detail" class="item-detail">{{ item.detail }}</div>
                <div class="item-actions">
                  <div class="amount-control">
                    <el-input-number
                      v-model="buyAmounts[item.name]"
                      :min="1"
                      :max="Math.max(1, getMaxBuyAmount(item))"
                      :disabled="getMaxBuyAmount(item) === 0"
                      size="small"
                      style="width: 120px;"
                      @change="() => calculatePrice(item)"
                    />
                    <el-button size="small" class="max-btn" @click="setBuyAmountToMax(item)" :disabled="isAtLimit(item) || getMaxBuyAmount(item) === 0">Max</el-button>
                  </div>
                  <div class="button-group">
                    <el-button
                      type="primary"
                      size="small"
                      @click="handleBuy(item)"
                      :loading="buying[item.name]"
                      :disabled="!isSatisfied(item) || isAtLimit(item) || !hasEnoughCurrency(item) || getMaxBuyAmount(item) === 0"
                    >
                      购买
                    </el-button>
                  </div>
                </div>
                <div class="item-total-price">
                  <span class="total-label">总价:</span>
                  <span class="total-value">{{ formatNumber(getTotalPrice(item)) }}</span>
                  <span class="price-type">{{ item.priceType }}</span>
                </div>
              </el-card>
            </div>
            <el-empty v-if="activeTab === 'items' && useableItems.length === 0" description="暂无可购买的道具" />
          </el-tab-pane>

          <el-tab-pane label="图纸" name="blueprints">
            <div class="items-grid" v-if="activeTab === 'blueprints' && blueprintItems.length > 0">
              <el-card v-for="item in blueprintItems" :key="'blueprints-' + item.name" class="shop-item" :class="{ 'at-limit': showUnsatisfiedItems && isAtLimit(item) }">
                <div class="item-header">
                  <div class="item-name">
                    {{ item.name }}
                    <span class="item-amount">({{ getCurrentAmount(item.name) }}{{ item.amountLimit ? `/${item.amountLimit}` : '' }})</span>
                    <el-tag v-if="showUnsatisfiedItems && isAtLimit(item)" type="warning" size="small" class="limit-tag">已达上限</el-tag>
                  </div>
                </div>
                <div v-if="item.detail" class="item-detail">{{ item.detail }}</div>
                <div class="item-actions">
                  <div class="amount-control">
                    <el-input-number
                      v-model="buyAmounts[item.name]"
                      :min="1"
                      :max="Math.max(1, getMaxBuyAmount(item))"
                      :disabled="getMaxBuyAmount(item) === 0"
                      size="small"
                      style="width: 120px;"
                      @change="() => calculatePrice(item)"
                    />
                    <el-button size="small" class="max-btn" @click="setBuyAmountToMax(item)" :disabled="isAtLimit(item) || getMaxBuyAmount(item) === 0">Max</el-button>
                  </div>
                  <div class="button-group">
                    <el-button
                      type="primary"
                      size="small"
                      @click="handleBuy(item)"
                      :loading="buying[item.name]"
                      :disabled="!isSatisfied(item) || isAtLimit(item) || !hasEnoughCurrency(item) || getMaxBuyAmount(item) === 0"
                    >
                      购买
                    </el-button>
                  </div>
                </div>
                <div class="item-total-price">
                  <span class="total-label">总价:</span>
                  <span class="total-value">{{ formatNumber(getTotalPrice(item)) }}</span>
                  <span class="price-type">{{ item.priceType }}</span>
                </div>
              </el-card>
            </div>
            <el-empty v-if="activeTab === 'blueprints' && blueprintItems.length === 0" description="暂无可购买的图纸" />
          </el-tab-pane>

          <el-tab-pane label="能力" name="abilities">
            <div class="items-grid" v-if="activeTab === 'abilities' && abilityItems.length > 0">
              <el-card v-for="item in abilityItems" :key="'abilities-' + item.name" class="shop-item" :class="{ 'at-limit': showUnsatisfiedItems && isAtLimit(item) }">
                <div class="item-header">
                  <div class="item-name">
                    {{ item.name }}
                    <span class="item-amount">({{ getCurrentAmount(item.name) }}{{ item.amountLimit ? `/${item.amountLimit}` : '' }})</span>
                    <el-tag v-if="showUnsatisfiedItems && isAtLimit(item)" type="warning" size="small" class="limit-tag">已达上限</el-tag>
                  </div>
                </div>
                <div v-if="item.detail" class="item-detail">{{ item.detail }}</div>
                <div v-if="item.shopPreItems" class="item-preitems">
                  <el-tag type="warning" size="small" v-for="preItem in getPreItems(item.shopPreItems)" :key="preItem">
                    需要: {{ preItem }}
                  </el-tag>
                </div>
                <div class="item-actions">
                  <div class="amount-control">
                    <el-input-number
                      v-model="buyAmounts[item.name]"
                      :min="1"
                      :max="Math.max(1, getMaxBuyAmount(item))"
                      :disabled="getMaxBuyAmount(item) === 0"
                      size="small"
                      style="width: 120px;"
                      @change="() => calculatePrice(item)"
                    />
                    <el-button size="small" class="max-btn" @click="setBuyAmountToMax(item)" :disabled="isAtLimit(item) || getMaxBuyAmount(item) === 0">Max</el-button>
                  </div>
                  <div class="button-group">
                    <el-button
                      type="primary"
                      size="small"
                      @click="handleBuy(item)"
                      :loading="buying[item.name]"
                      :disabled="!isSatisfied(item) || isAtLimit(item) || !hasEnoughCurrency(item) || getMaxBuyAmount(item) === 0"
                    >
                      购买
                    </el-button>
                  </div>
                </div>
                <div class="item-total-price">
                  <span class="total-label">总价:</span>
                  <span class="total-value">{{ formatNumber(getTotalPrice(item)) }}</span>
                  <span class="price-type">{{ item.priceType }}</span>
                </div>
              </el-card>
            </div>
            <el-empty v-if="activeTab === 'abilities' && abilityItems.length === 0" description="暂无可购买的能力" />
          </el-tab-pane>

          <el-tab-pane label="回购" name="sell">
            <div v-if="showUnsatisfiedItems" class="sell-hint">
              <el-alert type="info" :closable="false" show-icon>
                <template #title>
                  全部展示模式：显示所有可出售物品（包括未持有的）
                </template>
              </el-alert>
            </div>
            <div class="items-grid" v-if="activeTab === 'sell' && sellableItems.length > 0">
              <el-card v-for="item in sellableItems" :key="'sell-' + item.name" class="shop-item">
                <div class="item-header">
                  <div class="item-name">
                    {{ item.name }}
                    <span class="item-amount">({{ getCurrentAmount(item.name) }})</span>
                  </div>
                </div>
                <div v-if="item.detail" class="item-detail">{{ item.detail }}</div>
                <div class="item-actions">
                  <div class="amount-control">
                    <el-input-number
                      v-model="sellAmounts[item.name]"
                      :min="1"
                      :max="getCurrentAmount(item.name)"
                      :disabled="getCurrentAmount(item.name) === 0"
                      size="small"
                      style="width: 120px;"
                      @change="() => calculateSellPrice(item)"
                    />
                    <el-button size="small" class="max-btn" @click="setSellAmount(item, getCurrentAmount(item.name))">Max</el-button>
                  </div>
                  <div class="button-group">
                    <el-button
                      type="warning"
                      size="small"
                      @click="handleSell(item)"
                      :loading="selling[item.name]"
                      :disabled="getCurrentAmount(item.name) === 0"
                    >
                      出售
                    </el-button>
                  </div>
                </div>
                <div class="item-total-price" style="background: #fdf6ec;">
                  <span class="total-label">回购价:</span>
                  <span class="total-value" style="color: #e6a23c;">{{ formatNumber(getSellTotalPrice(item)) }}</span>
                  <span class="price-type">{{ item.priceType }}</span>
                </div>
              </el-card>
            </div>
            <el-empty v-if="activeTab === 'sell' && sellableItems.length === 0" description="暂无可出售的物品" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { shopApi, userApi, warehouseApi } from '@/api'
import type { Item } from '@/types'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, onUnmounted, ref } from 'vue'

const shopItems = ref<Item[]>([])
const warehouseItems = ref<Record<string, number>>({})
const userInfo = ref<any>(null)
const loading = ref(false)
const buying = ref<Record<string, boolean>>({})
const activeTab = ref('property')
const buyAmounts = ref<Record<string, number>>({})
const totalPrices = ref<Record<string, number>>({})
const showUnsatisfiedItems = ref(false)
const isMounted = ref(true)
const propertyItems = computed(() => {
  let items = shopItems.value.filter(item => item.type === '财产')
  if (!showUnsatisfiedItems.value) {
    items = items.filter(item => isSatisfied(item) && !isAtLimit(item))
  }
  return items
})

const useableItems = computed(() => {
  let items = shopItems.value.filter(item => item.type === '道具')
  if (!showUnsatisfiedItems.value) {
    items = items.filter(item => isSatisfied(item) && !isAtLimit(item))
  }
  return items
})

const blueprintItems = computed(() => {
  let items = shopItems.value.filter(item => item.type === '图纸')
  if (!showUnsatisfiedItems.value) {
    items = items.filter(item => isSatisfied(item) && !isAtLimit(item))
  }
  return items
})

const abilityItems = computed(() => {
  let items = shopItems.value.filter(item => item.type === '能力')
  if (!showUnsatisfiedItems.value) {
    items = items.filter(item => isSatisfied(item) && !isAtLimit(item))
  }
  return items
})

const sellableItems = computed(() => {
  // 显示可以出售的物品
  // 在"全部展示"模式下显示所有可出售物品，否则只显示用户持有的
  return shopItems.value.filter(item => {
    const canSell = item.sellingPrice && item.sellingPrice > 0
    if (!canSell) return false
    
    if (showUnsatisfiedItems.value) {
      // 全部展示模式：显示所有可出售物品
      return true
    } else {
      // 非全部展示模式：只显示用户持有的
      return getCurrentAmount(item.name) > 0
    }
  })
})

const getCurrentAmount = (itemName: string) => {
  return warehouseItems.value[itemName] || 0
}

const formatNumber = (num: number) => {
  return num.toLocaleString()
}

const getPreItems = (preItemsStr: string) => {
  if (!preItemsStr) return []
  return preItemsStr.split(',').map(item => item.trim()).filter(item => item)
}

const getMaxBuyAmount = (item: Item) => {
  // 生草工厂：使用特殊逻辑计算
  if (item.name === "生草工厂") {
    return calculateMaxForFactory(item)
  }
  
  // 草精炼厂：受生草工厂数量限制
  if (item.name === "草精炼厂") {
    const currentAmount = getCurrentAmount(item.name)
    const factoryAmount = getCurrentAmount("生草工厂")
    const hasOptimization = getCurrentAmount("产业链优化") > 0
    const limitRatio = hasOptimization ? 8 : 10
    const maxAdvFactory = Math.floor(factoryAmount / limitRatio)
    return Math.max(0, maxAdvFactory - currentAmount)
  }
  
  const currentAmount = getCurrentAmount(item.name)
  
  // 有数量上限的物品：计算剩余可购买数量
  if (item.amountLimit) {
    return Math.max(0, item.amountLimit - currentAmount)
  }
  
  // 浮动价格物品：限制最大购买数量（避免价格过高）
  if (item.priceRate) {
    return 2000
  }
  
  // 非浮动价格且无上限的物品：根据货币计算最大可购买数量
  return calculateMaxByCurrency(item)
}

// 根据货币计算最大可购买数量
const calculateMaxByCurrency = (item: Item) => {
  const priceType = getPriceType(item)
  const unitPrice = item.shopPrice
  
  if (unitPrice <= 0) return 999999
  
  let currentCurrency = 0
  if (priceType === "自动化核心") {
    currentCurrency = getCurrentAmount('自动化核心')
  } else if (priceType === "草") {
    currentCurrency = userInfo.value?.kusa || 0
  } else if (priceType === "草之精华") {
    currentCurrency = userInfo.value?.advKusa || 0
  }
  
  // 最多能买多少个（至少保留1单位货币，避免完全花光）
  const maxAffordable = Math.floor(currentCurrency / unitPrice)
  return Math.max(0, maxAffordable > 0 ? maxAffordable : 0)
}

const isAtLimit = (item: Item) => {
  if (item.name === "生草工厂") {
    return false
  }
  if (item.name === "草精炼厂") {
    const currentAmount = getCurrentAmount(item.name)
    const factoryAmount = getCurrentAmount("生草工厂")
    const hasOptimization = getCurrentAmount("产业链优化") > 0
    const limitRatio = hasOptimization ? 8 : 10
    const maxAdvFactory = Math.floor(factoryAmount / limitRatio)
    return currentAmount >= maxAdvFactory
  }
  
  const currentAmount = getCurrentAmount(item.name)
  return item.amountLimit ? currentAmount >= item.amountLimit : false
}

const isSatisfied = (item: Item) => {
  if (item.name === "草精炼厂") {
    const hasBlueprint = getCurrentAmount("生草工业园区蓝图") > 0
    return hasBlueprint
  }
  
  if (!item.shopPreItems) {
    return true
  }
  
  const preItems = getPreItems(item.shopPreItems)
  for (const preItem of preItems) {
    if (preItem.startsWith('Lv')) {
      const needLevel = parseInt(preItem.substring(2))
      const currentLevel = userInfo.value?.vipLevel || 0
      if (currentLevel < needLevel) {
        return false
      }
    } else {
      const currentAmount = getCurrentAmount(preItem)
      if (currentAmount <= 0) {
        return false
      }
    }
  }
  
  return true
}

const calculatePrice = (item: Item) => {
  const amount = buyAmounts.value[item.name] || 1
  const currentAmount = getCurrentAmount(item.name)
  
  if (item.name === "生草工厂") {
    const currentFactoryAmount = currentAmount
    const buyingAmount = amount
    
    const autoTechLevel = getAutoTechLevel()
    const cheapLevel = (userInfo.value?.vipLevel || 0) + autoTechLevel
    const base = 1 + 0.5 * Math.exp(-0.255 * cheapLevel)
    
    let needCoreAmount = 0
    if (base === 1) {
      needCoreAmount = buyingAmount
    } else {
      needCoreAmount = Math.floor((Math.pow(base, currentFactoryAmount) * (Math.pow(base, buyingAmount) - 1)) / (base - 1))
    }
    
    totalPrices.value[item.name] = needCoreAmount
  } else if (item.name === "草精炼厂") {
    totalPrices.value[item.name] = 500 * amount
  } else if (item.priceRate) {
    let totalPrice = 0
    for (let i = 0; i < amount; i++) {
      totalPrice += Math.floor(item.shopPrice * Math.pow(item.priceRate, currentAmount + i))
    }
    totalPrices.value[item.name] = totalPrice
  } else {
    totalPrices.value[item.name] = item.shopPrice * amount
  }
}

const getAutoTechLevel = () => {
  let level = 0
  if (warehouseItems.value['生草工厂自动工艺I'] && warehouseItems.value['生草工厂自动工艺I'] > 0) {
    level = 1
  }
  if (warehouseItems.value['生草工厂自动工艺II'] && warehouseItems.value['生草工厂自动工艺II'] > 0) {
    level = 2
  }
  return level
}

const getPriceType = (item: Item) => {
  if (item.name === "生草工厂" || item.name === "草精炼厂") {
    return "自动化核心"
  }
  return item.priceType || "草"
}

const hasEnoughCurrency = (item: Item) => {
  const priceType = getPriceType(item)
  const totalPrice = getTotalPrice(item)
  
  if (priceType === "自动化核心") {
    return getCurrentAmount('自动化核心') >= totalPrice
  } else if (priceType === "草") {
    return (userInfo.value?.kusa || 0) >= totalPrice
  } else if (priceType === "草之精华") {
    return (userInfo.value?.advKusa || 0) >= totalPrice
  }
  return true
}

const getTotalPrice = (item: Item) => {
  return totalPrices.value[item.name] || 0
}

const sellAmounts = ref<Record<string, number>>({})
const selling = ref<Record<string, boolean>>({})
const sellPrices = ref<Record<string, number>>({})

const calculateSellPrice = (item: Item) => {
  const amount = buyAmounts.value[item.name] || 1
  if (item.sellingPrice) {
    sellPrices.value[item.name] = item.sellingPrice * amount
  } else {
    sellPrices.value[item.name] = 0
  }
}

const getSellPrice = (item: Item) => {
  return sellPrices.value[item.name] || 0
}

const getSellTotalPrice = (item: Item) => {
  const amount = sellAmounts.value[item.name] || 1
  if (item.sellingPrice) {
    return item.sellingPrice * amount
  }
  return 0
}

const handleSell = async (item: Item) => {
  const amount = sellAmounts.value[item.name] || 1
  selling.value[item.name] = true
  try {
    const result = await shopApi.sellItem(item.name, amount, false)
    if (!isMounted.value) return
    
    ElMessage.success(`成功出售 ${amount} 个 ${item.name}，获得 ${result.totalPrice} ${result.priceType}`)
    await refreshShop()
  } catch (error: any) {
    if (isMounted.value) {
      ElMessage.error(error.message || '出售失败')
    }
  } finally {
    if (isMounted.value) {
      selling.value[item.name] = false
    }
  }
}

const canSell = (item: Item) => {
  return item.sellingPrice && item.sellingPrice > 0 && getCurrentAmount(item.name) > 0
}

const refreshShop = async () => {
  loading.value = true
  try {
    const [shopItemsData, warehouse, userInfoData] = await Promise.all([
      shopApi.getShopItems(),
      warehouseApi.getWarehouse(),
      userApi.getInfo()
    ])
    if (!isMounted.value) return
    
    shopItems.value = shopItemsData
    warehouseItems.value = {}
    
    warehouse.items.forEach((userItem: any) => {
      warehouseItems.value[userItem.item.name] = userItem.amount
    })
    
    if (!warehouseItems.value['自动化核心']) {
      warehouseItems.value['自动化核心'] = 0
    }
    
    userInfo.value = userInfoData
    shopItems.value.forEach(item => {
      if (!buyAmounts.value[item.name]) {
        buyAmounts.value[item.name] = 1
      }
      if (!sellAmounts.value[item.name]) {
        sellAmounts.value[item.name] = 1
      }
      calculatePrice(item)
      calculateSellPrice(item)
    })
  } catch (error) {
    console.error('获取商店物品失败:', error)
    if (isMounted.value) {
      ElMessage.error('获取商店物品失败')
    }
  } finally {
    if (isMounted.value) {
      loading.value = false
    }
  }
}

const handleBuy = async (item: Item) => {
  const amount = buyAmounts.value[item.name]
  if (!amount || amount < 1) {
    ElMessage.warning('请选择购买数量')
    return
  }

  if (isAtLimit(item)) {
    ElMessage.warning(`已达到物品持有上限(${item.amountLimit})`)
    return
  }

  // 检查是否花费超过1/3货币
  const totalPrice = getTotalPrice(item)
  const priceType = getPriceType(item)
  let currentCurrency = 0
  if (priceType === "自动化核心") {
    currentCurrency = getCurrentAmount('自动化核心')
  } else if (priceType === "草") {
    currentCurrency = userInfo.value?.kusa || 0
  } else if (priceType === "草之精华") {
    currentCurrency = userInfo.value?.advKusa || 0
  }

  if (currentCurrency > 0 && totalPrice >= currentCurrency / 3) {
    try {
      await ElMessageBox.confirm(
        `本次购买将花费 ${formatNumber(totalPrice)} ${priceType}，占您当前${priceType}总量的 ${Math.round(totalPrice / currentCurrency * 100)}%，确定购买吗？`,
        '购买确认',
        {
          confirmButtonText: '确定购买',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }

  buying.value[item.name] = true
  try {
    const result = await shopApi.buyItem(item.name, amount, false)
    if (!isMounted.value) return
    
    if (item.name === "生草工厂") {
      ElMessage.success(`成功购买 ${result.newFactories} 个 ${item.name}，消耗 ${result.coreCost} 自动化核心`)
    } else if (item.name === "草精炼厂") {
      ElMessage.success(`成功购买 ${result.newFactories} 个 ${item.name}，消耗 ${result.coreCost} 自动化核心`)
    } else {
      ElMessage.success(`成功购买 ${result.buyingAmount} 个 ${item.name}，消耗 ${result.totalPrice} ${result.priceType}`)
    }
    // 购买成功后重置数量选择器为1
    resetBuyAmount(item.name)
    await refreshShop()
  } catch (error: any) {
    if (isMounted.value) {
      ElMessage.error(error.message || '购买失败')
    }
  } finally {
    if (isMounted.value) {
      buying.value[item.name] = false
    }
  }
}

// 设置购买数量（Min按钮使用）
const setBuyAmount = (item: Item, amount: number) => {
  const maxAmount = getMaxBuyAmount(item)
  // 确保数量在有效范围内，且至少为1
  const finalAmount = Math.max(1, Math.min(amount, Math.max(1, maxAmount)))
  buyAmounts.value[item.name] = finalAmount
  calculatePrice(item)
}

// 设置购买数量为最大值（Max按钮使用）
const setBuyAmountToMax = (item: Item) => {
  let maxAmount: number
  
  if (item.name === "生草工厂") {
    // 生草工厂：特殊逻辑，最多100个，根据自动化核心计算
    maxAmount = calculateMaxForFactory(item)
  } else if (item.priceRate) {
    // 浮动价格物品：使用二分查找计算最大可购买数量
    maxAmount = calculateMaxForFloatingPrice(item)
  } else {
    // 固定价格物品：使用getMaxBuyAmount
    maxAmount = getMaxBuyAmount(item)
  }
  
  // 确保max至少为1，避免选择器报错
  const finalAmount = Math.max(1, maxAmount)
  
  buyAmounts.value[item.name] = finalAmount
  calculatePrice(item)
}

// 计算生草工厂的最大可购买数量（考虑浮动价格）
const calculateMaxForFactory = (item: Item): number => {
  const currentAmount = getCurrentAmount(item.name)
  const currentCores = warehouseItems.value['自动化核心'] || 0
  
  // 获取VIP等级（影响价格折扣）
  const vipLevel = userInfo.value?.vipLevel || 0
  // 计算自动工艺等级（I=1, II=2）
  const autoTechLevel = (warehouseItems.value['生草工厂自动工艺I'] ? 1 : 0) + 
                        (warehouseItems.value['生草工厂自动工艺II'] ? 1 : 0)
  const cheapLevel = vipLevel + autoTechLevel
  
  // 根据货币计算最大可购买数量（考虑浮动价格）
  const maxByCurrency = calculateMaxFactoryByCores(currentAmount, currentCores, cheapLevel)
  
  // 单次购买上限100个
  return Math.min(100, maxByCurrency)
}

// 根据核心数量计算最大可购买的生草工厂数量（考虑浮动价格）
const calculateMaxFactoryByCores = (currentFactories: number, availableCores: number, cheapLevel: number): number => {
  if (availableCores <= 0) return 0
  
  // 计算基础系数
  const base = 1 + 0.5 * Math.exp(-0.255 * cheapLevel)
  
  // 二分查找最大可购买数量
  let left = 1
  let right = 100
  let result = 0
  
  while (left <= right) {
    const mid = Math.floor((left + right) / 2)
    const totalCost = calculateFactoryCost(base, currentFactories, mid)
    
    if (totalCost <= availableCores) {
      result = mid
      left = mid + 1
    } else {
      right = mid - 1
    }
  }
  
  return result
}

// 计算购买指定数量生草工厂的总成本
const calculateFactoryCost = (base: number, nowFactories: number, newFactories: number): number => {
  // 公式：int((base ^ now) * (base ^ new - 1) / (base - 1))
  return Math.floor((base ** nowFactories) * (base ** newFactories - 1) / (base - 1))
}

// 计算浮动价格物品的最大可购买数量
const calculateMaxForFloatingPrice = (item: Item): number => {
  const priceType = getPriceType(item)
  let currentCurrency = 0
  
  if (priceType === "自动化核心") {
    currentCurrency = getCurrentAmount('自动化核心')
  } else if (priceType === "草") {
    currentCurrency = userInfo.value?.kusa || 0
  } else if (priceType === "草之精华") {
    currentCurrency = userInfo.value?.advKusa || 0
  }
  
  // 二分查找最大可购买数量
  let left = 1
  let right = 2000 // 浮动价格物品上限
  let result = 0
  
  while (left <= right) {
    const mid = Math.floor((left + right) / 2)
    const totalPrice = calculateTotalPriceForAmount(item, mid)
    
    if (totalPrice <= currentCurrency) {
      result = mid
      left = mid + 1
    } else {
      right = mid - 1
    }
  }
  
  return result
}

// 计算购买指定数量浮动价格物品的总价
const calculateTotalPriceForAmount = (item: Item, amount: number): number => {
  if (!item.priceRate || amount <= 0) return 0
  
  const currentAmount = getCurrentAmount(item.name)
  let totalPrice = 0
  
  for (let i = 0; i < amount; i++) {
    const priceMultiplier = Math.pow(item.priceRate, currentAmount + i)
    totalPrice += Math.floor(item.shopPrice * priceMultiplier)
  }
  
  return totalPrice
}

// 设置出售数量
const setSellAmount = (item: Item, amount: number) => {
  const maxAmount = getCurrentAmount(item.name)
  const finalAmount = Math.max(1, Math.min(amount, maxAmount))
  sellAmounts.value[item.name] = finalAmount
  calculateSellPrice(item)
}

// 重置购买数量为1
const resetBuyAmount = (itemName: string) => {
  buyAmounts.value[itemName] = 1
  const item = shopItems.value.find(i => i.name === itemName)
  if (item) {
    calculatePrice(item)
  }
}

onMounted(() => {
  refreshShop()
})

onUnmounted(() => {
  isMounted.value = false
})
</script>

<style scoped>
.shop-container {
  max-width: 1200px;
  margin: 0 auto;
}

.shop-card {
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

.header-left {
  flex: 1;
  margin-left: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.currency-tag {
  font-weight: bold;
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.shop-item {
  transition: transform 0.2s;
}

.shop-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.item-name {
  font-weight: bold;
  font-size: 16px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-amount {
  font-size: 14px;
  color: #909399;
  font-weight: normal;
}

.item-detail {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  margin-bottom: 12px;
  min-height: 40px;
}

.item-preitems {
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.amount-control {
  display: flex;
  align-items: center;
}

.amount-control .max-btn {
  border-radius: 0 4px 4px 0;
  border-left: none;
  padding: 0 10px;
  font-size: 12px;
}

.amount-control .el-input-number :deep(.el-input__wrapper) {
  border-radius: 4px 0 0 4px;
}

.button-group {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.item-total-price {
  padding: 6px 12px;
  background: #f0f9ff;
  border-radius: 4px;
  text-align: right;
  font-size: 16px;
  line-height: 1.5;
  margin-bottom: 6px;
}

.total-label {
  color: #666;
  margin-right: 8px;
}

.total-value {
  color: #f56c6c;
  font-size: 20px;
  font-weight: bold;
}

.price-type {
  color: #999;
  font-size: 12px;
}

.shop-item.at-limit {
  border: 2px solid #e6a23c;
  background-color: #fdf6ec;
}

.shop-item.at-limit .item-name {
  color: #e6a23c;
}

.limit-tag {
  margin-left: 8px;
}

@media screen and (max-width: 600px) {
  .card-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .header-left {
    margin-left: 0;
    order: 2;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .items-grid {
    grid-template-columns: 1fr;
  }

  .item-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .button-group {
    margin-left: 0;
    justify-content: flex-end;
  }
}
</style>
