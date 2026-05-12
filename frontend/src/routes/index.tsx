import { createFileRoute, Link } from '@tanstack/react-router';
import * as React from 'react';
import {
  Globe,
  Shield,
  Zap,
  Smartphone,
  Bot,
  ArrowRight,
  CheckCircle2,
  Star,
  Play,
  Terminal,
  Sparkles,
  Cpu,
  Code2,
  Layers,
} from 'lucide-react';

export const Route = createFileRoute('/')({
  component: HomeComponent,
});

const FEATURES = [
  {
    icon: Globe,
    color: 'violet',
    title: '浏览器自动化',
    description: '自然语言驱动浏览器，支持 NLP/DSL 双模式，自动执行复杂 Web 任务并生成 GIF 回放。',
    href: '/browser',
    badge: 'NEW',
    highlights: ['自然语言驱动', '30+ DSL 指令', 'GIF 录制'],
  },
  {
    icon: Zap,
    color: 'cyan',
    title: 'API 接口测试',
    description: 'YAML 驱动的零代码接口测试，支持多环境切换、变量提取、断言验证和报告导出。',
    href: '/api-testing',
    badge: 'NEW',
    highlights: ['YAML 模板', '变量提取', '断言验证'],
  },
  {
    icon: Shield,
    color: 'red',
    title: '安全测试',
    description: '集成 Xray + Rad 引擎，自动检测 SQL 注入、XSS、命令注入等安全漏洞。',
    href: '/security',
    badge: 'NEW',
    highlights: ['被动扫描', '多插件覆盖', '报告导出'],
  },
  {
    icon: Smartphone,
    color: 'emerald',
    title: '移动设备控制',
    description: '连接 Android/HarmonyOS 设备，AI 对话驱动触控、输入、应用启动等操作。',
    href: '/chat',
    badge: 'AutoGLM',
    highlights: ['ADB/HDC 连接', 'AI 对话控制', '实时投屏'],
  },
];

const STATS = [
  { value: '30+', label: 'DSL 操作指令' },
  { value: '6+', label: 'LLM 提供商' },
  { value: '5', label: '安全插件' },
  { value: '100%', label: '开源免费' },
];

const CAPABILITIES = [
  { icon: Bot, title: '自然语言理解', desc: 'LLM 理解意图，自动转换为可执行指令' },
  { icon: Code2, title: '多语言支持', desc: '支持 Python、JavaScript、DSL 等多种方式' },
  { icon: Layers, title: '工作流编排', desc: '可视化流程设计，一键执行复杂任务' },
  { icon: Cpu, title: '本地运行', desc: '数据不出本地，保护隐私安全' },
];

function FeatureCard({ feature }: { feature: typeof FEATURES[0] }) {
  const Icon = feature.icon;
  const colorMap: Record<string, { bg: string; text: string; border: string; icon: string }> = {
    violet: { bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/20', icon: 'text-violet-400' },
    cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20', icon: 'text-cyan-400' },
    red: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', icon: 'text-red-400' },
    emerald: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', icon: 'text-emerald-400' },
  };
  const colors = colorMap[feature.color];
  return (
    <Link
      to={feature.href}
      className="feature-card group block"
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl ${colors.bg} border ${colors.border} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${colors.icon}`} />
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${colors.bg} ${colors.text} border ${colors.border}`}>
          {feature.badge}
        </span>
      </div>
      <h3 className="font-semibold text-base mb-1.5 group-hover:text-primary transition-colors">
        {feature.title}
      </h3>
      <p className="text-xs text-muted-foreground leading-relaxed mb-3">
        {feature.description}
      </p>
      <div className="flex flex-wrap gap-1.5 mb-4">
        {feature.highlights.map(h => (
          <span key={h} className="text-[10px] px-2 py-0.5 rounded-full bg-secondary/60 text-muted-foreground border border-border">
            {h}
          </span>
        ))}
      </div>
      <div className={`flex items-center gap-1 text-xs font-medium ${colors.text} opacity-0 group-hover:opacity-100 transition-opacity`}>
        <span>立即使用</span>
        <ArrowRight className="w-3 h-3" />
      </div>
    </Link>
  );
}

function HomeComponent() {
  return (
    <div className="flex-1 overflow-y-auto">
      {/* Hero Section - Grok Style */}
      <section className="relative overflow-hidden"
        style={{
          background: 'linear-gradient(180deg, rgba(124,58,237,0.08) 0%, transparent 50%)',
          minHeight: '70vh',
        }}>
        {/* Background Effects */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-20 left-1/4 w-[500px] h-[500px] bg-violet-500/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-20 right-1/4 w-[400px] h-[400px] bg-cyan-500/8 rounded-full blur-[100px]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-violet-600/5 rounded-full blur-[80px]" />
        </div>

        <div className="relative max-w-5xl mx-auto px-8 py-20 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 mb-8">
            <Sparkles className="w-4 h-4 text-violet-400" />
            <span className="text-sm text-violet-300">智能自动化平台</span>
          </div>

          {/* Logo */}
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl mb-8"
            style={{
              background: 'linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%)',
              boxShadow: '0 20px 60px rgba(124,58,237,0.4), 0 0 0 1px rgba(255,255,255,0.1) inset',
            }}>
            <span className="text-white font-bold text-3xl">N</span>
          </div>

          <h1 className="text-5xl font-bold mb-4 tracking-tight">
            <span className="nexus-gradient-text">AutoGLM</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-3">
            一句话完成自动化任务
          </p>
          <p className="text-base text-muted-foreground/70 mb-10 max-w-2xl mx-auto leading-relaxed">
            集浏览器自动化、API 测试、安全扫描、移动设备控制于一体，用自然语言驱动一切自动化任务。
          </p>

          {/* CTA Buttons */}
          <div className="flex items-center justify-center gap-4 flex-wrap mb-16">
            <Link to="/browser">
              <button className="group flex items-center gap-2 px-6 py-3 rounded-xl text-base font-medium text-white transition-all hover:scale-105"
                style={{
                  background: 'linear-gradient(135deg, #7c3aed, #5b21b6)',
                  boxShadow: '0 8px 30px rgba(124,58,237,0.4)',
                }}>
                <Play className="w-5 h-5" />
                立即开始
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-6 max-w-3xl mx-auto">
            {STATS.map(stat => (
              <div key={stat.label} className="text-center p-4 rounded-2xl bg-card/50 border border-border backdrop-blur-sm">
                <div className="text-3xl font-bold nexus-gradient-text mb-1">{stat.value}</div>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Modules Grid */}
      <section className="px-8 py-16 border-t border-border"
        style={{ borderColor: 'rgba(124,58,237,0.08)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">四大核心模块</h2>
            <p className="text-muted-foreground">开箱即用，覆盖主流自动化场景</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {FEATURES.map(f => <FeatureCard key={f.href} feature={f} />)}
          </div>
        </div>
      </section>

      {/* Capabilities Section */}
      <section className="px-8 py-16 border-t border-border"
        style={{ borderColor: 'rgba(124,58,237,0.08)', background: 'rgba(124,58,237,0.02)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">核心优势</h2>
            <p className="text-muted-foreground">企业级能力，个人级体验</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {CAPABILITIES.map(item => (
              <div key={item.title} className="text-center p-6 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-all">
                <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
                  <item.icon className="w-6 h-6 text-violet-400" />
                </div>
                <h3 className="font-semibold mb-2">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section className="px-8 py-16 border-t border-border"
        style={{ borderColor: 'rgba(124,58,237,0.08)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">工作流程</h2>
            <p className="text-muted-foreground">从自然语言到执行的完整闭环</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', title: '描述任务', desc: '用自然语言描述你想完成的自动化任务', icon: Bot, color: 'violet' },
              { step: '02', title: 'AI 解析', desc: 'LLM 理解意图，转换为可执行指令', icon: Sparkles, color: 'cyan' },
              { step: '03', title: '自动执行', desc: '浏览器/设备/API 按指令精确执行', icon: Terminal, color: 'emerald' },
            ].map(item => (
              <div key={item.step} className="relative p-8 rounded-2xl bg-card border border-border group hover:border-violet-500/30 transition-all">
                <div className="absolute -top-4 -left-4 w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-cyan-500 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-violet-500/30">
                  {item.step}
                </div>
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
                    <item.icon className="w-6 h-6 text-violet-400" />
                  </div>
                  <h3 className="text-lg font-semibold">{item.title}</h3>
                </div>
                <p className="text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* LLM Provider Section */}
      <section className="px-8 py-16 border-t border-border"
        style={{ borderColor: 'rgba(124,58,237,0.08)', background: 'rgba(124,58,237,0.02)' }}>
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-3">支持多种 LLM 提供商</h2>
          <p className="text-muted-foreground mb-8">灵活配置 AI 模型，支持主流服务商</p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            {['OpenAI GPT-4', 'Anthropic Claude', 'Google Gemini', '智谱 GLM', 'Azure OpenAI', '本地模型'].map(p => (
              <span key={p} className="px-5 py-2.5 rounded-xl text-sm font-medium bg-card border border-border hover:border-violet-500/30 transition-all cursor-default">
                {p}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-8 py-20 text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold mb-4">开始你的自动化之旅</h2>
          <p className="text-muted-foreground mb-8">免费开源，无需注册，即刻体验</p>
          <Link to="/browser">
            <button className="inline-flex items-center gap-2 px-8 py-4 rounded-xl text-lg font-medium text-white transition-all hover:scale-105"
              style={{
                background: 'linear-gradient(135deg, #7c3aed, #5b21b6)',
                boxShadow: '0 10px 40px rgba(124,58,237,0.4)',
              }}>
              <Play className="w-5 h-5" />
              免费开始使用
              <ArrowRight className="w-5 h-5" />
            </button>
          </Link>
        </div>
      </section>
    </div>
  );
}
