import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '../api/client'
import type { Workspace, Project, Collection, ApiItem } from '../api/types'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspaces = ref<Workspace[]>([])
  const projects = ref<Project[]>([])
  const collections = ref<Collection[]>([])
  const apis = ref<ApiItem[]>([])

  async function loadWorkspaces() {
    workspaces.value = await http.get<Workspace[]>('/workspaces') as Workspace[]
  }
  async function createWorkspace(data: { name: string; description?: string }) {
    const ws = await http.post<Workspace>('/workspaces', data) as Workspace
    workspaces.value.push(ws)
    return ws
  }

  async function loadProjects(workspaceId?: number) {
    const params: any = {}
    if (workspaceId) params.workspace_id = workspaceId
    projects.value = await http.get<Project[]>('/projects', { params }) as Project[]
  }
  async function createProject(data: { workspace_id: number; name: string; description?: string; base_url?: string }) {
    const p = await http.post<Project>('/projects', data) as Project
    projects.value.push(p)
    return p
  }

  async function loadCollections(projectId: number) {
    collections.value = await http.get<Collection[]>('/collections', { params: { project_id: projectId } }) as Collection[]
  }
  async function createCollection(data: { project_id: number; parent_id?: number; name: string }) {
    const c = await http.post<Collection>('/collections', data) as Collection
    collections.value.push(c)
    return c
  }

  async function loadApis(collectionId: number) {
    apis.value = await http.get<ApiItem[]>('/apis', { params: { collection_id: collectionId } }) as ApiItem[]
  }
  async function createApi(data: any) {
    return await http.post('/apis', data)
  }
  async function updateApi(id: number, data: any) {
    return await http.put(`/apis/${id}`, data)
  }
  async function deleteApi(id: number) {
    await http.delete(`/apis/${id}`)
    apis.value = apis.value.filter(a => a.id !== id)
  }

  async function getProjectTree(projectId: number) {
    return await http.get(`/projects/${projectId}/tree`)
  }

  return {
    workspaces, projects, collections, apis,
    loadWorkspaces, createWorkspace,
    loadProjects, createProject,
    loadCollections, createCollection,
    loadApis, createApi, updateApi, deleteApi,
    getProjectTree,
  }
})