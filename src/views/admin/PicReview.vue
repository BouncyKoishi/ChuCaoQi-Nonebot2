<template>
  <div class="pic-review">
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-header">
          <div class="header-left">
            <span class="section-title">图片审核</span>
            <el-tag v-if="pendingList.length > 0" size="small" type="warning">
              待审核 {{ pendingList.length }} 张
            </el-tag>
            <el-tag v-else-if="!loading" size="small" type="success">无待审核图片</el-tag>
          </div>
          <div class="header-right">
            <el-button size="small" @click="refresh" :loading="loading">刷新列表</el-button>
          </div>
        </div>
      </template>

      <div v-loading="loading">
        <!-- 空状态 -->
        <el-empty v-if="!loading && pendingList.length === 0" description="没有待审核图片" />

        <!-- 审核视图 -->
        <div v-else-if="currentPic" class="review-view">
          <!-- 顶部导航 -->
          <div class="review-nav">
            <el-button size="small" :disabled="currentIndex === 0" @click="goPrev">
              <el-icon><ArrowLeft /></el-icon> 上一张
            </el-button>
            <span class="nav-position">{{ currentIndex + 1 }} / {{ pendingList.length }}</span>
            <el-button size="small" :disabled="currentIndex >= pendingList.length - 1" @click="goNext">
              下一张 <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>

          <el-row :gutter="16">
            <!-- 图片预览 -->
            <el-col :xs="24" :md="14">
              <div class="pic-preview">
                <el-image
                  :src="currentPicBlobUrl"
                  fit="contain"
                  :preview-src-list="currentPicBlobUrl ? [currentPicBlobUrl] : []"
                  preview-teleported
                  class="pic-image"
                  v-loading="imageLoading"
                >
                  <template #error>
                    <div class="pic-error">
                      <el-icon><Picture /></el-icon>
                      <span>图片加载失败</span>
                    </div>
                  </template>
                  <template #placeholder>
                    <div class="pic-loading">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      <span>加载中...</span>
                    </div>
                  </template>
                </el-image>
              </div>
            </el-col>

            <!-- 信息与操作 -->
            <el-col :xs="24" :md="10">
              <div class="pic-info-panel">
                <h4>图片信息</h4>
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="文件名">{{ currentPic.filename }}</el-descriptions-item>
                  <el-descriptions-item label="文件大小">{{ currentPic.sizeStr }}</el-descriptions-item>
                  <el-descriptions-item label="上传者QQ">{{ currentPic.uploaderQQ || '-' }}</el-descriptions-item>
                </el-descriptions>

                <h4 style="margin-top: 20px">分类操作</h4>
                <p class="tip-text">点击按钮即分类（移动到对应图库目录）</p>
                <div class="category-grid">
                  <el-button
                    v-for="cat in categories"
                    :key="cat.key"
                    type="primary"
                    plain
                    size="small"
                    class="category-btn"
                    :loading="operating && operatingCategory === cat.key"
                    @click="doClassify(cat.key)"
                  >
                    {{ cat.name }}
                  </el-button>
                </div>

                <h4 style="margin-top: 20px">其他操作</h4>
                <div class="other-actions">
                  <el-button :loading="operating && opType === 'skip'" @click="doSkip" size="small">跳过</el-button>
                  <el-button type="success" plain :loading="operating && opType === 'save'" @click="doSave" size="small">移到私藏</el-button>
                  <el-button type="danger" plain :loading="operating && opType === 'delete'" @click="doDelete" size="small">删除</el-button>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { adminApi } from '@/api'
import { ArrowLeft, ArrowRight, Loading, Picture } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

interface PicItem {
  filename: string
  size: number
  sizeStr: string
  uploaderQQ: string | null
}

const loading = ref(false)
const operating = ref(false)
const opType = ref<'' | 'skip' | 'save' | 'delete' | 'classify'>('')
const operatingCategory = ref('')
const pendingList = ref<PicItem[]>([])
const categories = ref<{ key: string; name: string }[]>([])
const currentIndex = ref(0)

const currentPic = computed(() => pendingList.value[currentIndex.value] || null)
const currentPicBlobUrl = ref('')
const imageLoading = ref(false)

watch(
  () => currentPic.value,
  async (newPic) => {
    // 释放旧 blob URL
    if (currentPicBlobUrl.value) {
      URL.revokeObjectURL(currentPicBlobUrl.value)
      currentPicBlobUrl.value = ''
    }
    if (!newPic) return
    imageLoading.value = true
    try {
      const blob = await adminApi.fetchPicImage(newPic.filename)
      currentPicBlobUrl.value = URL.createObjectURL(blob)
    } catch (e: any) {
      ElMessage.error('图片加载失败')
    } finally {
      imageLoading.value = false
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  if (currentPicBlobUrl.value) {
    URL.revokeObjectURL(currentPicBlobUrl.value)
  }
})

const fetchCategories = async () => {
  try {
    categories.value = await adminApi.getPicCategories()
  } catch (e: any) {
    ElMessage.error(e.message || '获取分类失败')
  }
}

const refresh = async () => {
  loading.value = true
  try {
    const data = await adminApi.getPendingPics()
    pendingList.value = data
    if (currentIndex.value >= pendingList.value.length) {
      currentIndex.value = Math.max(0, pendingList.value.length - 1)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '获取列表失败')
  } finally {
    loading.value = false
  }
}

defineExpose({ refresh })

const goPrev = () => {
  if (currentIndex.value > 0) currentIndex.value--
}

const goNext = () => {
  if (currentIndex.value < pendingList.value.length - 1) currentIndex.value++
}

// 操作完成后：移除当前项，自动到下一张
const removeCurrentAndAdvance = () => {
  pendingList.value.splice(currentIndex.value, 1)
  if (currentIndex.value >= pendingList.value.length) {
    currentIndex.value = Math.max(0, pendingList.value.length - 1)
  }
}

const doClassify = async (categoryKey: string) => {
  if (!currentPic.value) return
  operating.value = true
  operatingCategory.value = categoryKey
  try {
    const res: any = await adminApi.classifyPic(currentPic.value.filename, categoryKey)
    if (res.success !== false) {
      ElMessage.success(res.message || '已分类')
      removeCurrentAndAdvance()
    } else {
      ElMessage.error(res.error || '分类失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '分类失败')
  } finally {
    operating.value = false
    operatingCategory.value = ''
  }
}

const doSkip = async () => {
  if (!currentPic.value) return
  operating.value = true
  opType.value = 'skip'
  try {
    await adminApi.skipPic(currentPic.value.filename)
    ElMessage.success('已跳过')
    goNext()
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    operating.value = false
    opType.value = ''
  }
}

const doSave = async () => {
  if (!currentPic.value) return
  operating.value = true
  opType.value = 'save'
  try {
    const res: any = await adminApi.savePic(currentPic.value.filename)
    if (res.success !== false) {
      ElMessage.success(res.message || '已移到私藏')
      removeCurrentAndAdvance()
    } else {
      ElMessage.error(res.error || '操作失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    operating.value = false
    opType.value = ''
  }
}

const doDelete = async () => {
  if (!currentPic.value) return
  ElMessageBox.confirm(
    `确定要删除图片 "${currentPic.value.filename}" 吗？此操作不可恢复。`,
    '危险操作',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  )
    .then(async () => {
      operating.value = true
      opType.value = 'delete'
      try {
        const res: any = await adminApi.deletePic(currentPic.value.filename)
        if (res.success !== false) {
          ElMessage.success(res.message || '已删除')
          removeCurrentAndAdvance()
        } else {
          ElMessage.error(res.error || '删除失败')
        }
      } catch (e: any) {
        ElMessage.error(e.message || '删除失败')
      } finally {
        operating.value = false
        opType.value = ''
      }
    })
    .catch(() => {})
}

onMounted(() => {
  fetchCategories()
  refresh()
})
</script>

<style scoped>
.pic-review {
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

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.review-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.review-nav {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.nav-position {
  font-size: 14px;
  color: #606266;
  min-width: 60px;
  text-align: center;
}

.pic-preview {
  background: #f5f7fa;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.pic-image {
  width: 100%;
  height: 500px;
}

.pic-image :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: zoom-in;
}

.pic-error,
.pic-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #909399;
  padding: 40px;
}

.pic-info-panel h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #303133;
}

.tip-text {
  font-size: 12px;
  color: #909399;
  margin: 0 0 8px;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.category-btn {
  margin: 0 !important;
}

.other-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
