<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
      <h3>环境变量管理</h3>
      <el-button type="primary" @click="showCreateDialog"><el-icon><Plus /></el-icon> 新建环境</el-button>
    </div>

    <el-table :data="environments" stripe>
      <el-table-column prop="name" label="环境名称" width="200" />
      <el-table-column label="变量数量" width="120">
        <template #default="{ row }">{{ row.variables ? Object.keys(row.variables).length : 0 }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '激活' : '未激活' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button size="small" @click="editEnv(row)">编辑</el-button>
          <el-button size="small" :type="row.is_active ? 'warning' : 'success'" @click="toggleActive(row)">
            {{ row.is_active ? '取消激活' : '激活' }}
          </el-button>
          <el-button size="small" type="danger" @click="deleteEnv(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑环境' : '新建环境'" width="600px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="envForm.name" /></el-form-item>
        <el-form-item label="变量">
          <div v-for="(v, i) in varRows" :key="i" style="display: flex; gap: 5px; margin-bottom: 5px;">
            <el-input v-model="v.key" placeholder="Key" style="width: 200px;" />
            <el-input v-model="v.value" placeholder="Value" />
            <el-button size="small" type="danger" @click="varRows.splice(i, 1)"><el-icon><Delete /></el-icon></el-button>
          </div>
          <el-button size="small" @click="varRows.push({ key: '', value: '' })">+ 添加变量</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEnv">保存</el-button>
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
const environments = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const envForm = reactive({ name: '' })
const varRows = ref<{ key: string; value: string }[]>([])

onMounted(() => loadEnvs())

async function loadEnvs() {
  environments.value = await http.get('/environments', { params: { project_id: projectId } })
}

function showCreateDialog() {
  editingId.value = null
  envForm.name = ''
  varRows.value = [{ key: '', value: '' }]
  dialogVisible.value = true
}

function editEnv(row: any) {
  editingId.value = row.id
  envForm.name = row.name
  varRows.value = row.variables ? Object.entries(row.variables).map(([key, value]) => ({ key, value: String(value) })) : []
  dialogVisible.value = true
}

async function saveEnv() {
  const vars: any = {}
  varRows.value.filter(v => v.key).forEach(v => { vars[v.key] = v.value })
  if (editingId.value) {
    await http.put(`/environments/${editingId.value}`, { name: envForm.name, variables: vars })
  } else {
    await http.post('/environments', { project_id: projectId, name: envForm.name, variables: vars })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  await loadEnvs()
}

async function toggleActive(row: any) {
  await http.post(`/environments/${row.id}/activate`)
  ElMessage.success('操作成功')
  await loadEnvs()
}

async function deleteEnv(id: number) {
  await ElMessageBox.confirm('确定删除该环境？', '提示', { type: 'warning' })
  await http.delete(`/environments/${id}`)
  ElMessage.success('删除成功')
  await loadEnvs()
}
</script>