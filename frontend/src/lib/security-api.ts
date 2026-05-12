import axios from 'redaxios';

export interface SecurityVuln {
  id: string;
  name: string;
  target: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  vuln_type: string;
  url: string;
  detail: string;
  payload?: string;
  timestamp: string;
}

export interface SecurityScanResult {
  success: boolean;
  task_id: string;
  elapsed_ms: number;
  target_url: string;
  scan_type: string;
  vuln_count: number;
  vulns: SecurityVuln[];
  stdout?: string;
  stderr?: string;
  error?: string;
}

export interface SecurityScanSummary {
  task_id: string;
  target_url: string;
  scan_type: string;
  severity_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  total: number;
  scanned_at: string;
  duration_ms: number;
}

// ============ Security Module API Client ============

const SECURITY_BASE = 'http://127.0.0.1:9244';

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${SECURITY_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Security API error: ${response.status}`);
  }
  return response.json();
}

export async function startSecurityScan(params: {
  target_url: string;
  scan_type: 'quick' | 'full' | 'xss' | 'sqli' | 'cmd';
  enable_auth?: boolean;
  auth_username?: string;
  auth_password?: string;
}): Promise<{ success: boolean; task_id: string; message?: string; error?: string }> {
  return apiRequest('/scan', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getSecurityScanStatus(taskId: string): Promise<{
  success: boolean;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  vulns_found: number;
  message?: string;
  error?: string;
}> {
  return apiRequest(`/scan/${taskId}/status`);
}

export async function getSecurityScanResult(taskId: string): Promise<SecurityScanResult> {
  return apiRequest(`/scan/${taskId}/result`);
}

export async function listSecurityScans(): Promise<{
  success: boolean;
  scans: SecurityScanSummary[];
}> {
  return apiRequest('/scans');
}

export async function deleteSecurityScan(taskId: string): Promise<{ success: boolean }> {
  return apiRequest(`/scan/${taskId}`, { method: 'DELETE' });
}

export async function exportSecurityReport(taskId: string, format: 'json' | 'html'): Promise<{
  success: boolean;
  report_content?: string;
  report_url?: string;
  error?: string;
}> {
  return apiRequest(`/scan/${taskId}/export?format=${format}`, {
    method: 'GET',
  });
}

export async function testSecurityEndpoint(url: string): Promise<{
  success: boolean;
  status_code?: number;
  response_time_ms?: number;
  headers?: Record<string, string>;
  server?: string;
  powered_by?: string;
  error?: string;
}> {
  return apiRequest('/test-endpoint', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

export const SCAN_TYPE_OPTIONS = [
  { value: 'quick', label: '快速扫描', description: 'SQL注入、XSS基础检测，2-5分钟' },
  { value: 'full', label: '全面扫描', description: '全插件覆盖，包含SQL/XSS/XXE/Cmd注入等，10-30分钟' },
  { value: 'xss', label: 'XSS 专项', description: '仅检测跨站脚本漏洞，3-8分钟' },
  { value: 'sqli', label: 'SQL注入专项', description: '仅检测SQL注入漏洞，5-15分钟' },
  { value: 'cmd', label: '命令注入专项', description: '仅检测命令注入漏洞，2-5分钟' },
];

export const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  info: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};
