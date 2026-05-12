<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
      <h3>测试套件</h3>
      <el-button type="primary" @click="showCreateDialog"><el-icon><Plus /></el-icon> 新建套件</el-button>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-table :data="suites" stripe @row-click="selectSuite">
          <el-table-column prop="name" label="套件名称" />
          <el-table-column prop="description" label="描述" />
          <el-table-column label="步骤数" width="100">
            <template #default="{ row }">{{ row.steps?.length || 0 }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button size="small" type="success" :loading="runningId === row.id" @click.stop="runSuite(row)">运行</el-button>
              <el-button size="small" @click.stop="editSuite(row)">编辑</el-button>
              <el-button size="small" type="danger" @click.stop="deleteSuite(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-col>
      <el-col :span="8">
        <div v-if="runResult" class="card-section">
          <h4>运行结果</h4>
          <el-descriptions :column="2" border size="small" style="margin-bottom: 10px;">
            <el-descriptions-item label="总计">{{ runResult.total }}</el-descriptions-item>
            <el-descriptions-item label="通过"><el-tag type="success">{{ runResult.passed }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="失败"><el-tag type="danger">{{ runResult.failed }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="耗时">{{ runResult.duration }}ms</el-descriptions-item>
          </el-descriptions>
          <div v-for="(r, i) in runResult.results" :key="i" style="margin-bottom: 8px;">
            <el-tag :type="r.passed ? 'success' : 'danger'" size="small">{{ r.name }}</el-tag>
            <span v-if="!r.passed" style="color: #f56c6c; font-size: 12px; margin-left: 5px;">{{ r.assertions?.filter((a: any) => !a.passed).map((a: any) => a.message).join('; ') }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑套件' : '新建套件'" width="600px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="suiteForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="suiteForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSuite">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/client'

const route = useRoute()
const projectId = Number(route.params.projectId)
const suites = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const suiteForm = reactive({ name: '', description: '' })
const runningId = ref<number | null>(null)
const runResult = ref<any>(null)

onMounted(() => loadSuites())

async function loadSuites() {
  suites.value = await http.get('/suites', { params: { project_id: projectId } })
}

function showCreateDialog() {
  editingId.value = null; suiteForm.name = ''; suiteForm.description = ''; dialogVisible.value = true
}

function editSuite(row: any) {
  editingId.value = row.id; suiteForm.name = row.name; suiteForm.description = row.description || ''; dialogVisible.value = true
}

function selectSuite(row: any) { runResult.value = null }

async function saveSuite() {
  if (editingId.value) {
    await http.put(`/suites/${editingId.value}`, { ...suiteForm, project_id: projectId })
  } else {
    await http.post('/suites', { ...suiteForm, project_id: projectId, steps: [] })
  }
  ElMessage.success('保存成功'); dialogVisible.value = false; await loadSuites()
}

async function runSuite(suite: any) {
  runningId.value = suite.id; runResult.value = null
  try { runResult.value = await http.post('/suites/run', { suite_id: suite.id, project_id: projectId }) }
  catch {} finally { runningId.value = null }
}

async function deleteSuite(id: number) {
  await ElMessageBox.confirm('确定删除？', '提示', { type: 'warning' })
  await http.delete(`/suites/${id}`); ElMessage.success('删除成功'); await loadSuites()
}
</script>