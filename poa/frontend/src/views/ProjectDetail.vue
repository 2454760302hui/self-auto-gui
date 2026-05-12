<template>
  <el-container style="height: calc(100vh - 110px);">
    <!-- 左侧树 -->
    <el-aside width="280px" style="background: #fff; border-right: 1px solid #e6e6e6; overflow: auto; padding: 10px;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
        <strong>{{ project?.name }}</strong>
        <el-dropdown @command="handleTreeAction">
          <el-button size="small" type="primary"><el-icon><Plus /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="collection">新建文件夹</el-dropdown-item>
              <el-dropdown-item command="api">新建 API</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <el-tree :data="treeData" :props="{ label: 'name', children: 'children' }" default-expand-all highlight-current @node-click="handleNodeClick">
        <template #default="{ node, data }">
          <span class="tree-item">
            <span v-if="data.method" :class="`method-tag method-${data.method.toLowerCase()}`">{{ data.method }}</span>
            <span>{{ node.label }}</span>
          </span>
        </template>
      </el-tree>
    </el-aside>

    <!-- 右侧编辑区 -->
    <el-main style="padding: 15px; overflow: auto;">
      <div v-if="!selectedApi" style="text-align: center; color: #909399; padding-top: 100px;">
        <el-icon :size="60"><Document /></el-icon>
        <p style="margin-top: 15px;">选择或创建一个 API 开始测试</p>
      </div>

      <div v-else>
        <!-- URL 栏 -->
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
          <el-select v-model="apiForm.method" class="method-select">
            <el-option v-for="m in ['GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS']" :key="m" :label="m" :value="m" />
          </el-select>
          <el-input v-model="apiForm.url" placeholder="https://api.example.com/users" class="url-input" />
          <el-button type="primary" :loading="sending" @click="sendRequest">发送</el-button>
          <el-button @click="saveApi">保存</el-button>
        </div>

        <el-tabs v-model="activeTab">
          <!-- 请求体 -->
          <el-tab-pane label="Headers" name="headers">
            <el-table :data="headerRows" size="small">
              <el-table-column label="Key" width="250">
                <template #default="{ row }"><el-input v-model="row.key" size="small" /></template>
              </el-table-column>
              <el-table-column label="Value">
                <template #default="{ row }"><el-input v-model="row.value" size="small" /></template>
              </el-table-column>
              <el-table-column label="" width="60">
                <template #default="{ $index }"><el-button size="small" type="danger" @click="headerRows.splice($index, 1)"><el-icon><Delete /></el-icon></el-button></template>
              </el-table-column>
            </el-table>
            <el-button size="small" @click="headerRows.push({ key: '', value: '' })" style="margin-top: 5px;">+ 添加</el-button>
          </el-tab-pane>

          <el-tab-pane label="Params" name="params">
            <el-table :data="paramRows" size="small">
              <el-table-column label="Key" width="250">
                <template #default="{ row }"><el-input v-model="row.key" size="small" /></template>
              </el-table-column>
              <el-table-column label="Value">
                <template #default="{ row }"><el-input v-model="row.value" size="small" /></template>
              </el-table-column>
              <el-table-column label="" width="60">
                <template #default="{ $index }"><el-button size="small" type="danger" @click="paramRows.splice($index, 1)"><el-icon><Delete /></el-icon></el-button></template>
              </el-table-column>
            </el-table>
            <el-button size="small" @click="paramRows.push({ key: '', value: '' })" style="margin-top: 5px;">+ 添加</el-button>
          </el-tab-pane>

          <el-tab-pane label="Body" name="body">
            <el-radio-group v-model="apiForm.body_type" style="margin-bottom: 10px;">
              <el-radio-button value="none">none</el-radio-button>
              <el-radio-button value="json">JSON</el-radio-button>
              <el-radio-button value="form">Form</el-radio-button>
              <el-radio-button value="raw">Raw</el-radio-button>
            </el-radio-group>
            <el-input v-if="apiForm.body_type !== 'none'" v-model="apiForm.body" type="textarea" :rows="10" placeholder="请求体内容" />
          </el-tab-pane>

          <el-tab-pane label="前置脚本" name="pre_script">
            <el-input v-model="apiForm.pre_script" type="textarea" :rows="8" placeholder="poa.setVariable('key', value)" />
          </el-tab-pane>

          <el-tab-pane label="后置脚本" name="post_script">
            <el-input v-model="apiForm.post_script" type="textarea" :rows="8" placeholder="poa.setVariable('token', response['json']['token'])" />
          </el-tab-pane>

          <el-tab-pane label="断言" name="assertions">
            <div v-for="(a, i) in assertionRows" :key="i" style="display: flex; gap: 5px; margin-bottom: 5px;">
              <el-select v-model="a.source" style="width: 120px;" size="small">
                <el-option label="Body" value="body" /><el-option label="Status" value="status" /><el-option label="Header" value="header" />
              </el-select>
              <el-input v-model="a.path" placeholder="path" style="width: 200px;" size="small" />
              <el-select v-model="a.type" style="width: 120px;" size="small">
                <el-option label="等于" value="eq" /><el-option label="不等于" value="ne" /><el-option label="包含" value="contains" /><el-option label="存在" value="exists" />
              </el-select>
              <el-input v-model="a.expected" placeholder="期望值" style="flex: 1;" size="small" />
              <el-button size="small" type="danger" @click="assertionRows.splice(i, 1)"><el-icon><Delete /></el-icon></el-button>
            </div>
            <el-button size="small" @click="assertionRows.push({ source: 'body', path: '', type: 'eq', expected: '' })">+ 添加断言</el-button>
          </el-tab-pane>
        </el-tabs>

        <!-- 响应区 -->
        <el-divider />
        <div v-if="response" class="card-section">
          <div style="display: flex; gap: 15px; margin-bottom: 10px; align-items: center;">
            <el-tag :type="response.status_code < 300 ? 'success' : response.status_code < 400 ? 'warning' : 'danger'" size="large">{{ response.status_code }}</el-tag>
            <span>{{ response.elapsed_ms }}ms</span>
            <span>{{ response.size }} bytes</span>
            <el-tag v-if="runResult" :type="runResult.passed ? 'success' : 'danger'">{{ runResult.passed ? '断言通过' : '断言失败' }}</el-tag>
          </div>
          <el-tabs>
            <el-tab-pane label="Body">
              <pre>{{ formatJson(response.json || response.text) }}</pre>
            </el-tab-pane>
            <el-tab-pane label="Headers">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item v-for="(v, k) in response.headers" :key="k" :label="k">{{ v }}</el-descriptions-item>
              </el-descriptions>
            </el-tab-pane>
            <el-tab-pane label="断言结果" v-if="runResult?.assertions?.length">
              <el-table :data="runResult.assertions" size="small">
                <el-table-column label="状态" width="80"><template #default="{ row }"><el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '失败' }}</el-tag></template></el-table-column>
                <el-table-column label="类型" prop="type" width="100" />
                <el-table-column label="路径" prop="path" />
                <el-table-column label="期望" prop="expected" />
                <el-table-column label="实际" prop="actual" />
                <el-table-column label="信息" prop="message" />
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </el-main>

    <!-- 新建文件夹对话框 -->
    <el-dialog v-model="colDialogVisible" title="新建文件夹" width="400px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="colName" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="colDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createCollection">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新建 API 对话框 -->
    <el-dialog v-model="apiDialogVisible" title="新建 API" width="400px">
      <el-form label-width="80px">
        <el-form-item label="文件夹"><el-select v-model="newApiColId"><el-option v-for="c in store.collections" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item label="名称"><el-input v-model="newApiName" /></el-form-item>
        <el-form-item label="方法"><el-select v-model="newApiMethod"><el-option v-for="m in ['GET','POST','PUT','DELETE','PATCH']" :key="m" :label="m" :value="m" /></el-select></el-form-item>
        <el-form-item label="路径"><el-input v-model="newApiPath" placeholder="/api/users" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="apiDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createNewApi">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useWorkspaceStore } from '../stores/workspace'
import http from '../api/client'

const route = useRoute()
const store = useWorkspaceStore()
const projectId = computed(() => Number(route.params.id))
const project = ref<any>(null)
const treeData = ref<any[]>([])
const selectedApi = ref<any>(null)
const activeTab = ref('headers')
const sending = ref(false)
const response = ref<any>(null)
const runResult = ref<any>(null)

const apiForm = reactive({ method: 'GET', url: '', body_type: 'none', body: '', pre_script: '', post_script: '' })
const headerRows = ref<{ key: string; value: string }[]>([])
const paramRows = ref<{ key: string; value: string }[]>([])
const assertionRows = ref<any[]>([])

const colDialogVisible = ref(false)
const colName = ref('')
const apiDialogVisible = ref(false)
const newApiColId = ref<number>(0)
const newApiName = ref('')
const newApiMethod = ref('GET')
const newApiPath = ref('')

onMounted(async () => {
  try { project.value = await http.get(`/projects/${projectId.value}`) } catch {}
  await loadTree()
})

async function loadTree() {
  try {
    const tree = await http.get(`/projects/${projectId.value}/tree`)
    treeData.value = Array.isArray(tree) ? tree : []
  } catch {}
}

function handleNodeClick(data: any) {
  if (data.method) {
    selectedApi.value = data
    apiForm.method = data.method
    apiForm.url = (project.value?.base_url || '') + (data.path || '')
    apiForm.body_type = data.body_type || 'none'
    apiForm.body = typeof data.body === 'string' ? data.body : JSON.stringify(data.body || '', null, 2)
    apiForm.pre_script = data.pre_script || ''
    apiForm.post_script = data.post_script || ''
    headerRows.value = parseKvPairs(data.headers)
    paramRows.value = parseKvPairs(data.params)
    assertionRows.value = Array.isArray(data.assertions) ? data.assertions : []
    response.value = null
    runResult.value = null
  }
}

function parseKvPairs(raw: any) {
  if (Array.isArray(raw)) return raw.map((h: any) => ({ key: h.key || '', value: h.value || '' }))
  if (typeof raw === 'object' && raw) return Object.entries(raw).map(([key, value]) => ({ key, value: String(value) }))
  return []
}

async function sendRequest() {
  if (!selectedApi.value) return
  sending.value = true
  try {
    runResult.value = await http.post('/run', {
      api_id: selectedApi.value.id,
      method: apiForm.method,
      url: apiForm.url,
      headers: headerRows.value.filter(h => h.key),
      params: paramRows.value.filter(p => p.key),
      body_type: apiForm.body_type,
      body: apiForm.body,
      pre_script: apiForm.pre_script,
      post_script: apiForm.post_script,
      assertions: assertionRows.value,
      project_id: projectId.value,
    })
    response.value = runResult.value.response
  } catch {}
  sending.value = false
}

async function saveApi() {
  if (!selectedApi.value) return
  try {
    await http.put(`/apis/${selectedApi.value.id}`, {
      method: apiForm.method,
      path: apiForm.url.replace(project.value?.base_url || '', ''),
      headers: headerRows.value, params: paramRows.value,
      body_type: apiForm.body_type, body: apiForm.body,
      pre_script: apiForm.pre_script, post_script: apiForm.post_script,
      assertions: assertionRows.value,
    })
    ElMessage.success('保存成功')
  } catch {}
}

function handleTreeAction(cmd: string) {
  if (cmd === 'collection') colDialogVisible.value = true
  if (cmd === 'api') {
    if (store.collections.length === 0) { ElMessage.warning('请先创建文件夹'); return }
    newApiColId.value = store.collections[0]?.id || 0
    apiDialogVisible.value = true
  }
}

async function createCollection() {
  if (!colName.value) return
  await store.createCollection({ project_id: projectId.value, name: colName.value })
  ElMessage.success('创建成功')
  colDialogVisible.value = false; colName.value = ''
  await loadTree()
}

async function createNewApi() {
  if (!newApiName.value || !newApiColId.value) return
  await store.createApi({ collection_id: newApiColId.value, name: newApiName.value, method: newApiMethod.value, path: newApiPath.value })
  ElMessage.success('创建成功')
  apiDialogVisible.value = false
  await loadTree()
}

function formatJson(data: any) {
  if (typeof data === 'string') return data
  try { return JSON.stringify(data, null, 2) } catch { return String(data) }
}
</script>