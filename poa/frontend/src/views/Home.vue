<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
      <el-button type="primary" @click="wsDialogVisible = true"><el-icon><Plus /></el-icon> 新建工作区</el-button>
    </div>

    <!-- 工作区列表 -->
    <el-row :gutter="20">
      <el-col :span="8" v-for="ws in store.workspaces" :key="ws.id" style="margin-bottom: 20px;">
        <el-card shadow="hover" @click="selectWorkspace(ws.id)" style="cursor: pointer;">
          <template #header><strong>{{ ws.name }}</strong></template>
          <p style="color: #909399; font-size: 13px;">{{ ws.description || '暂无描述' }}</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 选中工作区后展示项目 -->
    <el-divider v-if="selectedWsId" />
    <div v-if="selectedWsId">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
        <h3>项目列表</h3>
        <el-button type="success" @click="projDialogVisible = true"><el-icon><Plus /></el-icon> 新建项目</el-button>
      </div>
      <el-table :data="filteredProjects" stripe @row-click="(row: any) => $router.push(`/project/${row.id}`)">
        <el-table-column prop="name" label="项目名称" />
        <el-table-column prop="base_url" label="Base URL" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建工作区对话框 -->
    <el-dialog v-model="wsDialogVisible" title="新建工作区" width="400px">
      <el-form :model="wsForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="wsForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="wsForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="wsDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createWs">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新建项目对话框 -->
    <el-dialog v-model="projDialogVisible" title="新建项目" width="500px">
      <el-form :model="projForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="projForm.name" /></el-form-item>
        <el-form-item label="Base URL"><el-input v-model="projForm.base_url" placeholder="https://api.example.com" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="projForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createProject">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useWorkspaceStore } from '../stores/workspace'

const store = useWorkspaceStore()
const selectedWsId = ref<number | null>(null)
const wsDialogVisible = ref(false)
const projDialogVisible = ref(false)
const wsForm = reactive({ name: '', description: '' })
const projForm = reactive({ name: '', base_url: '', description: '' })

const filteredProjects = computed(() =>
  selectedWsId.value ? store.projects.filter(p => p.workspace_id === selectedWsId.value) : []
)

onMounted(() => { store.loadWorkspaces() })

async function selectWorkspace(wsId: number) {
  selectedWsId.value = wsId
  await store.loadProjects(wsId)
}

async function createWs() {
  if (!wsForm.name) return ElMessage.warning('请输入名称')
  await store.createWorkspace({ ...wsForm })
  ElMessage.success('创建成功')
  wsDialogVisible.value = false
  wsForm.name = ''; wsForm.description = ''
}

async function createProject() {
  if (!projForm.name || !selectedWsId.value) return ElMessage.warning('请输入名称')
  await store.createProject({ workspace_id: selectedWsId.value, ...projForm })
  ElMessage.success('创建成功')
  projDialogVisible.value = false
  projForm.name = ''; projForm.base_url = ''; projForm.description = ''
  await store.loadProjects(selectedWsId.value)
}

function formatDate(d: string) { return d ? new Date(d).toLocaleString('zh-CN') : '' }
</script>