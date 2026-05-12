export interface Workspace {
  id: number; name: string; description?: string; created_at: string; updated_at: string
}
export interface Project {
  id: number; workspace_id: number; name: string; description?: string; base_url?: string; created_at: string; updated_at: string
}
export interface Collection {
  id: number; project_id: number; parent_id?: number; name: string; description?: string; sort_order: number; created_at: string
}
export interface ApiItem {
  id: number; collection_id: number; name: string; method: string; path: string; description?: string
  headers?: any; params?: any; body_type?: string; body?: any
  pre_script?: string; post_script?: string; assertions?: any[]; extractions?: any[]
  tags?: string[]; status?: string; created_at: string; updated_at: string
}
export interface Environment {
  id: number; project_id: number; name: string; variables: any; is_active: boolean; created_at: string
}
export interface TestSuite {
  id: number; project_id: number; name: string; description?: string; steps: any[]; created_at: string
}
export interface TestRunResult {
  total: number; passed: number; failed: number; duration: number; status: string; results: any[]
}
export interface RunResponse {
  request: any; response: any; assertions: any[]; extracted: any; passed: boolean; variables: any
}
export interface User { id: number; username: string; email: string; role: string }