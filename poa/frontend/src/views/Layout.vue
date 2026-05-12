<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div style="padding: 15px; color: #fff; font-size: 18px; font-weight: bold; text-align: center;">POA</div>
      <el-menu background-color="#304156" text-color="#bfcbd9" active-text-color="#409EFF" :default-active="$route.path" router>
        <el-menu-item index="/home"><el-icon><HomeFilled /></el-icon><span>工作台</span></el-menu-item>
        <el-menu-item v-for="ws in store.workspaces" :key="ws.id" :index="`/home?ws=${ws.id}`">
          <el-icon><Folder /></el-icon><span>{{ ws.name }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="main-header" height="50px">
        <h2>{{ currentTitle }}</h2>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="color: #606266; font-size: 14px;">{{ auth.user?.username }}</span>
          <el-dropdown @command="handleCommand">
            <el-button circle size="small"><el-icon><User /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const store = useWorkspaceStore()

const currentTitle = computed(() => (route.name as string) || 'POA')

onMounted(async () => {
  await auth.fetchMe()
  await store.loadWorkspaces()
})

function handleCommand(cmd: string) {
  if (cmd === 'logout') { auth.logout(); router.push('/login') }
}
</script>