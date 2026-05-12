# POA — API Testing Platform

> 集成 Postman + Apifox 优点的开源 API 测试平台，无需安装插件，开箱即用。

## 快速启动

```bash
cd 阿里云/poa/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

访问 `http://localhost:8000/api/docs-ui` 查看交互式 API 文档。

---

## 功能全览

### 工作空间 & 项目管理
| 端点 | 说明 |
|------|------|
| `GET /api/workspaces` | 列出所有工作空间 |
| `POST /api/workspaces` | 创建工作空间 |
| `PUT /api/workspaces/{id}` | 更新工作空间 |
| `GET /api/workspaces/{id}` | 工作空间详情 |
| `DELETE /api/workspaces/{id}` | 删除工作空间 |
| `GET /api/projects` | 列出项目（支持 workspace_id 筛选）|
| `POST /api/projects` | 创建项目 |
| `PUT /api/projects/{id}` | 更新项目 |
| `GET /api/projects/{id}` | 项目详情 |
| `DELETE /api/projects/{id}` | 删除项目 |
| `GET /api/projects/{id}/tree` | 项目树形结构（集合+接口）|
| `GET /api/projects/{id}/stats` | 项目统计（接口数/通过率/请求量）|

### 集合 & 接口
| 端点 | 说明 |
|------|------|
| `GET /api/collections` | 列出集合 |
| `POST /api/collections` | 创建集合 |
| `PUT /api/collections/{id}` | 更新集合 |
| `DELETE /api/collections/{id}` | 删除集合 |
| `POST /api/collections/{id}/duplicate` | 复制集合（含所有接口）|
| `GET /api/apis` | 列出接口 |
| `POST /api/apis` | 创建接口 |
| `GET /api/apis/{id}` | 接口详情 |
| `PUT /api/apis/{id}` | 更新接口（自动记录变更快照）|
| `DELETE /api/apis/{id}` | 删除接口 |
| `POST /api/apis/{id}/duplicate` | 复制接口 |
| `POST /api/apis/{id}/move` | 移动接口到其他集合 |
| `GET /api/apis/{id}/changelog` | 接口变更记录 |

### 环境变量
| 端点 | 说明 |
|------|------|
| `GET /api/environments` | 列出环境 |
| `POST /api/environments` | 创建环境 |
| `POST /api/environments/import` | 导入环境（JSON 文件）|
| `PUT /api/environments/{id}` | 更新环境 |
| `DELETE /api/environments/{id}` | 删除环境 |
| `POST /api/environments/{id}/activate` | 激活环境 |
| `POST /api/environments/{id}/duplicate` | 复制环境 |
| `GET /api/environments/{id}/export` | 导出环境（JSON 文件下载）|
| `GET /api/global-variables` | 全局变量列表 |
| `POST /api/global-variables` | 创建全局变量 |
| `POST /api/global-variables/batch` | 批量 upsert 全局变量 |
| `PUT /api/global-variables/{id}` | 更新全局变量 |
| `DELETE /api/global-variables/{id}` | 删除全局变量 |

### 请求执行
| 端点 | 说明 |
|------|------|
| `POST /api/run` | 执行单个接口（支持 api_id 或直接传配置）|
| `GET /api/history` | 请求历史（支持 status_code 筛选 + 分页）|
| `DELETE /api/history/batch` | 批量删除历史 |
| `DELETE /api/history/{id}` | 删除单条历史 |
| `POST /api/history/{id}/replay` | 重放历史请求 |

### 测试套件
| 端点 | 说明 |
|------|------|
| `GET /api/suites` | 列出测试套件 |
| `POST /api/suites` | 创建套件 |
| `PUT /api/suites/{id}` | 更新套件 |
| `DELETE /api/suites/{id}` | 删除套件 |
| `POST /api/suites/run` | 执行套件（HTTP）|
| `WS /api/ws/run` | 执行套件（WebSocket 实时推送）|
| `GET /api/test-runs` | 测试运行记录列表 |
| `GET /api/test-runs/{id}` | 运行详情 |
| `GET /api/test-runs/{id}/report` | 生成 HTML 测试报告 |
| `DELETE /api/test-runs` | 批量清空运行记录 |

### Mock 服务
| 端点 | 说明 |
|------|------|
| `GET /api/mocks` | Mock 规则列表 |
| `POST /api/mocks` | 创建 Mock 规则 |
| `PUT /api/mocks/{id}` | 更新 Mock 规则 |
| `DELETE /api/mocks/{id}` | 删除 Mock 规则 |
| `ANY /api/mock/{project_id}/{path}` | Mock 请求处理（支持路径参数/通配符/延迟）|

### 导入导出
| 端点 | 说明 |
|------|------|
| `POST /api/import/postman` | 导入 Postman Collection v2.1 |
| `POST /api/import/apifox` | 导入 Apifox（原生格式 + OpenAPI）|
| `POST /api/import/openapi` | 导入 OpenAPI 2.0/3.0（JSON/YAML）|
| `GET /api/export/postman/{id}` | 导出为 Postman Collection |
| `GET /api/export/openapi/{id}` | 导出为 OpenAPI 3.0 |
| `GET /api/export/apifox/{id}` | 导出为 Apifox 兼容格式 |

### 扩展功能
| 端点 | 说明 |
|------|------|
| `GET /api/cookie-jars` | Cookie Jar 列表 |
| `POST/PUT/DELETE /api/cookie-jars/{id}` | Cookie Jar CRUD |
| `GET /api/certificates` | SSL 证书列表 |
| `POST/PUT/DELETE /api/certificates/{id}` | 证书 CRUD |
| `GET /api/scheduled-tasks` | 定时任务列表 |
| `POST/PUT/DELETE /api/scheduled-tasks/{id}` | 定时任务 CRUD |
| `POST /api/scheduled-tasks/{id}/trigger` | 手动触发任务 |
| `POST /api/scheduled-tasks/{id}/toggle` | 启用/禁用任务 |
| `GET /api/scheduled-tasks/{id}/history` | 任务执行历史 |
| `GET /api/docs` | API 文档列表 |
| `POST /api/docs/generate/{id}` | 生成 OpenAPI 文档（支持分享 token）|
| `GET /api/docs/share/{token}` | 访问公开文档 |
| `GET /api/team-members` | 团队成员列表 |
| `POST /api/team-members` | 添加成员 |
| `PUT /api/team-members/{id}/role` | 更新角色（owner/editor/viewer）|
| `DELETE /api/team-members/{id}` | 移除成员 |
| `GET /api/search` | 全局搜索接口 |

### 认证
| 端点 | 说明 |
|------|------|
| `POST /api/auth/register` | 注册 |
| `POST /api/auth/login` | 登录（返回 JWT）|
| `GET /api/auth/me` | 当前用户信息 |
| `POST /api/auth/logout` | 登出 |
| `POST /api/auth/api-keys` | 创建 API Key |
| `GET /api/auth/api-keys` | API Key 列表 |
| `DELETE /api/auth/api-keys/{id}` | 删除 API Key |
| `PUT /api/auth/password` | 修改密码 |

### 备份恢复
| 端点 | 说明 |
|------|------|
| `POST /api/backup/{project_id}` | 导出项目完整备份（JSON）|
| `POST /api/restore` | 恢复备份（支持 skip/overwrite 冲突策略）|

### 系统监控
| 端点 | 说明 |
|------|------|
| `GET /api/metrics` | 系统指标（DB大小/请求量/成功率/响应时间）|
| `GET /api/logs` | 系统日志（支持 level 筛选）|
| `GET /health` | 健康检查 |

---

## 执行引擎能力

### 变量渲染
支持 `{{var}}` 和 `${var}` 两种语法：
```yaml
url: "{{base_url}}/api/users/${user_id}"
```

### 内置函数
```
{{timestamp()}}    当前时间戳（秒）
{{timestamp_ms()}} 当前时间戳（毫秒）
{{uuid()}}         UUID hex
{{rand_str()}}     随机16位字符串
{{rand_str(8)}}    随机8位字符串
{{rand_int()}}     随机整数 0-9999
{{rand_int(1,100)}} 随机整数 1-100
{{fake.name()}}    随机中文姓名
{{fake.phone()}}   随机手机号
{{fake.email()}}   随机邮箱
{{fake.address()}} 随机地址
{{fake.company()}} 随机公司名
{{fake.id_card()}} 随机身份证号
```

### 断言类型
```
eq / ne / gt / lt / ge / le
contains / not_contains
exists / not_exists
regex
json_schema
len_eq / len_gt / len_lt
```

### 变量提取
```
status_code          响应状态码
headers.X-Token      响应头
$.data.token         JSONPath
body.data.token      JMESPath
re:pattern           正则表达式
```

### 前置/后置脚本
```javascript
// 前置脚本
poa.setVariable('token', 'xxx')
poa.getVariable('base_url')
poa.log('debug info')

// 后置脚本
const data = response.json
poa.setVariable('user_id', data.id)
```

---

## 数据模型

```
Workspace → Project → Collection → Api
                    → Environment
                    → TestSuite → TestRun
                    → MockRule
                    → GlobalVariable
                    → ScheduledTask
                    → ApiDoc
                    → CookieJar
                    → Certificate
```

---

## 启动参数

```bash
# 开发模式
uvicorn main:app --reload --port 8000

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 自定义 JWT 密钥
POA_SECRET=your-secret-key uvicorn main:app --port 8000
```
