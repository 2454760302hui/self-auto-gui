import axios from 'redaxios';

export interface BrowserLLMConfig {
  configured: boolean;
  status: string;
  model: string;
  provider: string;
  raw_config: string;
}

export interface BrowserTaskResult {
  task_id: string;
  mode: string;
  success: boolean;
  elapsed_ms: number;
  dsl?: string;
  log?: string;
  stdout?: string;
  stderr?: string;
  steps?: number;
  final_result?: string;
  errors?: string[];
  gif_url?: string;
  has_gif?: boolean;
  error?: string;
}

export interface BrowserTrace {
  task_id: string;
  mode: string;
  success: boolean;
  steps: number;
  elapsed_ms: number;
  task: string;
  has_gif: boolean;
}

export interface BrowserDSDDemo {
  name: string;
  script: string;
}

export interface BrowserHealth {
  status: string;
  llm: { status: string; model: string };
  cdp_url: string;
}

// ============ Browser Use API Client ============
// 优先使用统一服务端口，否则回退到独立服务端口
const BASE_URL = typeof window !== 'undefined' && window.location.port === '8000'
  ? `${window.location.protocol}//${window.location.hostname}:9242`
  : 'http://127.0.0.1:9242';

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function getBrowserHealth(): Promise<{ success: boolean; data: BrowserHealth }> {
  return apiRequest('/health');
}

export async function getBrowserLLMStatus(): Promise<{ success: boolean; data: BrowserLLMConfig }> {
  return apiRequest('/llm-status');
}

export async function testBrowserLLM(config: string): Promise<{ success: boolean; data?: { status_text: string }; error?: string }> {
  return apiRequest('/test-llm', {
    method: 'POST',
    body: JSON.stringify({ config }),
  });
}

export async function runBrowserTask(params: {
  task: string;
  mode: 'llm' | 'dsl' | 'nlp';
  max_steps?: number;
  dsl?: string;
  cdp_url?: string;
  task_id?: string;
}): Promise<{ success: boolean; data: BrowserTaskResult; error?: string }> {
  return apiRequest('/run-task', {
    method: 'POST',
    body: JSON.stringify({
      task: params.task,
      mode: params.mode,
      max_steps: params.max_steps ?? 20,
      dsl: params.dsl ?? '',
      cdp_url: params.cdp_url ?? '',
      task_id: params.task_id ?? '',
    }),
  });
}

export async function runBrowserPlaywright(script: string, taskId?: string): Promise<{
  success: boolean;
  data: {
    task_id: string;
    success: boolean;
    elapsed_ms: number;
    stdout: string;
    stderr: string;
    gif_url?: string;
    has_gif?: boolean;
  };
}> {
  return apiRequest('/run-playwright', {
    method: 'POST',
    body: JSON.stringify({ script, task_id: taskId ?? '' }),
  });
}

export async function listBrowserTraces(): Promise<{ success: boolean; runs: BrowserTrace[] }> {
  return apiRequest('/traces');
}

export async function getBrowserTrace(taskId: string): Promise<BrowserTaskResult> {
  return apiRequest(`/traces/${taskId}/trace.json`);
}

export async function getBrowserTraceFile(taskId: string, filename: string): Promise<string> {
  const url = `${BASE_URL}/traces/${taskId}/${filename}`;
  const response = await fetch(url);
  return response.text();
}

export async function getBrowserDemos(): Promise<{ success: boolean; demos: Record<string, string> }> {
  return apiRequest('/dsl-demos');
}

export async function exportBrowserDSL(dsl: string, format: 'yaml' | 'pytest'): Promise<{ success: boolean; content: string; error?: string }> {
  return apiRequest('/export', {
    method: 'POST',
    body: JSON.stringify({ dsl, format }),
  });
}

export async function clearBrowserTraces(): Promise<{ success: boolean; cleared: number }> {
  return apiRequest('/traces', { method: 'DELETE' });
}

export async function getBrowserNLPStatus(): Promise<{ success: boolean; data: { available: boolean; status: string; features: string[] } }> {
  return apiRequest('/nlp/status');
}

export async function analyzeBrowserNLP(text: string): Promise<{
  success: boolean;
  data?: {
    original_text: string;
    dsl_output: string;
    primary_intent: string;
    confidence: number;
    entities: unknown[];
    commands: unknown[];
    warnings: string[];
    processing_time_ms: number;
  };
  error?: string;
}> {
  return apiRequest('/nlp/analyze', {
    method: 'POST',
    body: JSON.stringify({ text, use_llm: false }),
  });
}

export async function convertBrowserNLPToDSL(text: string): Promise<{ success: boolean; data?: { dsl: string }; error?: string }> {
  return apiRequest('/nlp/to-dsl', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}
