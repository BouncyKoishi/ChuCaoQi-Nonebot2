<template>
  <div class="user-manage">
    <!-- 用户列表区 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-header">
          <span class="section-title">用户列表</span>
          <div class="search-bar">
            <el-input
              v-model="searchId"
              placeholder="按 ID 或 QQ 号搜索"
              clearable
              size="small"
              style="width: 200px"
              @keyup.enter="onSearch"
              @clear="onSearch"
            />
            <el-input
              v-model="searchName"
              placeholder="按昵称搜索"
              clearable
              size="small"
              style="width: 200px"
              @keyup.enter="onSearch"
              @clear="onSearch"
            />
            <el-button type="primary" size="small" @click="onSearch">搜索</el-button>
            <el-button size="small" @click="onReset">重置</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="userList"
        v-loading="loading"
        border
        stripe
        size="small"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="qq" label="QQ" width="120" />
        <el-table-column prop="name" label="昵称" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="信息员等级" width="90">
          <template #default="{ row }">
            <span>Lv{{ row.vipLevel }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="kusa" label="草数" width="130">
          <template #default="{ row }">
            {{ formatNum(row.kusa) }}
          </template>
        </el-table-column>
        <el-table-column prop="advKusa" label="草精数" width="120">
          <template #default="{ row }">
            {{ formatNum(row.advKusa) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <div class="op-cell">
              <el-button text type="primary" size="small" @click="openDetail(row)">详情</el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => handleCommand(cmd, row)">
                <el-button text type="primary" size="small">
                  更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="name">修改昵称</el-dropdown-item>
                    <el-dropdown-item command="title">授予称号</el-dropdown-item>
                    <el-dropdown-item command="donation">设置捐赠</el-dropdown-item>
                    <el-dropdown-item command="donations">捐赠信息</el-dropdown-item>
                    <el-dropdown-item command="chat">查看/设置 Chat 权限</el-dropdown-item>
                    <el-dropdown-item command="token">生成 webToken</el-dropdown-item>
                    <el-dropdown-item command="friendCode">查看好友码</el-dropdown-item>
                    <el-dropdown-item command="marks">帐号标记</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper, total"
        style="margin-top: 12px; justify-content: center"
        @current-change="fetchUsers"
      />
    </el-card>

    <!-- 称号管理区 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-header">
          <span class="section-title">称号管理</span>
          <el-button type="primary" size="small" @click="openCreateTitle">新增称号</el-button>
        </div>
      </template>

      <el-table :data="titleList" v-loading="titleLoading" border size="small" style="width: 100%">
        <el-table-column prop="name" label="称号名称" width="120" />
        <el-table-column prop="detail" label="描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.detail || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="ownerCount" label="拥有者数" width="100" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <div class="op-cell">
              <el-button text type="primary" size="small" @click="openOwnersDialog(row)">拥有者详情</el-button>
              <el-button text type="danger" size="small" @click="confirmDeleteTitle(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 用户详情弹窗 -->
    <el-dialog v-model="detailVisible" title="用户仓库详情" width="80%" top="5vh">
      <div v-if="detailData" v-loading="detailLoading">
        <el-descriptions :column="3" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="ID">{{ detailData.user.userId }}</el-descriptions-item>
          <el-descriptions-item label="QQ">{{ detailData.user.qq || '-' }}</el-descriptions-item>
          <el-descriptions-item label="昵称">{{ detailData.user.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="称号">{{ detailData.user.title || '-' }}</el-descriptions-item>
          <el-descriptions-item label="信息员等级">Lv{{ detailData.user.vipLevel }}</el-descriptions-item>
          <el-descriptions-item label="草数">{{ formatNum(detailData.user.kusa) }}</el-descriptions-item>
          <el-descriptions-item label="草精数">{{ formatNum(detailData.user.advKusa) }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 12px 0 8px">物品列表</h4>
        <el-table :data="detailData.items" border size="small" max-height="400">
          <el-table-column prop="item.name" label="名称" min-width="120" />
          <el-table-column prop="item.type" label="类型" width="80" />
          <el-table-column prop="item.detail" label="描述" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.item.detail || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="数量" width="100" />
          <el-table-column label="可用" width="80">
            <template #default="{ row }">
              <el-tag :type="row.allowUse ? 'success' : 'info'" size="small">
                {{ row.allowUse ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-else description="暂无数据" />
    </el-dialog>

    <!-- 修改昵称弹窗 -->
    <el-dialog v-model="nameDialog.visible" title="修改昵称" width="400px">
      <el-form label-width="80px">
        <el-form-item label="用户">
          <span>{{ nameDialog.userName }} (ID: {{ nameDialog.userId }})</span>
        </el-form-item>
        <el-form-item label="新昵称">
          <el-input v-model="nameDialog.name" placeholder="请输入新昵称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nameDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="nameDialog.loading" @click="submitName">确认</el-button>
      </template>
    </el-dialog>

    <!-- 授予称号弹窗 -->
    <el-dialog v-model="titleDialog.visible" title="授予称号" width="500px">
      <div v-loading="titleDialog.loadingTitles">
        <el-form label-width="80px">
          <el-form-item label="用户">
            <span>{{ titleDialog.userName }} (ID: {{ titleDialog.userId }})</span>
          </el-form-item>
          <el-form-item label="当前称号">
            <span v-if="titleDialog.currentTitle">
              <el-tag size="small" type="warning">{{ titleDialog.currentTitle }}</el-tag>
            </span>
            <span v-else class="no-owners">无</span>
          </el-form-item>
          <el-form-item label="已有称号">
            <div v-if="titleDialog.ownedTitles.length > 0">
              <el-tag
                v-for="t in titleDialog.ownedTitles"
                :key="t.name"
                size="small"
                :type="t.inUse ? 'warning' : 'info'"
                style="margin: 2px"
              >
                {{ t.name }}{{ t.inUse ? '(使用中)' : '' }}
              </el-tag>
            </div>
            <span v-else class="no-owners">无</span>
          </el-form-item>
          <el-form-item label="选择称号">
            <el-select
              v-model="titleDialog.title"
              placeholder="请选择称号"
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="t in selectableTitles"
                :key="t.name"
                :label="t.name"
                :value="t.name"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="titleDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="titleDialog.loading" @click="submitTitle">确认授予</el-button>
      </template>
    </el-dialog>

    <!-- 设置捐赠弹窗 -->
    <el-dialog v-model="donationDialog.visible" title="设置捐赠金额" width="400px">
      <el-form label-width="100px">
        <el-form-item label="用户">
          <span>{{ donationDialog.userName }} (ID: {{ donationDialog.userId }})</span>
        </el-form-item>
        <el-form-item label="金额(元)">
          <el-input-number v-model="donationDialog.amount" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="donationDialog.source" style="width: 100%">
            <el-option label="QQ红包" value="qq" />
            <el-option label="爱发电" value="ifd" />
            <el-option label="微信" value="wx" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          :title="`说明：此操作会追加该用户的投喂记录；累计≥20元将自动发放&quot;投喂者&quot;称号`"
          style="margin-top: 8px"
        />
      </el-form>
      <template #footer>
        <el-button @click="donationDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="donationDialog.loading" @click="submitDonation">确认</el-button>
      </template>
    </el-dialog>

    <!-- 捐赠信息弹窗 -->
    <el-dialog v-model="donationsDialog.visible" title="捐赠信息" width="600px">
      <div v-loading="donationsDialog.loading">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="用户">{{ donationsDialog.userName }} (ID: {{ donationsDialog.userId }})</el-descriptions-item>
          <el-descriptions-item label="累计捐赠">¥{{ (donationsDialog.total || 0).toFixed(2) }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 8px 0">捐赠记录</h4>
        <el-table :data="donationsDialog.records" border size="small" max-height="300">
          <el-table-column prop="donateDate" label="日期" width="120" />
          <el-table-column prop="amount" label="金额(元)" width="120">
            <template #default="{ row }">
              ¥{{ row.amount.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" min-width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="sourceTagType(row.source)">{{ sourceLabel(row.source) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button text type="danger" size="small" @click="deleteDonationRecord(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="donationsDialog.records.length === 0 && !donationsDialog.loading" description="暂无捐赠记录" />
      </div>
      <template #footer>
        <el-button @click="donationsDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="goAddDonation">添加捐赠记录</el-button>
      </template>
    </el-dialog>

    <!-- Chat 权限弹窗 -->
    <el-dialog v-model="chatDialog.visible" title="Chat 权限" width="500px">
      <div v-loading="chatDialog.loading">
        <el-descriptions v-if="chatDialog.data" :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="已激活">{{ chatDialog.data.activated ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="当前模型">{{ chatDialog.data.chosenModel || '-' }}</el-descriptions-item>
          <el-descriptions-item label="累计 Token">{{ chatDialog.data.tokenUse }}</el-descriptions-item>
          <el-descriptions-item label="今日 Token">{{ chatDialog.data.todayTokenUse }}</el-descriptions-item>
        </el-descriptions>

        <el-form label-width="120px" v-if="chatDialog.formData">
          <el-form-item label="允许私聊">
            <el-switch v-model="chatDialog.formData.allowPrivate" />
          </el-form-item>
          <el-form-item label="允许角色卡">
            <el-switch v-model="chatDialog.formData.allowRole" />
          </el-form-item>
          <el-form-item label="允许高级模型">
            <el-switch v-model="chatDialog.formData.allowAdvancedModel" />
          </el-form-item>
          <el-form-item label="每日 Token 限额">
            <el-radio-group v-model="chatDialog.formData.dailyLimitMode">
              <el-radio value="default">默认(1万)</el-radio>
              <el-radio value="high">高(100万)</el-radio>
              <el-radio value="unlimited">无限</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="chatDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="chatDialog.submitting" @click="submitChatPermission">保存</el-button>
      </template>
    </el-dialog>

    <!-- 生成 webToken 弹窗 -->
    <el-dialog v-model="tokenDialog.visible" title="生成 webToken" width="500px">
      <div v-loading="tokenDialog.loading">
        <p style="margin: 0 0 12px">
          为用户 <strong>{{ tokenDialog.userName }} (ID: {{ tokenDialog.userId }})</strong> 生成新的 webToken：
        </p>
        <el-input
          v-if="tokenDialog.token"
          v-model="tokenDialog.token"
          readonly
          type="textarea"
          :rows="2"
        />
        <el-alert
          v-if="tokenDialog.token"
          type="warning"
          :closable="false"
          title="生成后旧 Token 会立即失效，请将新 Token 安全交付给用户"
          style="margin-top: 12px"
        />
      </div>
      <template #footer>
        <el-button @click="tokenDialog.visible = false">关闭</el-button>
        <el-button
          type="primary"
          :loading="tokenDialog.loading"
          @click="submitGenerateToken"
          v-if="!tokenDialog.token"
        >
          确认生成
        </el-button>
      </template>
    </el-dialog>

    <!-- 生成好友码弹窗 -->
    <el-dialog v-model="friendCodeDialog.visible" title="查看好友码" width="500px">
      <div v-loading="friendCodeDialog.loading">
        <p style="margin: 0 0 12px">
          用户 <strong>{{ friendCodeDialog.userName }} (QQ: {{ friendCodeDialog.qq }})</strong> 的好友码：
        </p>
        <el-input
          v-if="friendCodeDialog.code"
          v-model="friendCodeDialog.code"
          readonly
          style="font-size: 18px; text-align: center"
        />
        <el-alert
          v-if="friendCodeDialog.code"
          type="info"
          :closable="false"
          title="好友码每日更新，用户需在好友申请备注中填写当日好友码，bot 将自动通过申请"
          style="margin-top: 12px"
        />
      </div>
      <template #footer>
        <el-button @click="friendCodeDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 帐号标记弹窗 -->
    <el-dialog v-model="marksDialog.visible" title="帐号标记" width="500px">
      <div v-loading="marksDialog.loading">
        <p style="margin: 0 0 16px">
          用户 <strong>{{ marksDialog.userName }} (ID: {{ marksDialog.userId }})</strong>
        </p>
        <el-form label-width="100px">
          <el-form-item label="小号关联">
            <el-select
              v-model="marksDialog.relatedUserId"
              filterable
              remote
              clearable
              :remote-method="searchUserForMarks"
              :loading="marksDialog.searchLoading"
              placeholder="搜索 QQ号或昵称选择主号，留空取消关联"
              style="width: 100%"
            >
              <el-option
                v-for="u in marksDialog.searchResults"
                :key="u.id"
                :label="`${u.name || '(无昵称)'} (${u.qq || u.id})`"
                :value="u.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="机械臂标记">
            <el-switch v-model="marksDialog.isRobot" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="marksDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="marksDialog.submitting" @click="submitMarks">确认</el-button>
      </template>
    </el-dialog>

    <!-- 新增称号弹窗 -->
    <el-dialog v-model="createTitleDialog.visible" title="新增称号" width="400px">
      <el-form label-width="80px">
        <el-form-item label="称号名称" required>
          <el-input v-model="createTitleDialog.name" placeholder="请输入称号名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="createTitleDialog.detail"
            type="textarea"
            :rows="2"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createTitleDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="createTitleDialog.loading" @click="submitCreateTitle">创建</el-button>
      </template>
    </el-dialog>

    <!-- 拥有者详情弹窗 -->
    <el-dialog v-model="ownersDialog.visible" :title='`称号"${ownersDialog.titleName}"拥有者`' width="80%" top="5vh">
      <el-table :data="ownersDialog.list" v-loading="ownersDialog.loading" border stripe size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="qq" label="QQ" width="120" />
        <el-table-column prop="name" label="昵称" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="title" label="称号" min-width="80" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.title" size="small" type="warning">{{ row.title }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="信息员等级" width="90">
          <template #default="{ row }">
            <span>Lv{{ row.vipLevel }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="kusa" label="草数" width="130">
          <template #default="{ row }">
            {{ formatNum(row.kusa) }}
          </template>
        </el-table-column>
        <el-table-column prop="advKusa" label="草精数" width="120">
          <template #default="{ row }">
            {{ formatNum(row.advKusa) }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { adminApi } from '@/api'
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

// ==================== 用户列表 ====================
const userList = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)
const searchId = ref('')
const searchName = ref('')

const fetchUsers = async () => {
  loading.value = true
  try {
    const data = await adminApi.getUsers(
      currentPage.value,
      pageSize,
      searchId.value || undefined,
      searchName.value || undefined
    )
    userList.value = data.list
    total.value = data.total
  } catch (e: any) {
    ElMessage.error(e.message || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

defineExpose({ refresh: fetchUsers })

const onSearch = () => {
  currentPage.value = 1
  fetchUsers()
}

const onReset = () => {
  searchId.value = ''
  searchName.value = ''
  currentPage.value = 1
  fetchUsers()
}

const formatNum = (n: number) => {
  if (n === undefined || n === null) return '0'
  return n.toLocaleString()
}

// ==================== 称号管理 ====================
const titleList = ref<any[]>([])
const titleLoading = ref(false)

const selectableTitles = computed(() => titleList.value)

const fetchTitles = async () => {
  titleLoading.value = true
  try {
    const data = await adminApi.getTitles()
    titleList.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '获取称号列表失败')
  } finally {
    titleLoading.value = false
  }
}

const createTitleDialog = reactive({
  visible: false,
  name: '',
  detail: '',
  loading: false
})

const openCreateTitle = () => {
  createTitleDialog.name = ''
  createTitleDialog.detail = ''
  createTitleDialog.visible = true
}

const submitCreateTitle = async () => {
  if (!createTitleDialog.name.trim()) {
    ElMessage.warning('请输入称号名称')
    return
  }
  createTitleDialog.loading = true
  try {
    await adminApi.createTitle(createTitleDialog.name.trim(), createTitleDialog.detail.trim() || undefined)
    ElMessage.success('称号已创建')
    createTitleDialog.visible = false
    fetchTitles()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    createTitleDialog.loading = false
  }
}

const confirmDeleteTitle = (row: any) => {
  ElMessageBox.confirm(
    `确定要删除称号"${row.name}"吗？该称号当前有 ${row.ownerCount} 个持有者，删除后所有持有记录将一并清除。`,
    '危险操作',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消'
    }
  )
    .then(async () => {
      try {
        await adminApi.deleteTitle(row.name)
        ElMessage.success('称号已删除')
        fetchTitles()
      } catch (e: any) {
        ElMessage.error(e.message || '删除失败')
      }
    })
    .catch(() => {})
}

// ==================== 操作路由 ====================
const handleCommand = (cmd: string, row: any) => {
  switch (cmd) {
    case 'name':
      openNameDialog(row)
      break
    case 'title':
      openTitleDialog(row)
      break
    case 'donation':
      openDonationDialog(row)
      break
    case 'donations':
      openDonationsDialog(row)
      break
    case 'chat':
      openChatDialog(row)
      break
    case 'token':
      openTokenDialog(row)
      break
    case 'friendCode':
      openFriendCodeDialog(row)
      break
    case 'marks':
      openMarksDialog(row)
      break
  }
}

// ==================== 详情弹窗 ====================
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<any>(null)

const openDetail = async (row: any) => {
  detailVisible.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    const data = await adminApi.getUserWarehouse(row.id)
    detailData.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '获取详情失败')
  } finally {
    detailLoading.value = false
  }
}

// ==================== 修改昵称 ====================
const nameDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  name: '',
  loading: false
})

const openNameDialog = (row: any) => {
  nameDialog.userId = row.id
  nameDialog.userName = row.name || row.qq || String(row.id)
  nameDialog.name = row.name || ''
  nameDialog.visible = true
}

const submitName = async () => {
  if (!nameDialog.name.trim()) {
    ElMessage.warning('昵称不能为空')
    return
  }
  nameDialog.loading = true
  try {
    await adminApi.updateUserName(nameDialog.userId, nameDialog.name.trim())
    ElMessage.success('昵称已更新')
    nameDialog.visible = false
    fetchUsers()
  } catch (e: any) {
    ElMessage.error(e.message || '修改失败')
  } finally {
    nameDialog.loading = false
  }
}

// ==================== 授予称号 ====================
const titleDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  title: '',
  loading: false,
  loadingTitles: false,
  currentTitle: '' as string,
  ownedTitles: [] as { name: string; detail: string; amount: number; inUse: boolean }[]
})

const openTitleDialog = async (row: any) => {
  titleDialog.userId = row.id
  titleDialog.userName = row.name || row.qq || String(row.id)
  titleDialog.title = ''
  titleDialog.currentTitle = ''
  titleDialog.ownedTitles = []
  titleDialog.visible = true
  titleDialog.loadingTitles = true
  try {
    const res: any = await adminApi.getUserTitles(row.id)
    titleDialog.currentTitle = res.currentTitle || ''
    titleDialog.ownedTitles = res.titles || []
  } catch (e: any) {
    ElMessage.error(e.message || '获取用户称号失败')
  } finally {
    titleDialog.loadingTitles = false
  }
}

const submitTitle = async () => {
  if (!titleDialog.title) {
    ElMessage.warning('请选择称号')
    return
  }
  titleDialog.loading = true
  try {
    await adminApi.giveUserTitle(titleDialog.userId, titleDialog.title)
    ElMessage.success('称号已授予')
    titleDialog.visible = false
    fetchUsers()
    fetchTitles()
  } catch (e: any) {
    ElMessage.error(e.message || '授予失败')
  } finally {
    titleDialog.loading = false
  }
}

// ==================== 设置捐赠 ====================
const donationDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  amount: 0,
  source: 'qq',
  loading: false
})

const openDonationDialog = (row: any) => {
  donationDialog.userId = row.id
  donationDialog.userName = row.name || row.qq || String(row.id)
  donationDialog.amount = 0
  donationDialog.source = 'qq'
  donationDialog.visible = true
}

const submitDonation = async () => {
  if (donationDialog.amount <= 0) {
    ElMessage.warning('金额必须大于0')
    return
  }
  donationDialog.loading = true
  try {
    const res: any = await adminApi.setUserDonation(
      donationDialog.userId,
      donationDialog.amount,
      donationDialog.source
    )
    let msg = '捐赠记录已添加'
    if (res.totalDonate !== undefined) {
      msg += `（累计: ¥${res.totalDonate.toFixed(2)}）`
    }
    if (res.autoTitles && res.autoTitles.length > 0) {
      msg += `，已自动发放称号: ${res.autoTitles.join('、')}`
    }
    ElMessage.success(msg)
    donationDialog.visible = false
  } catch (e: any) {
    ElMessage.error(e.message || '设置失败')
  } finally {
    donationDialog.loading = false
  }
}

// ==================== 捐赠信息 ====================
const donationsDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  total: 0,
  records: [] as { id: number; amount: number; donateDate: string; source: string }[],
  loading: false
})

const sourceLabel = (source: string) => {
  const map: Record<string, string> = { qq: 'QQ红包', ifd: '爱发电', wx: '微信', other: '其他', afdian: '爱发电' }
  return map[source] || source || '-'
}

const sourceTagType = (source: string) => {
  if (source === 'ifd' || source === 'afdian') return 'success'
  if (source === 'qq') return 'warning'
  if (source === 'wx') return 'primary'
  return 'info'
}

const openDonationsDialog = async (row: any) => {
  donationsDialog.userId = row.id
  donationsDialog.userName = row.name || row.qq || String(row.id)
  donationsDialog.total = 0
  donationsDialog.records = []
  donationsDialog.visible = true
  donationsDialog.loading = true
  try {
    const res: any = await adminApi.getUserDonations(row.id)
    donationsDialog.total = res.total || 0
    donationsDialog.records = res.records || []
  } catch (e: any) {
    ElMessage.error(e.message || '获取捐赠信息失败')
  } finally {
    donationsDialog.loading = false
  }
}

const goAddDonation = () => {
  donationsDialog.visible = false
  openDonationDialog({ id: donationsDialog.userId, name: donationsDialog.userName })
}

const deleteDonationRecord = (row: { id: number; amount: number; donateDate: string }) => {
  ElMessageBox.confirm(
    `确定要删除该捐赠记录吗？（日期: ${row.donateDate}，金额: ¥${row.amount.toFixed(2)}）`,
    '确认删除',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    }
  )
    .then(async () => {
      try {
        const res: any = await adminApi.deleteUserDonation(donationsDialog.userId, row.id)
        let msg = '记录已删除'
        if (res.totalDonate !== undefined) {
          msg += `（累计: ¥${res.totalDonate.toFixed(2)}）`
        }
        if (res.revokedTitles && res.revokedTitles.length > 0) {
          msg += `，已回收称号: ${res.revokedTitles.join('、')}`
        }
        ElMessage.success(msg)
        // 刷新捐赠记录列表
        const donationsRes: any = await adminApi.getUserDonations(donationsDialog.userId)
        donationsDialog.total = donationsRes.total || 0
        donationsDialog.records = donationsRes.records || []
      } catch (e: any) {
        ElMessage.error(e.message || '删除失败')
      }
    })
    .catch(() => {})
}

// ==================== Chat 权限 ====================
const chatDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  data: null as any,
  formData: null as null | {
    allowPrivate: boolean
    allowRole: boolean
    allowAdvancedModel: boolean
    dailyLimitMode: 'default' | 'high' | 'unlimited'
  },
  loading: false,
  submitting: false
})

const openChatDialog = async (row: any) => {
  chatDialog.userId = row.id
  chatDialog.userName = row.name || row.qq || String(row.id)
  chatDialog.data = null
  chatDialog.formData = null
  chatDialog.visible = true
  chatDialog.loading = true
  try {
    const res: any = await adminApi.getUserChatPermission(row.id)
    // 拦截器已解包，res 即权限数据对象
    chatDialog.data = res
    // 根据 dailyTokenLimit 还原模式
    let mode: 'default' | 'high' | 'unlimited' = 'default'
    if (res.dailyTokenLimit === -1) mode = 'unlimited'
    else if (res.dailyTokenLimit >= 1000000) mode = 'high'
    chatDialog.formData = {
      allowPrivate: res.allowPrivate,
      allowRole: res.allowRole,
      allowAdvancedModel: res.allowAdvancedModel,
      dailyLimitMode: mode
    }
  } catch (e: any) {
    ElMessage.error(e.message || '获取权限失败')
  } finally {
    chatDialog.loading = false
  }
}

const submitChatPermission = async () => {
  if (!chatDialog.formData) return
  chatDialog.submitting = true
  try {
    await adminApi.updateUserChatPermission(chatDialog.userId, chatDialog.formData)
    ElMessage.success('Chat 权限已更新')
    chatDialog.visible = false
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    chatDialog.submitting = false
  }
}

// ==================== 生成 webToken ====================
const tokenDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  token: '',
  loading: false
})

const openTokenDialog = (row: any) => {
  tokenDialog.userId = row.id
  tokenDialog.userName = row.name || row.qq || String(row.id)
  tokenDialog.token = ''
  tokenDialog.visible = true
}

const submitGenerateToken = async () => {
  tokenDialog.loading = true
  try {
    const res: any = await adminApi.generateUserWebToken(tokenDialog.userId)
    if (res.success && res.token) {
      tokenDialog.token = res.token
      ElMessage.success('Token 已生成')
    } else {
      ElMessage.error(res.error || '生成失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    tokenDialog.loading = false
  }
}

// ==================== 生成好友码 ====================
const friendCodeDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  qq: '',
  code: '',
  loading: false
})

const openFriendCodeDialog = async (row: any) => {
  friendCodeDialog.visible = true
  friendCodeDialog.userId = row.id
  friendCodeDialog.userName = row.name || '(无昵称)'
  friendCodeDialog.qq = row.qq || ''
  friendCodeDialog.code = ''
  friendCodeDialog.loading = true
  try {
    const res: any = await adminApi.generateFriendCode(row.id)
    if (res.success && res.code) {
      friendCodeDialog.code = res.code
      friendCodeDialog.qq = res.qq || friendCodeDialog.qq
    } else {
      ElMessage.error(res.error || '生成失败')
      friendCodeDialog.visible = false
    }
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
    friendCodeDialog.visible = false
  } finally {
    friendCodeDialog.loading = false
  }
}

// ==================== 帐号标记 ====================
const marksDialog = reactive({
  visible: false,
  userId: 0,
  userName: '',
  relatedUserId: null as number | null,
  isRobot: false,
  loading: false,
  submitting: false,
  searchLoading: false,
  searchResults: [] as any[]
})

const openMarksDialog = async (row: any) => {
  marksDialog.visible = true
  marksDialog.userId = row.id
  marksDialog.userName = row.name ? `${row.name}(${row.qq})` : row.qq || `ID:${row.id}`
  marksDialog.relatedUserId = null
  marksDialog.isRobot = false
  marksDialog.searchResults = []
  marksDialog.loading = true
  try {
    const res: any = await adminApi.getAccountMarks(row.id)
    if (res.success) {
      marksDialog.relatedUserId = res.relatedUserId ?? null
      marksDialog.isRobot = res.isRobot ?? false
      // 如果已有关联用户，放入搜索结果供显示
      if (res.relatedUser) {
        marksDialog.searchResults = [{
          id: res.relatedUser.userId,
          qq: res.relatedUser.qq,
          name: res.relatedUser.name
        }]
      }
    } else {
      ElMessage.error(res.error || '获取标记失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '获取标记失败')
  } finally {
    marksDialog.loading = false
  }
}

const searchUserForMarks = async (query: string) => {
  if (!query) {
    marksDialog.searchResults = []
    return
  }
  marksDialog.searchLoading = true
  try {
    const res: any = await adminApi.getUsers(1, 20, query)
    marksDialog.searchResults = res.list || []
  } catch {
    marksDialog.searchResults = []
  } finally {
    marksDialog.searchLoading = false
  }
}

const submitMarks = async () => {
  marksDialog.submitting = true
  try {
    const res: any = await adminApi.updateAccountMarks(marksDialog.userId, {
      relatedUserId: marksDialog.relatedUserId,
      isRobot: marksDialog.isRobot
    })
    if (res.success) {
      ElMessage.success('帐号标记已更新')
      marksDialog.visible = false
      fetchUsers()
    } else {
      ElMessage.error(res.error || '更新失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    marksDialog.submitting = false
  }
}

// ==================== 称号拥有者详情 ====================
const ownersDialog = reactive({
  visible: false,
  titleName: '',
  list: [] as any[],
  loading: false
})

const openOwnersDialog = async (row: { name: string }) => {
  ownersDialog.titleName = row.name
  ownersDialog.list = []
  ownersDialog.visible = true
  ownersDialog.loading = true
  try {
    const res: any = await adminApi.getTitleOwners(row.name)
    ownersDialog.list = res.owners || []
  } catch (e: any) {
    ElMessage.error(e.message || '获取拥有者详情失败')
  } finally {
    ownersDialog.loading = false
  }
}

// ==================== 初始化 ====================
onMounted(() => {
  fetchUsers()
  fetchTitles()
})
</script>

<style scoped>
.user-manage {
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

.search-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.op-cell {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

.op-cell .el-button {
  padding: 5px 6px;
  min-width: auto;
}

.more-owners {
  color: #909399;
  font-size: 12px;
  margin-left: 4px;
}

.no-owners {
  color: #c0c4cc;
  font-size: 12px;
}
</style>
