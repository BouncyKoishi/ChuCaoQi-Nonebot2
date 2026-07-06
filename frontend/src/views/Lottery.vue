<template>
  <div class="lottery-container">
    <el-card class="lottery-card">
      <template #header>
        <div class="card-header">
          <h2>抽奖系统</h2>
          <div class="header-actions">
            <el-button type="primary" @click="showAddDialog = true">添加物品</el-button>
            <el-button @click="refreshStorage" circle size="default" style="width: 32px; height: 32px;">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="抽奖" name="draw">
          <div class="draw-section">
            <div class="draw-header">
              <el-select v-model="drawPool" placeholder="选择奖池" style="width: 200px;">
                <el-option label="所有奖池" :value="''" />
                <el-option v-for="pool in pools" :key="pool" :label="pool" :value="pool" />
              </el-select>
              <el-button type="primary" size="large" @click="handleDraw" :disabled="drawDisabled" :loading="drawing">
                抽奖
              </el-button>
              <div class="item-status">
                <el-tag v-if="quantumShieldAmount > 0" type="info" class="status-tag">量子护盾 ×{{ quantumShieldAmount }}</el-tag>
                <el-tag v-if="diceFragmentAmount > 0" type="warning" class="status-tag">骰子碎片 ×{{ diceFragmentAmount }}</el-tag>
              </div>
            </div>

            <div class="draw-buttons">
              <div class="draw-ten-section">
                <el-select v-model="drawTenLevel" placeholder="选择十连券" style="width: 180px;" @change="loadTenTicketAmount">
                  <el-option label="十连券" :value="0" />
                  <el-option label="高级十连券" :value="1" />
                  <el-option label="特级十连券" :value="2" />
                  <el-option label="天琴十连券" :value="3" />
                </el-select>
                <span class="ticket-amount">×{{ tenTicketAmount }}</span>
                <el-button type="success" size="large" @click="handleDrawTen" :disabled="drawDisabled || tenTicketAmount <= 0" :loading="drawingTen">
                  十连抽
                </el-button>
              </div>
            </div>

            <div v-if="drawDisabled" class="draw-disabled-hint">
              <el-icon><WarningFilled /></el-icon>
              <span>抽奖已禁用，请等待 {{ formatNumber(drawDisabledTime) }} 秒</span>
            </div>

            <el-divider />

            <div v-if="drawResult || drawTenResult" class="draw-result">
              <div v-if="drawResult" class="single-draw-result">
                <h3>抽奖结果</h3>
                <div v-if="drawResult.redrawCount > 0" class="redraw-info">
                  <el-tag type="warning" size="small">消耗骰子碎片 ×{{ drawResult.redrawCount }}</el-tag>
                </div>
                <div class="result-item" :class="`result-rare-${drawResult.item.rare.toLowerCase()}`" @click="showItemDetail(drawResult.item.name)">
                  <el-tag :type="getRareTagType(drawResult.item.rare)" size="large">
                    {{ drawResult.item.rare }}
                  </el-tag>
                  <span class="result-name">
                    {{ drawResult.item.name }}
                    <span v-if="drawResult.isNew" class="new-tag">(New!)</span>
                  </span>
                </div>
                <div v-if="drawResult.item.detail" class="result-detail" v-html="formatNewline(drawResult.item.detail)"></div>
              </div>

              <div v-if="drawTenResult" class="ten-draw-result">
                <h3>十连抽结果</h3>
                <div class="ten-items">
                  <div v-for="(item, index) in drawTenResult.items" :key="index" class="result-item" :class="`result-rare-${item.rare.toLowerCase()}`" @click="showItemDetail(item.name)">
                    <el-tag :type="getRareTagType(item.rare)">
                      {{ item.rare }}
                    </el-tag>
                    <span class="result-name">
                      {{ item.name }}
                      <span v-if="item.isNew" class="new-tag">(New!)</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="物品仓库" name="storage">
          <div class="storage-header">
            <el-input 
              v-model="storageSearchKeyword" 
              placeholder="搜索物品名称" 
              clearable
              style="width: 200px;"
            />
            <el-select v-model="selectedPool" placeholder="选择奖池" clearable style="width: 150px; margin-left: 12px;" @change="refreshStorage">
              <el-option label="所有奖池" :value="''" />
              <el-option v-for="pool in pools" :key="pool" :label="pool" :value="pool" />
            </el-select>
            <el-select v-model="selectedRare" placeholder="选择稀有度" clearable style="width: 120px; margin-left: 12px;" @change="refreshStorage">
              <el-option label="Easy" value="Easy" />
              <el-option label="Normal" value="Normal" />
              <el-option label="Hard" value="Hard" />
              <el-option label="Lunatic" value="Lunatic" />
            </el-select>
          </div>

          <div v-if="filteredStorageData.byRare" class="storage-content">
            <div v-for="(rareData, rare) in filteredStorageData.byRare" :key="rare" class="rare-section">
              <div class="rare-header" :class="`rare-${rare.toLowerCase()}`" @click="toggleRareExpand(rare)">
                <div class="rare-header-left">
                  <el-icon class="expand-icon" :class="{ 'is-expanded': expandedRares[rare] }">
                    <ArrowRight />
                  </el-icon>
                  <span>{{ rare }}</span>
                </div>
                <span class="rare-count">{{ rareData.items.length }}/{{ rareData.total }}</span>
              </div>
              <el-collapse-transition>
                <div class="item-list" v-show="expandedRares[rare]">
                  <el-tag 
                    v-for="item in rareData.items" 
                    :key="item.name" 
                    :type="getRareTagType(rare)"
                    class="item-tag"
                    @click="showItemDetail(item.name)"
                  >
                    {{ item.name }} ×{{ item.amount }}
                  </el-tag>
                  <span v-if="rareData.items.length === 0" class="empty-hint">暂无物品</span>
                </div>
              </el-collapse-transition>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="自制物品" name="myItems">
          <div class="my-items-header">
            <el-input 
              v-model="myItemsSearchKeyword" 
              placeholder="搜索物品名称" 
              clearable
              style="width: 180px;"
            />
            <el-select v-model="myItemsPoolFilter" placeholder="选择奖池" clearable style="width: 130px; margin-left: 12px;">
              <el-option v-for="pool in myItemsPools" :key="pool" :label="pool" :value="pool" />
            </el-select>
            <el-select v-model="myItemsRareFilter" placeholder="选择稀有度" clearable style="width: 120px; margin-left: 12px;">
              <el-option label="Easy" value="Easy" />
              <el-option label="Normal" value="Normal" />
              <el-option label="Hard" value="Hard" />
              <el-option label="Lunatic" value="Lunatic" />
            </el-select>
          </div>
          <el-table :data="paginatedMyItems" style="width: 100%" v-if="filteredMyItems.length > 0">
            <el-table-column prop="name" label="名称" min-width="150" />
            <el-table-column prop="rare" label="稀有度" width="100">
              <template #default="{ row }">
                <el-tag :type="getRareTagType(row.rare)" size="small">{{ row.rare }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="pool" label="奖池" width="100" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="editItem(row)">编辑</el-button>
                <el-button type="danger" size="small" link @click="deleteItem(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无自制物品" />
          <div class="pagination-container" v-if="filteredMyItems.length > myItemsPageSize">
            <el-pagination
              v-model:current-page="myItemsCurrentPage"
              :page-size="myItemsPageSize"
              :total="filteredMyItems.length"
              layout="prev, pager, next"
              small
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="搜索物品" name="search">
          <div class="search-section">
            <el-input 
              v-model="searchKeyword" 
              placeholder="输入物品名称搜索" 
              @keyup.enter="searchItems"
              style="width: 300px;"
            >
              <template #append>
                <el-button @click="searchItems">搜索</el-button>
              </template>
            </el-input>
          </div>

          <div v-if="searchResults.length > 0" class="search-results">
            <el-tag 
              v-for="item in searchResults" 
              :key="item.id" 
              :type="getRareTagType(item.rare)"
              class="item-tag"
              @click="showItemDetail(item.name)"
            >
              [{{ item.rare }}] {{ item.name }}
            </el-tag>
          </div>
          <el-empty v-else-if="searchKeyword && searched" description="未找到相关物品" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="itemDetailVisible" :title="currentItem?.name" width="500px">
      <div v-if="currentItem" class="item-detail-content">
        <div class="detail-grid">
          <div class="detail-row">
            <span class="detail-label">稀有度：</span>
            <span class="detail-value">
              <el-tag :type="getRareTagType(currentItem.rare)">{{ currentItem.rare }}</el-tag>
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">持有数量：</span>
            <span class="detail-value">{{ currentItem.amount }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">所属奖池：</span>
            <span class="detail-value">{{ currentItem.pool }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">创作者：</span>
            <span class="detail-value">{{ currentItem.authorQQ || '系统' }}</span>
          </div>
          <div v-if="currentItem.personCount" class="detail-row detail-row-full">
            <span class="detail-label">被抽中次数：</span>
            <span class="detail-value">{{ currentItem.numberCount }}次 ({{ currentItem.personCount }}人)</span>
          </div>
          <div v-else class="detail-row detail-row-full">
            <span class="detail-label">还没有人抽到这件物品</span>
          </div>
        </div>
        <div class="detail-divider-wrapper">
          <el-divider class="detail-divider" />
        </div>
        <div class="detail-section">
          <div class="detail-section-title">物品说明</div>
          <div class="detail-section-content">
            <span v-if="currentItem.detail" class="detail-section-content" v-html="formatNewline(currentItem.detail)"></span>
            <span v-else class="empty-hint">暂无说明</span>
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showAddDialog" title="添加自定义物品" width="500px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="物品名" required>
          <el-input v-model="addForm.name" maxlength="32" show-word-limit placeholder="最多32字" />
        </el-form-item>
        <el-form-item label="稀有度" required>
          <el-select v-model="addForm.rareRank" style="width: 100%;">
            <el-option label="Easy (1000草)" :value="0" />
            <el-option label="Normal (8000草)" :value="1" />
            <el-option label="Hard (64000草)" :value="2" />
            <el-option label="Lunatic (512000草)" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="奖池">
          <el-select v-model="addForm.pool" style="width: 100%;" allow-create filterable>
            <el-option v-for="pool in pools" :key="pool" :label="pool" :value="pool" />
          </el-select>
        </el-form-item>
        <el-form-item label="物品说明">
          <el-input v-model="addForm.detail" type="textarea" :rows="5" maxlength="1024" show-word-limit placeholder="最多1024字" />
        </el-form-item>
        <el-form-item label="消耗草">
          <span class="cost-display">{{ formatNumber(addCost) }} 草</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addItem" :loading="adding">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditDialog" title="编辑物品说明" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="物品名">
          <span>{{ editForm.name }}</span>
        </el-form-item>
        <el-form-item label="物品说明">
          <el-input v-model="editForm.detail" type="textarea" :rows="5" maxlength="1024" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateItem" :loading="updating">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { itemApi, lotteryApi } from '@/api'
import { formatNumber } from '@/utils'
import { ArrowRight, Refresh, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'

const activeTab = ref('draw')
const pools = ref<string[]>([])
const selectedPool = ref('')
const selectedRare = ref('')
const storageData = ref<any>({ byRare: {} })
const storageSearchKeyword = ref('')
const expandedRares = ref<Record<string, boolean>>({})

const filteredStorageData = computed(() => {
  if (!storageData.value.byRare) return { byRare: {} }
  
  const result: any = { byRare: {} }
  const keyword = storageSearchKeyword.value.toLowerCase().trim()
  
  for (const [rare, rareData] of Object.entries(storageData.value.byRare)) {
    const data = rareData as any
    const filteredItems = keyword 
      ? data.items.filter((item: any) => item.name.toLowerCase().includes(keyword))
      : data.items
    result.byRare[rare] = {
      ...data,
      items: filteredItems
    }
  }
  
  return result
})

const updateExpandedRares = () => {
  if (!storageData.value.byRare) return
  
  const newExpandedRares: Record<string, boolean> = {}
  const keyword = storageSearchKeyword.value.toLowerCase().trim()
  
  for (const [rare, rareData] of Object.entries(storageData.value.byRare)) {
    const data = rareData as any
    const filteredItems = keyword 
      ? data.items.filter((item: any) => item.name.toLowerCase().includes(keyword))
      : data.items
    newExpandedRares[rare] = filteredItems.length <= 100
  }
  
  expandedRares.value = newExpandedRares
}

const toggleRareExpand = (rare: string) => {
  expandedRares.value[rare] = !expandedRares.value[rare]
}

const searchKeyword = ref('')
const searched = ref(false)
const searchResults = ref<any[]>([])

const itemDetailVisible = ref(false)
const currentItem = ref<any>(null)

const showAddDialog = ref(false)
const adding = ref(false)
const addForm = ref({
  name: '',
  rareRank: 0,
  pool: '默认',
  detail: ''
})

const addCost = computed(() => {
  return 1000 * Math.pow(8, addForm.value.rareRank)
})

const myItems = ref<any[]>([])
const myItemsSearchKeyword = ref('')
const myItemsPoolFilter = ref('')
const myItemsRareFilter = ref('')
const myItemsCurrentPage = ref(1)
const myItemsPageSize = 10

const myItemsPools = computed(() => {
  const poolSet = new Set<string>()
  myItems.value.forEach((item: any) => {
    if (item.pool) poolSet.add(item.pool)
  })
  return Array.from(poolSet)
})

const filteredMyItems = computed(() => {
  const keyword = myItemsSearchKeyword.value.toLowerCase().trim()
  const poolFilter = myItemsPoolFilter.value
  const rareFilter = myItemsRareFilter.value
  
  return myItems.value.filter((item: any) => {
    const matchKeyword = !keyword || item.name.toLowerCase().includes(keyword)
    const matchPool = !poolFilter || item.pool === poolFilter
    const matchRare = !rareFilter || item.rare === rareFilter
    return matchKeyword && matchPool && matchRare
  })
})

const paginatedMyItems = computed(() => {
  const start = (myItemsCurrentPage.value - 1) * myItemsPageSize
  return filteredMyItems.value.slice(start, start + myItemsPageSize)
})

const showEditDialog = ref(false)
const editForm = ref({ name: '', detail: '' })
const updating = ref(false)

const drawPool = ref('')
const drawTenLevel = ref(0)
const drawDisabled = ref(false)
const drawDisabledTime = ref(0)
const drawing = ref(false)
const drawingTen = ref(false)
const drawResult = ref<any>(null)
const drawTenResult = ref<any>(null)
const tenTicketAmount = ref(0)
const quantumShieldAmount = ref(0)
const diceFragmentAmount = ref(0)

const DISABLED_STORAGE_KEY = 'lottery_disabled_until'

const loadDisabledStatus = () => {
  const disabledUntil = localStorage.getItem(DISABLED_STORAGE_KEY)
  if (disabledUntil) {
    const until = parseInt(disabledUntil)
    const now = Date.now()
    if (until > now) {
      const remaining = Math.ceil((until - now) / 1000)
      drawDisabled.value = true
      drawDisabledTime.value = remaining
      startDisabledTimer()
    } else {
      localStorage.removeItem(DISABLED_STORAGE_KEY)
    }
  }
}

const saveDisabledStatus = (seconds: number) => {
  const until = Date.now() + seconds * 1000
  localStorage.setItem(DISABLED_STORAGE_KEY, until.toString())
}

const startDisabledTimer = () => {
  const timer = setInterval(() => {
    drawDisabledTime.value--
    if (drawDisabledTime.value <= 0) {
      drawDisabled.value = false
      localStorage.removeItem(DISABLED_STORAGE_KEY)
      clearInterval(timer)
    }
  }, 1000)
}

const tenTicketNames = ['十连券', '高级十连券', '特级十连券', '天琴十连券']

const getRareTagType = (rare: string) => {
  const types: Record<string, string> = {
    'Easy': '',
    'Normal': 'success',
    'Hard': 'warning',
    'Lunatic': 'danger'
  }
  return types[rare] || ''
}

const formatNewline = (text: string): string => {
  if (!text) return ''
  return text.replace(/\r\n/g, '<br>').replace(/\n/g, '<br>').replace(/\r/g, '<br>')
}

const loadQuantumShieldAmount = async () => {
  try {
    const res = await itemApi.getItemAmount('量子护盾')
    if (res && typeof res.amount === 'number') {
      quantumShieldAmount.value = res.amount
    } else {
      quantumShieldAmount.value = 0
    }
  } catch (error) {
    console.error('获取量子护盾数量失败:', error)
    quantumShieldAmount.value = 0
  }
}

const loadDiceFragmentAmount = async () => {
  try {
    const res = await itemApi.getItemAmount('骰子碎片')
    if (res && typeof res.amount === 'number') {
      diceFragmentAmount.value = res.amount
    } else {
      diceFragmentAmount.value = 0
    }
  } catch (error) {
    console.error('获取骰子碎片数量失败:', error)
    diceFragmentAmount.value = 0
  }
}

const refreshStorage = async () => {
  try {
    const res = await lotteryApi.getStorage(selectedRare.value || undefined, selectedPool.value || undefined)
    if (res) {
      storageData.value = res
      updateExpandedRares()
    }
  } catch (error) {
    console.error('获取物品仓库失败:', error)
  }
}

const loadPools = async () => {
  try {
    const res = await lotteryApi.getPools()
    if (res) {
      pools.value = res
    }
  } catch (error) {
    console.error('获取奖池列表失败:', error)
  }
}

const loadTenTicketAmount = async () => {
  try {
    const ticketName = tenTicketNames[drawTenLevel.value]
    const res = await itemApi.getItemAmount(ticketName)
    if (res && typeof res.amount === 'number') {
      tenTicketAmount.value = res.amount
    } else {
      tenTicketAmount.value = 0
    }
  } catch (error) {
    console.error('获取十连券数量失败:', error)
    tenTicketAmount.value = 0
  }
}

const searchItems = async () => {
  if (!searchKeyword.value.trim()) return
  searched.value = true
  try {
    const res = await lotteryApi.searchItems(searchKeyword.value)
    if (res) {
      searchResults.value = res.items
    }
  } catch (error) {
    console.error('搜索失败:', error)
  }
}

const showItemDetail = async (itemName: string) => {
  console.log('showItemDetail called:', itemName)
  try {
    console.log('Calling lotteryApi.getItem with:', itemName)
    const res = await lotteryApi.getItem(itemName)
    console.log('lotteryApi.getItem response:', res)
    if (res) {
      currentItem.value = res
      itemDetailVisible.value = true
      console.log('Dialog should be visible now')
    }
  } catch (error) {
    console.error('获取物品详情失败:', error)
  }
}

const addItem = async () => {
  if (!addForm.value.name.trim()) {
    ElMessage.warning('请输入物品名')
    return
  }
  
  adding.value = true
  try {
    await lotteryApi.addItem(addForm.value.name, addForm.value.rareRank, addForm.value.pool, addForm.value.detail)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    addForm.value = { name: '', rareRank: 0, pool: '默认', detail: '' }
    refreshStorage()
    loadMyItems()
  } catch (error: any) {
    if (error.message === 'EXIST') {
      ElMessage.error('物品名已存在')
    } else if (error.message === 'INSUFFICIENT_KUSA') {
      ElMessage.error('草不足')
    } else if (error.message === 'MODERATION_FAILED') {
      ElMessage.error('内容审核未通过，请修改后重试')
    } else if (error.message === 'MODERATION_API_ERROR') {
      ElMessage.error('内容审核功能异常，暂时无法新增物品')
    } else {
      ElMessage.error(error.message || '添加失败')
    }
  } finally {
    adding.value = false
  }
}

const loadMyItems = async () => {
  try {
    const res = await lotteryApi.getMyItems()
    if (res) {
      myItems.value = res
    }
  } catch (error) {
    console.error('获取自制物品失败:', error)
  }
}

const editItem = (item: any) => {
  editForm.value = { name: item.name, detail: item.detail || '' }
  showEditDialog.value = true
}

const updateItem = async () => {
  updating.value = true
  try {
    await lotteryApi.updateItem(editForm.value.name, editForm.value.detail)
    ElMessage.success('修改成功')
    showEditDialog.value = false
    loadMyItems()
  } catch (error: any) {
    if (error.message === 'MODERATION_FAILED') {
      ElMessage.error('内容审核未通过，请修改后重试')
    } else if (error.message === 'MODERATION_API_ERROR') {
      ElMessage.error('内容审核功能异常，暂时无法修改物品')
    } else {
      ElMessage.error(error.message || '修改失败')
    }
  } finally {
    updating.value = false
  }
}

const deleteItem = async (item: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除物品"${item.name}"吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await lotteryApi.deleteItem(item.name)
    ElMessage.success('删除成功')
    loadMyItems()
    refreshStorage()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleDraw = async () => {
  if (drawDisabled.value) {
    return
  }
  
  drawing.value = true
  drawResult.value = null
  drawTenResult.value = null
  
  try {
    const res = await lotteryApi.draw(drawPool.value || undefined)
    if (res) {
      if (res.banned) {
        drawDisabled.value = true
        drawDisabledTime.value = res.disabledSeconds
        saveDisabledStatus(res.disabledSeconds)
        startDisabledTimer()
        ElMessage.warning(`获得了：口球(${res.disabledSeconds}s)！`)
      } else {
        drawResult.value = res
      }
      await loadQuantumShieldAmount()
      await loadDiceFragmentAmount()
    }
  } catch (error: any) {
    console.error('抽奖失败:', error)
    if (error.response?.data?.error === 'DISABLED') {
      const remaining = error.response?.data?.data?.remaining || 0
      if (remaining > 0) {
        drawDisabled.value = true
        drawDisabledTime.value = remaining
        saveDisabledStatus(remaining)
        startDisabledTimer()
      }
      return
    }
    if (error.response?.data?.error === 'EMPTY_POOL' || 
        error.message?.includes('pool') || 
        error.message?.includes('空') || 
        error.message?.includes('empty')) {
      ElMessage.warning('该奖池暂无物品可抽')
    } else {
      ElMessage.error(error.message || '抽奖失败')
    }
  } finally {
    drawing.value = false
  }
}

const handleDrawTen = async () => {
  if (drawDisabled.value) {
    return
  }
  
  if (tenTicketAmount.value <= 0) {
    ElMessage.warning('没有足够的十连券')
    return
  }
  
  drawingTen.value = true
  drawResult.value = null
  drawTenResult.value = null
  
  try {
    const res = await lotteryApi.drawTen(drawTenLevel.value, drawPool.value || undefined)
    if (res) {
      drawTenResult.value = res
      await loadTenTicketAmount()
    }
  } catch (error: any) {
    console.error('十连抽失败:', error)
    if (error.response?.data?.error === 'DISABLED') {
      const remaining = error.response?.data?.data?.remaining || 0
      if (remaining > 0) {
        drawDisabled.value = true
        drawDisabledTime.value = remaining
        saveDisabledStatus(remaining)
        startDisabledTimer()
      }
      return
    }
    if (error.response?.data?.error === 'NO_TICKET') {
      ElMessage.warning(error.response?.data?.message || '没有足够的十连券')
      await loadTenTicketAmount()
      return
    }
    if (error.response?.data?.error === 'EMPTY_POOL' || 
        error.message?.includes('pool') || 
        error.message?.includes('空') || 
        error.message?.includes('empty')) {
      ElMessage.warning('该奖池暂无物品可抽')
    } else {
      ElMessage.error(error.message || '十连抽失败')
    }
  } finally {
    drawingTen.value = false
  }
}

onMounted(async () => {
  loadDisabledStatus()
  
  const userId = localStorage.getItem('userId')
  const initPromises: Promise<void>[] = [
    loadPools(),
    refreshStorage()
  ]
  
  if (userId) {
    initPromises.push(
      loadTenTicketAmount(),
      loadQuantumShieldAmount(),
      loadDiceFragmentAmount()
    )
  }
  
  await Promise.all(initPromises)
})

watch(activeTab, (newVal) => {
  if (newVal === 'myItems') {
    loadMyItems()
  }
})

watch([myItemsSearchKeyword, myItemsPoolFilter, myItemsRareFilter], () => {
  myItemsCurrentPage.value = 1
})

watch(drawTenLevel, () => {
  loadTenTicketAmount()
})

watch(storageSearchKeyword, () => {
  updateExpandedRares()
})
</script>

<style scoped>
.lottery-container {
  max-width: 900px;
  margin: 0 auto;
}

.lottery-card {
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
  gap: 8px;
}

.draw-section {
  text-align: center;
  padding: 40px 0;
}

.draw-header {
  margin-bottom: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.draw-buttons {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.draw-ten-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.item-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-tag {
  font-weight: bold;
}

.ticket-amount {
  font-size: 16px;
  color: #606266;
  font-weight: bold;
}

.draw-disabled-hint {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  color: #f56c6c;
  margin-top: 20px;
  font-size: 16px;
}

.draw-result {
  margin-top: 30px;
}

.draw-result h3 {
  margin-bottom: 20px;
  color: #333;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  background: #f5f7fa;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.result-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.result-item.result-rare-easy {
  border-left: 4px solid #909399;
}

.result-item.result-rare-normal {
  border-left: 4px solid #67c23a;
}

.result-item.result-rare-hard {
  border-left: 4px solid #e6a23c;
}

.result-item.result-rare-lunatic {
  border-left: 4px solid #f56c6c;
}

.result-name {
  font-size: 18px;
  font-weight: bold;
}

.new-tag {
  color: #f56c6c;
  font-size: 14px;
  margin-left: 8px;
}

.result-detail {
  color: #666;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.ten-draw-result .ten-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.redraw-info {
  margin-bottom: 12px;
}

.ten-draw-result .result-item {
  margin-bottom: 0;
}

.storage-header {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.storage-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rare-section {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.rare-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  font-weight: bold;
  color: #fff;
  cursor: pointer;
  user-select: none;
}

.rare-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.expand-icon {
  transition: transform 0.3s;
}

.expand-icon.is-expanded {
  transform: rotate(90deg);
}

.rare-header.rare-easy {
  background: #909399;
}

.rare-header.rare-normal {
  background: #67c23a;
}

.rare-header.rare-hard {
  background: #e6a23c;
}

.rare-header.rare-lunatic {
  background: #f56c6c;
}

.rare-count {
  font-size: 14px;
  opacity: 0.9;
}

.item-list {
  padding: 12px 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.item-tag {
  cursor: pointer;
  transition: transform 0.2s;
}

.item-tag:hover {
  transform: scale(1.05);
}

.empty-hint {
  color: #909399;
  font-size: 14px;
}

.my-items-header {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.search-section {
  margin-bottom: 20px;
}

.search-results {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cost-display {
  color: #f56c6c;
  font-weight: bold;
}

.item-detail-content {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 24px;
  padding-bottom: 8px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-row-full {
  grid-column: 1 / -1;
}

.detail-label {
  font-weight: 500;
  color: #909399;
  flex-shrink: 0;
  white-space: nowrap;
}

.detail-value {
  color: #303133;
  flex: 1;
  word-break: break-word;
}

.detail-divider-wrapper {
  margin: 0;
}

.detail-divider {
  margin: 8px 0 !important;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 0;
}

.detail-section-title {
  font-weight: 600;
  color: #303133;
  font-size: 15px;
}

.detail-section-content {
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
}

.empty-hint {
  color: #909399;
  font-style: italic;
}

@media screen and (max-width: 600px) {
  .card-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .storage-header,
  .my-items-header {
    flex-direction: column;
    align-items: stretch;
  }

  .storage-header .el-input,
  .storage-header .el-select,
  .my-items-header .el-input,
  .my-items-header .el-select {
    width: 100% !important;
    margin-left: 0 !important;
  }

  .draw-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .draw-header .el-select,
  .draw-header .el-button {
    width: 100%;
  }

  .draw-buttons {
    flex-direction: column;
    align-items: stretch;
    gap: 20px;
  }

  .draw-ten-section {
    width: 100%;
    flex-direction: column;
    gap: 12px;
  }

  .draw-ten-section .el-select {
    width: 100%;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
