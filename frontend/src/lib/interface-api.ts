import axios from 'redaxios';

export interface APITestConfig {
  env: string;
  base_url: string;
  proxies_ip?: string;
}

export interface APITestStep {
  name?: string;
  request: {
    method: string;
    url: string;
    params?: Record<string, unknown>;
    data?: unknown;
    headers?: Record<string, string>;
  };
  extract?: Array<{
    name: string;
    from: 'body' | 'headers' | 'cookies' | 'status_code' | 'response_time';
    expression: string;
  }>;
  validate?: Array<{
    name: string;
    assert: string;
    expect: unknown;
    actual?: unknown;
  }>;
  export?: string[];
}

export interface APITestCase {
  name: string;
  description?: string;
  config: APITestConfig;
  teststeps: APITestStep[];
}

export interface APITestRunResult {
  success: boolean;
  output?: string;
  error?: string;
}

export interface APIEnvConfig {
  name: string;
  base_url: string;
  description?: string;
}

// ============ Interface Module API Client ============
// 优先使用统一服务端口，否则回退到独立服务端口
const INTERFACE_BASE = typeof window !== 'undefined' && window.location.port === '8000'
  ? `${window.location.protocol}//${window.location.hostname}:9243`
  : 'http://127.0.0.1:9243';

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${INTERFACE_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function runInterfaceTest(yamlContent: string, env?: string): Promise<APITestRunResult> {
  return apiRequest<APITestRunResult>('/run', {
    method: 'POST',
    body: JSON.stringify({ yaml: yamlContent, env: env ?? 'aliyun' }),
  });
}

export async function getInterfaceEnvs(): Promise<{ envs: APIEnvConfig[] }> {
  return apiRequest('/envs');
}

export async function testInterfaceEndpoint(method: string, url: string, data?: unknown): Promise<{
  success: boolean;
  status_code?: number;
  response_time_ms?: number;
  body?: unknown;
  error?: string;
}> {
  return apiRequest('/test-endpoint', {
    method: 'POST',
    body: JSON.stringify({ method, url, data }),
  });
}

export async function parseInterfaceYAML(yamlContent: string): Promise<{
  success: boolean;
  test_case?: APITestCase;
  error?: string;
}> {
  return apiRequest('/parse-yaml', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export const PRESET_TEST_TEMPLATES: Array<{ name: string; description: string; yaml: string }> = [
  {
    name: 'HTTP GET 请求',
    description: '最简单的 GET 请求测试',
    yaml: `config:
  base_url: https://httpbin.org
  env: aliyun

teststeps:
  - name: GET请求
    request:
      method: GET
      url: /get
    validate:
      - assert: status_code
        expect: 200
    export:
      - content`,
  },
  {
    name: 'HTTP POST 表单',
    description: 'POST 提交表单数据',
    yaml: `config:
  base_url: https://httpbin.org
  env: aliyun

teststeps:
  - name: POST表单
    request:
      method: POST
      url: /post
      data:
        username: test_user
        password: test_pass
    validate:
      - assert: status_code
        expect: 200
      - assert: body.json.args
        expect: {}`,
  },
  {
    name: 'HTTP POST JSON',
    description: 'POST 提交 JSON 数据',
    yaml: `config:
  base_url: https://httpbin.org
  env: aliyun

teststeps:
  - name: POST JSON
    request:
      method: POST
      url: /post
      headers:
        Content-Type: application/json
      data:
        name: nextagent
        type: automation
    validate:
      - assert: status_code
        expect: 200
      - assert: body.json.data
        expect: "{\\"name\\":\\"nextagent\\",\\"type\\":\\"automation\\"}"`,
  },
  {
    name: '获取响应数据',
    description: '提取响应中的数据并验证',
    yaml: `config:
  base_url: https://httpbin.org
  env: aliyun

teststeps:
  - name: 获取数据
    request:
      method: GET
      url: /json
    extract:
      - name: title
        from: body
        expression: $.slideshow.title
    validate:
      - assert: status_code
        expect: 200
      - assert: content.title
        expect: "Wake Up to WonderWidgets!"`,
  },
  {
    name: '设置请求头',
    description: '携带自定义 Header 发送请求',
    yaml: `config:
  base_url: https://httpbin.org
  env: aliyun

teststeps:
  - name: 自定义Header
    request:
      method: GET
      url: /headers
      headers:
        X-API-Key: next-agent-key
        X-Platform: nextagent
    validate:
      - assert: status_code
        expect: 200
      - assert: body.headers["X-Api-Key"]
        expect: "nexus-agent-key"`,
  },
  {
    name: '连续请求 (提取变量)',
    description: '从第一个请求提取数据传给第二个',
    yaml: `config:
  base_url: https://httpbin.org
  env: aliyun

teststeps:
  - name: 第一个请求
    request:
      method: GET
      url: /uuid
    extract:
      - name: uuid_value
        from: body
        expression: $.uuid
  - name: 第二个请求
    request:
      method: GET
      url: /anything
      headers:
        X-Request-ID: $uuid_value
    validate:
      - assert: status_code
        expect: 200`,
  },
];
