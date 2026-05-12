<template>
  <div class="landing">
    <!-- 导航栏 -->
    <header class="navbar">
      <div class="nav-inner">
        <div class="logo">POA</div>
        <nav>
          <a href="#features">功能特性</a>
          <a href="#modules">支持模块</a>
          <a href="#docs">API 文档</a>
        </nav>
        <div class="nav-actions">
          <el-button @click="$router.push('/login')">登录</el-button>
          <el-button type="primary" @click="$router.push('/register')">立即体验</el-button>
        </div>
      </div>
    </header>

    <!-- 英雄区 -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">POA - API 测试平台</h1>
        <p class="hero-sub">集成 Postman + Apifox 优点的全功能 API 测试平台。支持接口管理、环境变量、自动化测试、Mock 服务、数据备份与恢复。</p>
        <div class="hero-btns">
          <el-button type="primary" size="large" @click="$router.push('/register')">立即体验</el-button>
          <el-button size="large" @click="scrollTo('modules')">了解更多</el-button>
        </div>
      </div>
    </section>

    <!-- 功能特性 -->
    <section id="features" class="features">
      <h2 class="section-title">核心功能</h2>
      <div class="feature-grid">
        <div class="feature-card">
          <div class="feature-icon">&#128196;</div>
          <h3>接口管理</h3>
          <p>树形结构管理项目/集合/API，支持导入 Postman/Apifox 数据</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">&#9889;</div>
          <h3>快速执行</h3>
          <p>一键发送请求，支持预/后置脚本、变量替换、断点调试</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">&#128202;</div>
          <h3>测试套件</h3>
          <p>批量执行 API 测试，支持断言、变量提取、报告生成</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">&#127870;</div>
          <h3>Mock 服务</h3>
          <p>本地 Mock Server，无需等待后端即可调试接口</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">&#128273;</div>
          <h3>环境管理</h3>
          <p>多环境切换，环境变量加密存储，安全可靠</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">&#128230;</div>
          <h3>数据备份</h3>
          <p>一键导出/导入项目数据，跨环境迁移无缝衔接</p>
        </div>
      </div>
    </section>

    <!-- 支持模块 -->
    <section id="modules" class="modules">
      <h2 class="section-title">支持的测试模块</h2>
      <p class="section-desc">POA 平台支持 5 大测试模块，覆盖 UI、接口、安全、移动端全场景</p>
      <div class="module-grid">
        <div class="module-card" v-for="mod in modules" :key="mod.name">
          <div class="module-icon">{{ mod.icon }}</div>
          <div class="module-info">
            <h3>{{ mod.name }}</h3>
            <p>{{ mod.desc }}</p>
            <div class="module-tags">
              <span v-for="tag in mod.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>
          <el-tooltip :content="mod.tooltip" placement="top">
            <span class="module-help">?</span>
          </el-tooltip>
        </div>
      </div>
    </section>

    <!-- API 文档 -->
    <section id="docs" class="docs-section">
      <div class="docs-inner">
        <h2 class="section-title">完整 API 文档</h2>
        <p class="section-desc">提供完整的 REST API，可二次开发或与 CI/CD 集成</p>
        <div class="docs-grid">
          <div class="doc-item">
            <h4>认证接口</h4>
            <code>POST /api/auth/login</code>
            <code>POST /api/auth/register</code>
            <code>GET  /api/auth/me</code>
          </div>
          <div class="doc-item">
            <h4>项目管理</h4>
            <code>GET    /api/workspaces</code>
            <code>POST   /api/projects</code>
            <code>GET    /api/projects/{id}/tree</code>
          </div>
          <div class="doc-item">
            <h4>接口执行</h4>
            <code>POST /api/run</code>
            <code>POST /api/suites/run</code>
            <code>GET  /api/history</code>
          </div>
          <div class="doc-item">
            <h4>数据管理</h4>
            <code>GET  /api/environments</code>
            <code>POST /api/global-variables</code>
            <code>POST /api/backup/{id}</code>
          </div>
        </div>
        <el-button type="primary" size="large" @click="openDocs">查看完整文档</el-button>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <p>POA API Testing Platform &copy; 2024-2026 | <a href="/api/docs-ui" target="_blank">API 文档</a></p>
    </footer>
  </div>
</template>

<script setup lang="ts">
const modules = [
  {
    name: 'DSL',
    icon: '💱',
    desc: 'UI 自动化测试框架，支持 Web 自动化操作录制与回放',
    tags: ['Web UI', '录制回放', '元素定位'],
    tooltip: 'DSL (Domain Specific Language) UI自动化框架，支持浏览器录制回放、元素智能定位、变量替换、批量执行。适用于 Web 页面功能测试、回归测试。',
  },
  {
    name: 'Interface',
    icon: '📜',
    desc: 'HTTP 接口自动化测试框架，支持参数化、数据驱动',
    tags: ['REST API', '参数化', '数据驱动'],
    tooltip: 'Interface 接口自动化测试框架，支持 HTTP/WebSocket/Dubbo 协议，参数化变量、环境切换、数据驱动、断言验证。适用于 API 回归测试、接口监控。',
  },
  {
    name: 'POA',
    icon: '🏢',
    desc: 'POA 自研 API 测试平台，集成项目管理、测试套件、Mock 服务',
    tags: ['API 平台', 'Mock', '协作'],
    tooltip: 'POA (Platform of API) 是自研 API 测试平台，提供项目管理、集合管理、API 编辑执行、测试套件、Mock 服务、数据导入导出等功能。支持团队协作。',
  },
  {
    name: 'Security',
    icon: '🔒',
    desc: '安全扫描框架，支持漏洞检测与报告生成',
    tags: ['漏洞扫描', 'Xray', '安全审计'],
    tooltip: 'Security 安全扫描框架，支持 Xray/AWVS/Nessus 等主流扫描器集成，自动漏洞检测、报告生成、风险评级。适用于 Web 安全测试、渗透测试。',
  },
  {
    name: 'Mobile',
    icon: '📱',
    desc: '移动端自动化测试框架，支持 Android/iOS/鸿蒙',
    tags: ['App 测试', '多平台', '图像识别'],
    tooltip: 'Mobile 移动端自动化测试框架，支持 Android/iOS/鸿蒙三大平台，元素定位、图像识别、触屏操作、性能监控。适用于 App 功能测试、兼容性测试。',
  },
]

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

function openDocs() {
  window.open('/api/docs-ui', '_blank')
}
</script>

<style scoped>
.landing { min-height: 100vh; background: #f5f7fa; }

/* 导航栏 */
.navbar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.nav-inner {
  max-width: 1200px; margin: 0 auto; padding: 0 24px;
  height: 60px; display: flex; align-items: center; gap: 40px;
}
.logo { font-size: 24px; font-weight: 800; color: #409EFF; letter-spacing: 2px; }
nav { flex: 1; display: flex; gap: 24px; }
nav a { color: #606266; text-decoration: none; font-size: 15px; }
nav a:hover { color: #409EFF; }
.nav-actions { display: flex; gap: 12px; }

/* 英雄区 */
.hero {
  padding: 140px 24px 100px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff; text-align: center;
}
.hero-content { max-width: 700px; margin: 0 auto; }
.hero-title { font-size: 48px; font-weight: 800; margin: 0 0 20px; letter-spacing: 2px; }
.hero-sub { font-size: 18px; line-height: 1.7; opacity: 0.9; margin: 0 0 40px; }
.hero-btns { display: flex; gap: 16px; justify-content: center; }

/* 通用区块 */
.section-title { font-size: 32px; font-weight: 700; text-align: center; margin: 0 0 16px; color: #303133; }
.section-desc { font-size: 16px; color: #909399; text-align: center; margin: 0 0 48px; }

/* 功能特性 */
.features { padding: 80px 24px; background: #fff; }
.feature-grid { max-width: 1000px; margin: 0 auto; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.feature-card {
  padding: 32px 24px; background: #f5f7fa; border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.feature-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
.feature-icon { font-size: 40px; margin-bottom: 16px; }
.feature-card h3 { margin: 0 0 8px; color: #303133; font-size: 18px; }
.feature-card p { margin: 0; color: #909399; font-size: 14px; line-height: 1.6; }

/* 模块展示 */
.modules { padding: 80px 24px; background: #f5f7fa; }
.module-grid { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.module-card {
  display: flex; align-items: center; gap: 20px;
  padding: 24px 28px; background: #fff; border-radius: 12px;
  border: 1px solid #e4e7ed; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.module-card:hover { border-color: #409EFF; box-shadow: 0 4px 12px rgba(64,158,255,0.1); }
.module-icon { font-size: 36px; flex-shrink: 0; }
.module-info { flex: 1; }
.module-info h3 { margin: 0 0 6px; font-size: 18px; color: #303133; }
.module-info p { margin: 0 0 10px; font-size: 14px; color: #909399; }
.module-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.module-tags span {
  padding: 2px 10px; background: #ecf5ff; color: #409EFF;
  border-radius: 20px; font-size: 12px;
}
.module-help {
  width: 24px; height: 24px; border-radius: 50%; background: #909399;
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: bold; cursor: help; flex-shrink: 0;
}

/* API 文档 */
.docs-section { padding: 80px 24px; background: #fff; }
.docs-inner { max-width: 900px; margin: 0 auto; }
.docs-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 40px; }
.doc-item {
  padding: 20px; background: #f5f7fa; border-radius: 8px;
  border-left: 4px solid #409EFF;
}
.doc-item h4 { margin: 0 0 10px; color: #303133; font-size: 15px; }
.doc-item code { display: block; font-size: 13px; color: #606266; margin: 4px 0; font-family: 'Courier New', monospace; }

/* 页脚 */
.footer { padding: 24px; text-align: center; color: #909399; font-size: 14px; background: #fff; border-top: 1px solid #e4e7ed; }
.footer a { color: #409EFF; text-decoration: none; }
</style>