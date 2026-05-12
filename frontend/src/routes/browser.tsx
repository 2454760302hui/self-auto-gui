import { createFileRoute } from '@tanstack/react-router';
import * as React from 'react';
import {
  Globe,
  Play,
  Square,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Download,
  Copy,
  ChevronDown,
  ChevronUp,
  Bot,
  Code2,
  FileText,
  Terminal,
  Zap,
  RefreshCw,
  Image,
  Clock,
} from 'lucide-react';
import {
  getBrowserHealth,
  getBrowserLLMStatus,
  getBrowserDemos,
  runBrowserTask,
  listBrowserTraces,
  getBrowserTrace,
  clearBrowserTraces,
  convertBrowserNLPToDSL,
  type BrowserTaskResult,
  type BrowserTrace,
} from '../lib/browser-api';
import { Toast, type ToastType } from '../components/Toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export const Route = createFileRoute('/browser')({
  component: BrowserPage,
});

type RunMode = 'llm' | 'dsl' | 'nlp';

interface LogEntry {
  id: string;
  time: string;
  type: 'info' | 'success' | 'error' | 'command' | 'result';
  content: string;
}

function BrowserPage() {
  const [mode, setMode] = React.useState<RunMode>('nlp');
  const [taskInput, setTaskInput] = React.useState('');
  const [dslCode, setDslCode] = React.useState('');
  const [isRunning, setIsRunning] = React.useState(false);
  const [health, setHealth] = React.useState<{ status: string; llm_status: string; llm_model: string } | null>(null);
  const [llmStatus, setLlmStatus] = React.useState<{ configured: boolean; model: string; provider: string } | null>(null);
  const [logs, setLogs] = React.useState<LogEntry[]>([]);
  const [traces, setTraces] = React.useState<BrowserTrace[]>([]);
  const [demos, setDemos] = React.useState<Record<string, string>>({});
  const [showDemos, setShowDemos] = React.useState(false);
  const [showHistory, setShowHistory] = React.useState(true);
  const [currentResult, setCurrentResult] = React.useState<BrowserTaskResult | null>(null);
  const [gifUrl, setGifUrl] = React.useState<string | null>(null);
  const [toast, setToast] = React.useState({ message: '', type: 'info' as ToastType, visible: false });
  const [maxSteps, setMaxSteps] = React.useState(20);
  const logsEndRef = React.useRef<HTMLDivElement>(null);
  const logIdRef = React.useRef(0);

  const showToast = (message: string, type: ToastType = 'info') => {
    setToast({ message, type, visible: true });
    setTimeout(() => setToast(p => ({ ...p, visible: false })), 3000);
  };

  const addLog = (type: LogEntry['type'], content: string) => {
    const entry: LogEntry = {
      id: `log-${++logIdRef.current}`,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      type,
      content,
    };
    setLogs(prev => [...prev.slice(-200), entry]);
  };

  React.useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const loadStatus = React.useCallback(async () => {
    try {
      const h = await getBrowserHealth();
      setHealth({
        status: h.data.status,
        llm_status: h.data.llm.status,
        llm_model: h.data.llm.model,
      });
    } catch { setHealth(null); }

    try {
      const l = await getBrowserLLMStatus();
      setLlmStatus({
        configured: l.data.configured,
        model: l.data.model,
        provider: l.data.provider,
      });
    } catch { setLlmStatus(null); }

    try {
      const d = await getBrowserDemos();
      setDemos(d.demos);
    } catch { setDemos({}); }

    try {
      const t = await listBrowserTraces();
      setTraces(t.runs);
    } catch { setTraces([]); }
  }, []);

  React.useEffect(() => { loadStatus(); }, [loadStatus]);

  const runTask = async () => {
    const input = mode === 'dsl' ? dslCode : taskInput;
    if (!input.trim()) { showToast('请输入任务内容', 'warning'); return; }

    setIsRunning(true);
    setCurrentResult(null);
    setGifUrl(null);
    addLog('info', `▶ 启动任务 [${mode.toUpperCase()}]`);

    try {
      const result = await runBrowserTask({
        task: input,
        mode,
        max_steps: maxSteps,
      });

      if (result.success && result.data) {
        setCurrentResult(result.data);
        if (result.data.has_gif && result.data.gif_url) {
          setGifUrl(result.data.gif_url);
        }
        addLog('success', `✓ 任务完成 (${result.data.elapsed_ms}ms)`);
        if (result.data.log) {
          result.data.log.split('\n').filter(Boolean).forEach((l: string) => {
            if (l.includes('[screenshot]')) addLog('result', l.trim());
            else if (l.startsWith('▶')) addLog('command', l.replace('▶', '').trim());
            else if (l.trim()) addLog('info', l.trim());
          });
        }
        if (result.data.final_result) {
          addLog('result', `最终结果: ${result.data.final_result.substring(0, 200)}`);
        }
        showToast('任务执行成功', 'success');
      } else {
        addLog('error', `✗ 任务失败: ${result.error || result.data?.error || '未知错误'}`);
        showToast('任务执行失败', 'error');
      }
    } catch (e) {
      addLog('error', `✗ 执行异常: ${e instanceof Error ? e.message : String(e)}`);
      showToast('执行异常', 'error');
    } finally {
      setIsRunning(false);
      loadStatus();
    }
  };

  const convertNLP = async () => {
    if (!taskInput.trim()) { showToast('请输入自然语言任务', 'warning'); return; }
    try {
      addLog('info', '⚙ NLP 转换中...');
      const result = await convertBrowserNLPToDSL(taskInput);
      if (result.success && result.data) {
        setDslCode(result.data.dsl);
        setMode('dsl');
        addLog('success', '✓ 已转换为 DSL');
        showToast('NLP 转 DSL 成功', 'success');
      } else {
        addLog('error', `转换失败: ${result.error}`);
      }
    } catch (e) {
      addLog('error', `转换异常: ${e}`);
    }
  };

  const loadDemo = (name: string, script: string) => {
    setDslCode(script);
    setMode('dsl');
    setShowDemos(false);
    addLog('info', `📋 已加载演示: ${name}`);
    showToast(`已加载: ${name}`, 'info');
  };

  const loadTrace = async (trace: BrowserTrace) => {
    try {
      const result = await getBrowserTrace(trace.task_id);
      setCurrentResult(result);
      if (result.dsl) setDslCode(result.dsl);
      if (result.log) {
        const lines = result.log.split('\n').filter(Boolean).slice(-20);
        lines.forEach(l => {
          if (l.includes('[screenshot]')) addLog('result', l.trim());
          else if (l.startsWith('▶')) addLog('command', l.replace('▶', '').trim());
          else if (l.trim()) addLog('info', l.trim());
        });
      }
      if (result.has_gif) {
        setGifUrl(`/traces/${trace.task_id}/recording.gif`);
      }
    } catch (e) {
      showToast('加载记录失败', 'error');
    }
  };

  const clearLogs = () => setLogs([]);
  const handleClearTraces = async () => {
    await clearBrowserTraces();
    setTraces([]);
    showToast('历史记录已清空', 'success');
  };

  const copyResult = () => {
    if (currentResult?.log) {
      navigator.clipboard.writeText(currentResult.log);
      showToast('已复制到剪贴板', 'success');
    }
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {toast.visible && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(p => ({ ...p, visible: false }))} />
      )}

      {/* Header */}
      <div className="px-6 py-3 border-b border-border flex items-center justify-between flex-shrink-0"
        style={{ borderColor: 'rgba(124,58,237,0.1)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-cyan-500 flex items-center justify-center">
            <Globe className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold">
              <span className="nexus-gradient-text">浏览器自动化</span>
            </h1>
            <p className="text-[11px] text-muted-foreground">browser-use · Playwright · NLP/DSL</p>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2">
          {health && (
            <span className="text-xs px-2.5 py-1 rounded-full bg-success/10 text-success border border-success/20">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-success mr-1 animate-pulse" />
              后端就绪
            </span>
          )}
          {llmStatus && (
            <span className={`text-xs px-2.5 py-1 rounded-full border ${
              llmStatus.configured
                ? 'bg-violet-500/10 text-violet-400 border-violet-500/20'
                : 'bg-gray-500/10 text-gray-400 border-gray-500/20'
            }`}>
              {llmStatus.configured ? '✓' : '✗'} LLM: {llmStatus.configured ? llmStatus.model : '未配置'}
            </span>
          )}
          <Button variant="ghost" size="icon" onClick={loadStatus} title="刷新状态">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Editor */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Mode Selector */}
          <div className="px-4 pt-3 pb-0 flex-shrink-0">
            <div className="flex items-center gap-1 p-1 rounded-xl bg-secondary/30 border border-border w-fit">
              {([
                { key: 'nlp', label: 'NLP 自然语言', icon: Bot },
                { key: 'dsl', label: 'DSL 脚本', icon: Code2 },
                { key: 'llm', label: 'LLM 直接', icon: Zap },
              ] as const).map(m => (
                <button
                  key={m.key}
                  onClick={() => setMode(m.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    mode === m.key
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <m.icon className="w-3.5 h-3.5" />
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* Input Area */}
          <div className="flex-1 overflow-hidden flex flex-col px-4 py-3 gap-3 min-h-0">
            {/* NLP Input */}
            {mode === 'nlp' && (
              <div className="flex-shrink-0">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <Bot className="w-3.5 h-3.5" /> 自然语言任务
                  </label>
                  <Button size="sm" variant="ghost" className="h-6 text-[11px]" onClick={convertNLP}>
                    <Zap className="w-3 h-3 mr-1" /> 转换为 DSL
                  </Button>
                </div>
                <textarea
                  value={taskInput}
                  onChange={e => setTaskInput(e.target.value)}
                  placeholder="例如：打开 Bing，搜索 Python 教程，然后截一张图"
                  className="w-full h-24 px-3 py-2 rounded-xl border border-border bg-card text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <div className="flex items-center gap-2 mt-2">
                  <label className="text-xs text-muted-foreground">最大步数</label>
                  <input
                    type="number"
                    value={maxSteps}
                    onChange={e => setMaxSteps(Number(e.target.value))}
                    min={1} max={100}
                    className="w-16 px-2 py-0.5 rounded border border-border bg-card text-xs text-center"
                  />
                </div>
              </div>
            )}

            {/* DSL Editor */}
            {mode === 'dsl' && (
              <div className="flex-1 overflow-hidden flex flex-col min-h-0">
                <div className="flex items-center justify-between mb-1.5 flex-shrink-0">
                  <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5" /> DSL 脚本
                  </label>
                  <Button size="sm" variant="ghost" className="h-6 text-[11px]" onClick={() => setShowDemos(!showDemos)}>
                    <FileText className="w-3 h-3 mr-1" />
                    {showDemos ? '收起示例' : '示例模板'}
                  </Button>
                </div>

                {/* Demo Templates */}
                {showDemos && (
                  <div className="mb-2 flex-shrink-0">
                    <div className="max-h-36 overflow-y-auto rounded-lg border border-border divide-y divide-border">
                      {Object.entries(demos).slice(0, 10).map(([name, script]) => (
                        <button
                          key={name}
                          onClick={() => loadDemo(name, script.trim())}
                          className="w-full text-left px-3 py-2 hover:bg-secondary/50 transition-colors text-xs"
                        >
                          <div className="font-medium text-foreground truncate">{name}</div>
                          <div className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
                            {script.split('\n').filter(l => l.trim() && !l.trim().startsWith('#'))[0] || ''}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <textarea
                  value={dslCode}
                  onChange={e => setDslCode(e.target.value)}
                  placeholder="输入 DSL 脚本，例如：&#10;打开 https://cn.bing.com&#10;等待加载完成&#10;截图&#10;输入 #sb_form_q Python&#10;按键 Enter"
                  spellCheck={false}
                  className="flex-1 w-full px-3 py-2 rounded-xl border border-border bg-card text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-primary min-h-0"
                  style={{ fontFamily: "'Fira Code', 'Consolas', monospace", fontSize: '12px', lineHeight: '1.6' }}
                />
                <div className="flex items-center gap-2 mt-1.5 flex-shrink-0">
                  <label className="text-xs text-muted-foreground">步数限制</label>
                  <input
                    type="number"
                    value={maxSteps}
                    onChange={e => setMaxSteps(Number(e.target.value))}
                    min={1} max={100}
                    className="w-16 px-2 py-0.5 rounded border border-border bg-card text-xs text-center"
                  />
                </div>
              </div>
            )}

            {/* LLM Direct Mode */}
            {mode === 'llm' && (
              <div className="flex-shrink-0">
                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-1.5">
                  <Zap className="w-3.5 h-3.5" /> LLM 直接执行
                </label>
                <textarea
                  value={taskInput}
                  onChange={e => setTaskInput(e.target.value)}
                  placeholder="直接输入自然语言任务，LLM 将自动决定执行步骤..."
                  className="w-full h-24 px-3 py-2 rounded-xl border border-border bg-card text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <div className="flex items-center gap-2 mt-2">
                  <label className="text-xs text-muted-foreground">最大步数</label>
                  <input
                    type="number"
                    value={maxSteps}
                    onChange={e => setMaxSteps(Number(e.target.value))}
                    min={1} max={100}
                    className="w-16 px-2 py-0.5 rounded border border-border bg-card text-xs text-center"
                  />
                </div>
              </div>
            )}

            {/* Run Button */}
            <div className="flex-shrink-0 flex items-center gap-2">
              <Button
                className="gap-2 flex-1"
                onClick={runTask}
                disabled={isRunning}
              >
                {isRunning ? (
                  <><Loader2 className="w-4 h-4 animate-spin" />执行中...</>
                ) : (
                  <><Play className="w-4 h-4" />执行任务</>
                )}
              </Button>
              {isRunning && (
                <Button variant="destructive" className="gap-1">
                  <Square className="w-4 h-4" /> 停止
                </Button>
              )}
            </div>

            {/* GIF Preview */}
            {gifUrl && (
              <div className="flex-shrink-0 rounded-xl overflow-hidden border border-border">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-card border-b border-border">
                  <Image className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium">执行回放</span>
                </div>
                <img
                  src={gifUrl}
                  alt="Execution replay"
                  className="w-full max-h-48 object-contain bg-black/5"
                />
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Logs & History */}
        <div className="w-80 border-l border-border flex flex-col overflow-hidden flex-shrink-0"
          style={{ borderColor: 'rgba(124,58,237,0.1)' }}>
          {/* Logs */}
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            <div className="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0"
              style={{ borderColor: 'rgba(124,58,237,0.08)' }}>
              <div className="flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs font-medium">执行日志</span>
                <span className="text-[10px] text-muted-foreground">({logs.length})</span>
              </div>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={clearLogs} title="清空日志">
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
              {logs.length === 0 && (
                <div className="text-center py-8">
                  <Terminal className="w-8 h-8 mx-auto mb-2 text-muted-foreground/30" />
                  <p className="text-xs text-muted-foreground">暂无日志</p>
                  <p className="text-[10px] text-muted-foreground/60">执行任务后将显示日志</p>
                </div>
              )}
              {logs.map(log => (
                <div key={log.id} className={`text-[11px] leading-relaxed ${
                  log.type === 'error' ? 'text-red-400' :
                  log.type === 'success' ? 'text-emerald-400' :
                  log.type === 'command' ? 'text-violet-400' :
                  log.type === 'result' ? 'text-cyan-400' :
                  'text-muted-foreground'
                }`}>
                  <span className="text-muted-foreground/50 mr-1">{log.time}</span>
                  {log.content}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>

          {/* History */}
          <div className="border-t border-border flex-shrink-0 flex flex-col max-h-64 overflow-hidden"
            style={{ borderColor: 'rgba(124,58,237,0.08)' }}>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center justify-between px-3 py-2 hover:bg-secondary/30 transition-colors flex-shrink-0"
            >
              <div className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs font-medium">历史记录</span>
                <span className="text-[10px] text-muted-foreground">({traces.length})</span>
              </div>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" className="h-5 w-5" onClick={e => { e.stopPropagation(); handleClearTraces(); }} title="清空历史">
                  <Trash2 className="w-3 h-3" />
                </Button>
                {showHistory ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" />}
              </div>
            </button>

            {showHistory && (
              <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-1">
                {traces.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">暂无历史记录</p>
                )}
                {traces.slice(0, 20).map(trace => (
                  <button
                    key={trace.task_id}
                    onClick={() => loadTrace(trace)}
                    className="w-full text-left p-2 rounded-lg hover:bg-secondary/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                        trace.success ? 'bg-success' : 'bg-red-500'
                      }`} />
                      <span className="text-[10px] text-muted-foreground flex-shrink-0">
                        {(trace.elapsed_ms / 1000).toFixed(1)}s
                      </span>
                    </div>
                    <p className="text-[11px] text-foreground truncate">{trace.task}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {trace.mode} · {trace.steps}步
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
