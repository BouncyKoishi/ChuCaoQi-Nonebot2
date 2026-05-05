<template>
  <div class="docs-container">
    <el-card class="docs-card">
      <template #header>
        <div class="card-header">
          <h2>除草器指令文档</h2>
          <el-input
            v-model="searchQuery"
            placeholder="搜索指令..."
            :prefix-icon="Search"
            clearable
            style="width: 240px"
          />
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane
          v-for="cat in categories"
          :key="cat.name"
          :label="cat.name"
          :name="cat.name"
        >
          <template v-if="cat.subcategories.length > 1 || cat.subcategories[0] !== cat.name">
            <el-collapse v-model="expandedSubcategories[cat.name]">
              <el-collapse-item
                v-for="sub in cat.subcategories"
                :key="sub"
                :title="sub"
                :name="sub"
              >
                <div class="commands-grid">
                  <el-card
                    v-for="cmd in getFilteredCommands(cat.name, sub)"
                    :key="cmd.name"
                    shadow="hover"
                    class="command-card"
                  >
                    <div class="cmd-header">
                      <span class="cmd-name">{{ formatCmd(cmd.name) }}</span>
                      <div class="cmd-tags">
                        <el-tag
                          v-for="tag in cmd.tags"
                          :key="tag.text"
                          :type="tag.type"
                          size="small"
                          effect="plain"
                        >
                          {{ tag.text }}
                        </el-tag>
                      </div>
                    </div>
                    <div v-if="cmd.aliases?.length" class="cmd-aliases">
                      别名: {{ cmd.aliases.map(a => formatCmd(a)).join(', ') }}
                    </div>
                    <div v-if="cmd.params" class="cmd-params">
                      参数: {{ cmd.params }}
                    </div>
                    <el-divider />
                    <div class="cmd-description">{{ cmd.description }}</div>
                    <ul v-if="cmd.details?.length" class="cmd-details">
                      <li v-for="detail in cmd.details" :key="detail">{{ detail }}</li>
                    </ul>
                  </el-card>
                </div>
                <el-empty
                  v-if="getFilteredCommands(cat.name, sub).length === 0 && searchQuery"
                  description="没有匹配的指令"
                  :image-size="60"
                />
              </el-collapse-item>
            </el-collapse>
          </template>
          <template v-else>
            <div class="commands-grid">
              <el-card
                v-for="cmd in getFilteredCommands(cat.name, cat.subcategories[0])"
                :key="cmd.name"
                shadow="hover"
                class="command-card"
              >
                <div class="cmd-header">
                  <span class="cmd-name">{{ formatCmd(cmd.name) }}</span>
                <div class="cmd-tags">
                  <el-tag
                    v-for="tag in cmd.tags"
                    :key="tag.text"
                    :type="tag.type"
                    size="small"
                    effect="plain"
                  >
                    {{ tag.text }}
                  </el-tag>
                </div>
              </div>
              <div v-if="cmd.aliases?.length" class="cmd-aliases">
                别名: {{ cmd.aliases.map(a => formatCmd(a)).join(', ') }}
                </div>
                <div v-if="cmd.params" class="cmd-params">
                  参数: {{ cmd.params }}
                </div>
                <el-divider />
                <div class="cmd-description">{{ cmd.description }}</div>
                <ul v-if="cmd.details?.length" class="cmd-details">
                  <li v-for="detail in cmd.details" :key="detail">{{ detail }}</li>
                </ul>
              </el-card>
            </div>
            <el-empty
              v-if="getFilteredCommands(cat.name, cat.subcategories[0]).length === 0 && searchQuery"
              description="没有匹配的指令"
              :image-size="60"
            />
          </template>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { categories, commands } from '@/data/commands'
import { Search } from '@element-plus/icons-vue'
import { reactive, ref } from 'vue'

const searchQuery = ref('')
const activeTab = ref('生草系统')

const expandedSubcategories = reactive<Record<string, string[]>>({})
for (const cat of categories) {
  expandedSubcategories[cat.name] = [...cat.subcategories]
}

const getFilteredCommands = (category: string, subcategory: string) => {
  let filtered = commands.filter(
    cmd => cmd.category === category && cmd.subcategory === subcategory
  )
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    filtered = filtered.filter(cmd =>
      cmd.name.toLowerCase().includes(q) ||
      cmd.description.toLowerCase().includes(q) ||
      cmd.aliases?.some(a => a.toLowerCase().includes(q))
    )
  }
  return filtered
}

const cmdPrefix = (name: string) => name.startsWith('#') ? '' : '!'
const formatCmd = (name: string) => cmdPrefix(name) + name
</script>

<style scoped>
.docs-container {
  max-width: 1200px;
  margin: 0 auto;
}

.docs-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header h2 {
  margin: 0;
  color: #333;
}

.commands-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
}

.command-card {
  transition: transform 0.2s;
}

.command-card:hover {
  transform: translateY(-2px);
}

.command-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.cmd-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cmd-name {
  font-weight: bold;
  font-size: 15px;
  color: #303133;
  font-family: 'Courier New', Courier, monospace;
}

.cmd-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.cmd-aliases {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}

.cmd-params {
  margin-top: 4px;
  color: #606266;
  font-size: 13px;
}

.command-card :deep(.el-divider) {
  margin: 10px 0;
}

.cmd-description {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

.cmd-details {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.cmd-details li {
  margin-bottom: 2px;
}

:deep(.el-collapse-item__header) {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

:deep(.el-collapse-item__content) {
  padding-top: 12px;
}

@media screen and (max-width: 600px) {
  .commands-grid {
    grid-template-columns: 1fr;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .card-header .el-input {
    width: 100% !important;
  }
}
</style>
