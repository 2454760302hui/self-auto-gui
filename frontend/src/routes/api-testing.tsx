import { createFileRoute } from '@tanstack/react-router';
import * as React from 'react';
import {
  Zap,
  Play,
  Square,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Copy,
  Download,
  RefreshCw,
  Trash2,
  Plus,
  FileText,
  Code2,
  Terminal,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Wrench,
} from 'lucide-react';
import {
  runInterfaceTest,
  PRESET_TEST_TEMPLATES,
  type APITestRunResult,
} from '../lib/interface-api';
import { Toast, type ToastType } from '../components/Toast';
import { Button } from '@/components/ui/button';

export const Route = createFileRoute('/api-testing')({
  component: APITestingPage,
});

const ENVIRONMENTS = [
  { key: 'aliyun', label: '阿里云', url: 'https://api-c.soboten.com' },
  { key: 'tencent', label: '腾讯云', url: 'https://api-c.soboten.com' },
  { key: 'sg', label: '新加坡', url: 'https://sg-api-c.soboten.com' },
  { key: 'us', label: '美国', url: 'https://us-api-c.soboten.com' },
];

interface TestOutputLine {
  time: string;
  type: 'info' | 'success' | 'error' | 'header' | 'request' | 'response';
  content: string;
}

function APITestingPage() {
  const [yamlCode, setYamlCode] = React.useState('');
  const [env, setEnv] = React.useState('aliyun');
  const [isRunning, setIsRunning] = React.useState(false);
  const [output, setOutput] = React.useState<TestOutputLine[]>([]);
  const [showTemplates, setShowTemplates] = React.useState(false);
  const [showHelp, setShowHelp] = React.useState(false);
  const [lastResult, setLastResult] = React.useState<{ success: boolean; output: string } | null>(null);
  const [toast, setToast] = React.useState({ message: '', type: 'info' as ToastType, visible: false });
  const outputIdRef = React.useRef(0);

  const showToast = (message: string, type: ToastType = 'info') => {
    setToast({ message, type, visible: true });
    setTimeout(() => setToast(p => ({ ...p, visible: false })), 3000);
  };

  const addOutput = (type: TestOutputLine['type'], content: string) => {
    const line: TestOutputLine = {
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      type,
      content,
    };
    setOutput(prev => [...prev.slice(-300), line]);
  };

  const runTest = async () => {
    if (!yamlCode.trim()) { showToast('请输入 YAML 测试用例', 'warning'); return; }
    setIsRunning(true);
    addOutput('info', '━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    addOutput('info', `▶ 开始执行 [${new Date().toLocaleString('zh-CN')}]`);
    addOutput('info', `▶ 环境: ${ENVIRONMENTS.find(e => e.key === env)?.label || env}`);

    try {
      const result = await runInterfaceTest(yamlCode, env);
      setLastResult({ success: result.success, output: result.output || result.error || '' });
      if (result.success) {
        addOutput('success', '✓ 测试通过');
        if (result.output) {
          addOutput('response', result.output);
        }
        showToast('测试执行成功', 'success');
      } else {
        addOutput('error', `✗ 测试失败: ${result.error}`);
        if (result.output) {
          addOutput('response', result.output);
        }
        showToast('测试执行失败', 'error');
      }
    } catch (e) {
      addOutput('error', `✗ 执行异常: ${e instanceof Error ? e.message : String(e)}`);
      showToast('执行异常', 'error');
    } finally {
      setIsRunning(false);
    }
  };

  const loadTemplate = (yaml: string) => {
    setYamlCode(yaml);
    setShowTemplates(false);
    showToast('已加载测试模板', 'info');
  };

  const copyOutput = () => {
    if (lastResult?.output) {
      navigator.clipboard.writeText(lastResult.output);
      showToast('已复制到剪贴板', 'success');
    }
  };

  const clearOutput = () => setOutput([]);
  const clearEditor = () => setYamlCode('');

  const currentEnv = ENVIRONMENTS.find(e => e.key === env);

  return (
    <div className="h-full flex flex-col bg-background">
      {toast.visible && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(p => ({ ...p, visible: false }))} />
      )}

      {/* Header */}
      <div className="px-6 py-3 border-b border-border flex items-center justify-between flex-shrink-0"
        style={{ borderColor: 'rgba(6,182,212,0.1)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold">
              <span style={{ background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                API 接口测试
              </span>
            </h1>
            <p className="text-[11px] text-muted-foreground">YAML 驱动 · pytest 引擎 · 多环境支持</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Environment Selector */}
          <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-secondary/30 border border-border">
            <span className="text-[11px] text-muted-foreground">环境:</span>
            <select
              value={env}
              onChange={e => setEnv(e.target.value)}
              className="bg-transparent text-xs font-medium outline-none cursor-pointer"
            >
              {ENVIRONMENTS.map(e => (
                <option key={e.key} value={e.key}>{e.label}</option>
              ))}
            </select>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowHelp(!showHelp)}>
            <BookOpen className="w-3.5 h-3.5 mr-1" />
            语法参考
          </Button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Editor Panel */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Toolbar */}
          <div className="px-4 py-2 flex items-center justify-between border-b border-border flex-shrink-0"
            style={{ borderColor: 'rgba(6,182,212,0.08)' }}>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="gap-1" onClick={() => setShowTemplates(!showTemplates)}>
                <FileText className="w-3.5 h-3.5" />
                {showTemplates ? '收起' : '模板'}
              </Button>
              <Button variant="ghost" size="sm" onClick={clearEditor}>
                <Trash2 className="w-3.5 h-3.5 mr-1" />
                清空
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground">
                {currentEnv?.url}
              </span>
              <Button
                className="gap-1"
                onClick={runTest}
                disabled={isRunning}
              >
                {isRunning ? (
                  <><Loader2 className="w-4 h-4 animate-spin" />执行中...</>
                ) : (
                  <><Play className="w-4 h-4" />运行测试</>
                )}
              </Button>
            </div>
          </div>

          {/* Templates Dropdown */}
          {showTemplates && (
            <div className="border-b border-border p-3 flex-shrink-0"
              style={{ borderColor: 'rgba(6,182,212,0.08)', background: 'rgba(6,182,212,0.02)' }}>
              <div className="grid grid-cols-2 gap-2">
                {PRESET_TEST_TEMPLATES.map(t => (
                  <button
                    key={t.name}
                    onClick={() => loadTemplate(t.yaml)}
                    className="text-left p-3 rounded-xl border border-border hover:border-cyan-500/40 hover:bg-cyan-500/5 transition-all"
                  >
                    <div className="text-xs font-medium mb-1 flex items-center gap-1.5">
                      <Code2 className="w-3.5 h-3.5 text-cyan-500" />
                      {t.name}
                    </div>
                    <div className="text-[10px] text-muted-foreground">{t.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* YAML Editor */}
          <div className="flex-1 overflow-hidden p-4 min-h-0">
            <textarea
              value={yamlCode}
              onChange={e => setYamlCode(e.target.value)}
              placeholder={`# YAML 接口测试用例&#10;config:&#10;  base_url: https://httpbin.org&#10;  env: ${env}&#10;&#10;teststeps:&#10;  - name: GET请求&#10;    request:&#10;      method: GET&#10;      url: /get&#10;    validate:&#10;      - assert: status_code&#10;        expect: 200`}
              spellCheck={false}
              className="w-full h-full px-4 py-3 rounded-xl border border-border bg-card text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
              style={{ fontFamily: "'Fira Code', 'Consolas', monospace", fontSize: '12px', lineHeight: '1.7' }}
            />
          </div>

          {/* Help Panel */}
          {showHelp && (
            <div className="border-t border-border p-4 flex-shrink-0 max-h-64 overflow-y-auto"
              style={{ borderColor: 'rgba(6,182,212,0.08)', background: 'rgba(6,182,212,0.02)' }}>
              <div className="text-xs font-medium mb-3 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-cyan-500" />
                YAML 语法参考
              </div>
              <div className="grid grid-cols-2 gap-4 text-[11px]">
                <div>
                  <div className="font-semibold mb-1.5 text-muted-foreground">基本结构</div>
                  <div className="space-y-1 font-mono text-[10px]">
                    <div><span className="text-cyan-400">config</span>: 全局配置</div>
                    <div><span className="text-cyan-400">teststeps</span>: 测试步骤</div>
                    <div><span className="text-cyan-400">name</span>: 步骤名称</div>
                    <div><span className="text-cyan-400">request</span>: 请求配置</div>
                    <div><span className="text-cyan-400">validate</span>: 断言</div>
                    <div><span className="text-cyan-400">extract</span>: 变量提取</div>
                  </div>
                </div>
                <div>
                  <div className="font-semibold mb-1.5 text-muted-foreground">常用断言</div>
                  <div className="space-y-1 font-mono text-[10px]">
                    <div><span className="text-cyan-400">eq</span>: 等于</div>
                    <div><span className="text-cyan-400">lt/gt</span>: 小于/大于</div>
                    <div><span className="text-cyan-400">contains</span>: 包含</div>
                    <div><span className="text-cyan-400">regex_match</span>: 正则</div>
                    <div><span className="text-cyan-400">response_time_less_than</span>: 响应时间</div>
                    <div><span className="text-cyan-400">json_schema</span>: JSON Schema</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Output Panel */}
        <div className="w-80 border-l border-border flex flex-col overflow-hidden flex-shrink-0"
          style={{ borderColor: 'rgba(6,182,212,0.1)' }}>
          <div className="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0"
            style={{ borderColor: 'rgba(6,182,212,0.08)' }}>
            <div className="flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-medium">测试输出</span>
              {lastResult && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                  lastResult.success
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {lastResult.success ? 'PASS' : 'FAIL'}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={copyOutput} title="复制">
                <Copy className="w-3 h-3" />
              </Button>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={clearOutput} title="清空">
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
            {output.length === 0 && (
              <div className="text-center py-8">
                <Terminal className="w-8 h-8 mx-auto mb-2 text-muted-foreground/30" />
                <p className="text-xs text-muted-foreground">暂无输出</p>
                <p className="text-[10px] text-muted-foreground/60">点击「运行测试」开始执行</p>
              </div>
            )}
            {output.map((line, i) => (
              <div key={i} className={`text-[11px] leading-relaxed font-mono ${
                line.type === 'error' ? 'text-red-400' :
                line.type === 'success' ? 'text-emerald-400' :
                line.type === 'header' ? 'text-cyan-400 font-bold' :
                line.type === 'request' ? 'text-amber-400' :
                line.type === 'response' ? 'text-muted-foreground' :
                'text-muted-foreground/80'
              }`}>
                <span className="text-muted-foreground/40 mr-1">{line.time}</span>
                {line.content}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
