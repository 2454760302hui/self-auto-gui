import axios, { AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

// 类型别名：拦截器将 AxiosResponse 转换为 data
type HttpInstance = Omit<typeof axios, 'get' | 'post' | 'put' | 'delete' | 'patch'> & {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
}

const http = axios.create({ baseURL: '/api', timeout: 30000 }) as unknown as HttpInstance

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('poa_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res: AxiosResponse) => res.data,
  (err: { response?: { status?: number; data?: { message?: string; detail?: string } }; message?: string }) => {
    const msg = err.response?.data?.message || err.response?.data?.detail || err.message || '请求失败'
    if (err.response?.status === 401) {
      localStorage.removeItem('poa_token')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  }
)

export default http