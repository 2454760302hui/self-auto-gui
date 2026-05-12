import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { ScrcpyPlayer } from '../components/ScrcpyPlayer';
import { useScreenshotPolling } from '../hooks/useScreenshotPolling';
import {
  listDevices,
  type Device,
  sendTap,
  sendSwipe,
  sendKeyEvent,
  sendTextInput,
  sendBack,
  sendHome,
  sendLaunchApp,
  sendDoubleTap,
  sendLongPress,
  getInstalledApps,
  forceStopApp,
  uninstallApp,
  runPytest,
  runYaml,
  type InstalledAppInfo,
} from '../api';
import {
  Hand,
  MousePointerClick,
  MousePointer2,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Square,
  Power,
  Volume2,
  VolumeX,
  Type,
  Play,
  Smartphone,
  CheckCircle2,
  AlertCircle,
  Monitor,
  Loader2,
  Search,
  X,
  Package,
  Trash2,
  Clock,
  ClipboardPaste,
  ChevronRight as ArrowRight,
  Code2,
  FileCode,
  FileText,
  Copy,
  Terminal,
  ScrollText,
} from 'lucide-react';

export const Route = createFileRoute('/automation')({
  component: AutomationPage,
});

const DEF_X = 540, DEF_Y = 960, DEF_DUR = 1000, SWIPE_DIST = 500;
const SYS_PREFIXES = ['com.android.', 'com.huawei.', 'com.hihonor.', 'com.harmony.', 'com.ohos.', 'android.'];
function isSystemPkg(pkg: string) { return SYS_PREFIXES.some(p => pkg.startsWith(p)); }

type ActionType = 'tap' | 'double_tap' | 'long_press' | 'swipe' | 'keyevent' | 'input' | 'launch' | 'back' | 'home' | 'stop';

interface RecordedAction {
  id: string;
  type: ActionType;
  params: Record<string, unknown>;
  description: string;
  ts: number;
}

// ---- Code Generators ----
function genPytest(actions: RecordedAction[], deviceSerial: string): string {
  const lines: string[] = [
    `"""Auto-generated device control test. device: ${deviceSerial}"""`,
    `import subprocess, time`,
    ``,
    `DEVICE_ID = "${deviceSerial}"`,
    ``,
    `def adb(cmd):`,
    `    subprocess.run(["adb", "-s", DEVICE_ID, "shell", cmd], check=True)`,
    ``,
    `def tap(x, y):`,
    `    adb(f"input tap {x} {y}")`,
    `    time.sleep(0.8)`,
    ``,
    `def dbclick(x, y):`,
    `    tap(x, y); time.sleep(0.1); tap(x, y)`,
    `    time.sleep(0.5)`,
    ``,
    `def swipe(sx, sy, ex, ey, d=300):`,
    `    adb(f"input swipe {sx} {sy} {ex} {ey} {d}")`,
    `    time.sleep(0.8)`,
    ``,
    `def back():`,
    `    adb("input keyevent 4")`,
    `    time.sleep(0.5)`,
    ``,
    `def home():`,
    `    adb("input keyevent 3")`,
    `    time.sleep(0.5)`,
    ``,
    `def stop(pkg):`,
    `    adb(f"am force-stop {pkg}")`,
    `    time.sleep(0.5)`,
    ``,
    `def text(t):`,
    `    adb(f'input text "{t}"')`,
    `    time.sleep(0.5)`,
    ``,
    `def test_main():`,
  ];
  actions.forEach((a, i) => {
    lines.push(`    # ${i + 1}. ${a.description}`);
    switch (a.type) {
      case 'tap':           lines.push(`    tap(${a.params.x}, ${a.params.y})`); break;
      case 'double_tap':    lines.push(`    dbclick(${a.params.x}, ${a.params.y})`); break;
      case 'long_press':    lines.push(`    adb(f"input swipe ${a.params.x} ${a.params.y} ${a.params.x} ${a.params.y} ${a.params.dur}")`); lines.push(`    time.sleep(${Number(a.params.dur) / 1000})`); break;
      case 'swipe':         lines.push(`    swipe(${a.params.sx}, ${a.params.sy}, ${a.params.ex}, ${a.params.ey}, ${a.params.d || 300})`); break;
      case 'back':          lines.push(`    back()`); break;
      case 'home':          lines.push(`    home()`); break;
      case 'stop':          lines.push(`    stop("${a.params.pkg}")`); break;
      case 'input':         lines.push(`    text("${a.params.text}")`); break;
      case 'launch':        lines.push(`    adb(f"monkey -p ${a.params.pkg} -c android.intent.category.LAUNCHER 1")`); lines.push(`    time.sleep(2.0)`); break;
      case 'keyevent':      lines.push(`    adb("input keyevent ${a.params.keycode}")`); lines.push(`    time.sleep(0.5)`); break;
    }
  });
  return lines.join('\n');
}

function genYaml(actions: RecordedAction[], deviceSerial: string): string {
  const lines: string[] = [
    `# AutoGLM 自动化用例 - ${deviceSerial}`,
    `device_id: "${deviceSerial}"`,
    `steps:`,
  ];
  actions.forEach(a => {
    switch (a.type) {
      case 'tap':          lines.push(`  - action: tap        x: ${a.params.x}    y: ${a.params.y}    description: "${a.description}"`); break;
      case 'double_tap':   lines.push(`  - action: double_tap        x: ${a.params.x}    y: ${a.params.y}    description: "${a.description}"`); break;
      case 'long_press':   lines.push(`  - action: long_press        x: ${a.params.x}    y: ${a.params.y}    duration: ${a.params.dur}    description: "${a.description}"`); break;
      case 'swipe':        lines.push(`  - action: swipe        start_x: ${a.params.sx}    start_y: ${a.params.sy}    end_x: ${a.params.ex}    end_y: ${a.params.ey}    duration: ${a.params.d || 300}    description: "${a.description}"`); break;
      case 'back':         lines.push(`  - action: back        description: "${a.description}"`); break;
      case 'home':         lines.push(`  - action: home        description: "${a.description}"`); break;
      case 'stop':         lines.push(`  - action: stop        package: "${a.params.pkg}"    description: "${a.description}"`); break;
      case 'input':        lines.push(`  - action: input_text        text: "${a.params.text}"    description: "${a.description}"`); break;
      case 'launch':       lines.push(`  - action: launch        package: "${a.params.pkg}"    description: "${a.description}"`); break;
      case 'keyevent':     lines.push(`  - action: keyevent        keycode: ${a.params.keycode}    description: "${a.description}"`); break;
    }
  });
  return lines.join('\n');
}

// ---- App Selector Dialog ----
interface AppRow extends InstalledAppInfo { running: boolean; }

function AppSelectorDialog({ deviceId, onLaunch, onClose }: { deviceId: string; onLaunch: (pkg: string) => void; onClose: () => void }) {
  const [tab, setTab] = useState<'third_party' | 'system'>('third_party');
  const [apps, setApps] = useState<AppRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [directPkg, setDirectPkg] = useState('');
  const [launching, setLaunching] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [runningPkgs, setRunningPkgs] = useState<Set<string>>(new Set());
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => {
    setLoading(true);
    getInstalledApps(deviceId).then(r => {
      if (r.success) setApps([...(r.third_party ?? []), ...(r.system ?? [])].map(a => ({ ...a, running: false })));
      else setMsg({ ok: false, text: r.error || '加载失败' });
    }).catch(() => setMsg({ ok: false, text: '加载失败' })).finally(() => setLoading(false));
  }, [deviceId]);

  const sysCount = apps.filter(a => isSystemPkg(a.package_name)).length;
  const filtered = apps.filter(a =>
    (tab === 'third_party' ? !isSystemPkg(a.package_name) : isSystemPkg(a.package_name)) &&
    (a.package_name.includes(search) || (a.app_name ?? '').includes(search))
  );

  const launch = async (pkg: string) => {
    setLaunching(true);
    try {
      const r = await sendLaunchApp(pkg, deviceId);
      if (r.success) { setRunningPkgs(p => { const n = new Set(p); n.add(pkg); return n; }); onLaunch(pkg); onClose(); }
      else setMsg({ ok: false, text: `启动失败: ${r.error}` });
    } catch { setMsg({ ok: false, text: '启动失败' }); }
    finally { setLaunching(false); }
  };

  const stop = async (pkg: string) => {
    const r = await forceStopApp(pkg, deviceId);
    if (r.success) { setRunningPkgs(p => { const n = new Set(p); n.delete(pkg); return n; }); setMsg({ ok: true, text: `已停止` }); }
    else setMsg({ ok: false, text: `停止失败: ${r.error}` });
  };

  const uninstall = async (pkg: string) => {
    if (!confirm(`确定卸载 ${pkg}？`)) return;
    setLaunching(true);
    try {
      const r = await uninstallApp(pkg, deviceId);
      if (r.success) { setApps(p => p.filter(a => a.package_name !== pkg)); setMsg({ ok: true, text: `已卸载` }); }
      else setMsg({ ok: false, text: `卸载失败: ${r.error}` });
    } catch { setMsg({ ok: false, text: '卸载失败' }); }
    finally { setLaunching(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(6px)' }} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-[#131929] border border-[#1e293b] rounded-2xl shadow-2xl flex flex-col overflow-hidden" style={{ width: 560, maxHeight: '82vh' }}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1e293b]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-purple-500/15 flex items-center justify-center"><Package className="w-4 h-4 text-purple-400" /></div>
            <div><div className="text-sm font-semibold">应用管理</div><div className="text-[11px] text-[#64748b]">第三方 {apps.length - sysCount} · 系统 {sysCount}</div></div>
          </div>
          <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-[#1e293b] text-[#64748b] hover:text-white transition-colors"><X className="w-4 h-4" /></button>
        </div>
        <div className="px-5 py-3 border-b border-[#1e293b] space-y-2.5">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#64748b]" />
            <input ref={inputRef} value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索包名或应用名..."
              className="w-full bg-[#0c0f1a] border border-[#1e293b] rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-[#475569]" />
          </div>
          <div className="flex gap-2">
            <input value={directPkg} onChange={e => setDirectPkg(e.target.value)} placeholder="直接输入包名启动..."
              className="flex-1 bg-[#0c0f1a] border border-[#1e293b] rounded-lg px-3 py-1.5 text-xs text-white placeholder-[#475569]"
              onKeyDown={e => { if (e.key === 'Enter' && directPkg.trim()) launch(directPkg.trim()); }} />
            <button onClick={() => directPkg.trim() && launch(directPkg.trim())} disabled={!directPkg.trim() || launching}
              className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white text-xs rounded-lg transition-colors flex items-center gap-1">
              {launching ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />} 启动
            </button>
          </div>
          {msg && <div className={`text-[11px] px-3 py-1.5 rounded-lg ${msg.ok ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>{msg.text}</div>}
        </div>
        <div className="flex border-b border-[#1e293b]">
          {([['third_party', '第三方应用', apps.length - sysCount], ['system', '系统应用', sysCount]] as const).map(([t, label, count]) => (
            <button key={t} onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${tab === t ? 'text-purple-400 border-b-2 border-purple-400 bg-purple-400/5' : 'text-[#64748b] hover:text-white border-b-2 border-transparent'}`}>
              {label}<span className={`text-[10px] px-1.5 py-0.5 rounded-full ${tab === t ? 'bg-purple-500/20 text-purple-300' : 'bg-[#1e293b] text-[#64748b]'}`}>{count}</span>
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto min-h-0">
          {loading ? <div className="flex items-center justify-center gap-2 py-16 text-[#64748b] text-xs"><Loader2 className="w-4 h-4 animate-spin" /> 加载中...</div>
           : filtered.length === 0 ? <div className="flex items-center justify-center py-16 text-[#64748b] text-xs">无匹配应用</div>
           : <div className="divide-y divide-[#1e293b]/50">
            {filtered.map(app => {
              const running = runningPkgs.has(app.package_name);
              const isSys = isSystemPkg(app.package_name);
              return (
                <div key={app.package_name} className="flex items-center gap-3 px-5 py-2.5 cursor-pointer hover:bg-[#1e293b]/60 transition-colors group" onClick={() => launch(app.package_name)}>
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${running ? 'bg-emerald-500/10' : 'bg-[#1e293b]'}`}>
                    <Package className={`w-4 h-4 ${running ? 'text-emerald-400' : 'text-[#475569]'}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="text-xs font-medium truncate text-white/90">{app.app_name || app.package_name}</div>
                      {running && <span className="flex-shrink-0 text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 font-medium">运行中</span>}
                    </div>
                    <div className="text-[10px] text-[#475569] truncate">{app.package_name}</div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                    {running && <button onClick={e => { e.stopPropagation(); stop(app.package_name); }}
                      className="p-1.5 rounded-lg hover:bg-amber-500/15 text-[#64748b] hover:text-amber-400 transition-colors" title="停止"><Power className="w-3.5 h-3.5" /></button>}
                    {!isSys && <button onClick={e => { e.stopPropagation(); uninstall(app.package_name); }}
                      className="p-1.5 rounded-lg hover:bg-red-500/15 text-[#64748b] hover:text-red-400 transition-colors" title="卸载"><Trash2 className="w-3.5 h-3.5" /></button>}
                    <div className={`px-2 py-1 rounded-lg text-[10px] font-medium flex items-center gap-1 ${running ? 'bg-[#1e293b] text-[#64748b] cursor-default' : 'bg-purple-500/15 text-purple-400 cursor-pointer hover:bg-purple-500/25'}`}>
                      {running ? <>已运行</> : <><Play className="w-3 h-3" /> 启动</>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>}
        </div>
        <div className="px-5 py-2.5 border-t border-[#1e293b]">
          <p className="text-[10px] text-[#475569]"><span className="text-amber-400/60">●</span> 运行中可停止 · <span className="text-red-400/60">●</span> 第三方可卸载</p>
        </div>
      </div>
    </div>
  );
}

// ---- Inline Input Popover ----
function InlineInput({ label, placeholder, value, onChange, onSubmit, onCancel, submitting }: {
  label: string; placeholder: string; value: string; onChange: (v: string) => void;
  onSubmit: () => void; onCancel: () => void; submitting: boolean;
}) {
  return (
    <div className="mx-2 mb-2 p-3 rounded-xl border border-[#1e293b] bg-[#0c0f1a] space-y-2">
      <span className="text-[11px] font-medium text-white/70">{label}</span>
      <div className="flex gap-2">
        <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className="flex-1 bg-[#131929] border border-[#1e293b] rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-[#475569] focus:outline-none focus:border-purple-500/50"
          onKeyDown={e => { if (e.key === 'Enter') onSubmit(); if (e.key === 'Escape') onCancel(); }} autoFocus />
        <button onClick={onSubmit} disabled={!value.trim() || submitting}
          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white text-xs rounded-lg transition-colors flex items-center gap-1">
          {submitting ? <Loader2 className="w-3 h-3 animate-spin" /> : null} 执行
        </button>
        <button onClick={onCancel} className="px-2.5 py-1.5 text-[#64748b] hover:text-white text-xs rounded-lg hover:bg-[#1e293b] transition-colors">取消</button>
      </div>
    </div>
  );
}

// ---- Op Section ----
function OpSection({ title, color, children }: { title: string; color: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="mb-1">
      <button onClick={() => setOpen(v => !v)} className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[#1e293b]/50 rounded-lg transition-colors group">
        <span className={`text-[11px] font-semibold ${color}`}>{title}</span>
        <ArrowRight className={`w-3 h-3 text-[#475569] transition-transform ml-auto group-hover:text-white ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && children}
    </div>
  );
}

// ---- Op Button ----
function OpBtn({ icon: Icon, label, color, bgColor, onClick, disabled }: {
  icon: React.ElementType; label: string; color: string; bgColor: string; onClick: () => void; disabled?: boolean;
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className={`h-12 rounded-xl border border-[#1e293b] flex flex-col items-center justify-center gap-1 transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed hover:border-current/20 ${bgColor}`}>
      <Icon className={`w-4 h-4 ${color}`} />
      <span className={`text-[10px] font-medium ${color}`}>{label}</span>
    </button>
  );
}

// ---- Main Page ----
function AutomationPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedSerial, setSelectedSerial] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastResult, setLastResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showAppSelector, setShowAppSelector] = useState(false);
  const [activeInput, setActiveInput] = useState<string | null>(null);
  const [textVal, setTextVal] = useState('');
  const [pkgVal, setPkgVal] = useState('');

  // 截图轮询：用于 ScrcpyPlayer fallback 模式下的画面实时更新
  const { screenshot: pollScreenshot, triggerRefresh } = useScreenshotPolling({
    deviceId,
    enabled: !!deviceId,
    pollDelayMs: 1200,
  });

  // Case editor state
  const [actions, setActions] = useState<RecordedAction[]>([]);
  const [editorTab, setEditorTab] = useState<'pytest' | 'yaml'>('pytest');
  const [codeText, setCodeText] = useState('');
  const [runResult, setRunResult] = useState<{ success: boolean; output: string } | null>(null);
  const [runningCode, setRunningCode] = useState(false);
  const [showEditor, setShowEditor] = useState(true);
  const [feedbackAnim, setFeedbackAnim] = useState<'tap' | 'swipe' | null>(null);
  const feedbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const triggerFeedback = (type: 'tap' | 'swipe') => {
    if (feedbackTimerRef.current) clearTimeout(feedbackTimerRef.current);
    setFeedbackAnim(type);
    feedbackTimerRef.current = setTimeout(() => setFeedbackAnim(null), 600);
  };

  // ---- Auto-sync codeText when actions or tab changes ----
  const syncCode = useCallback((tab: 'pytest' | 'yaml', currentActions: RecordedAction[], serial: string) => {
    setCodeText(tab === 'pytest' ? genPytest(currentActions, serial) : genYaml(currentActions, serial));
  }, []);

  const addAction = useCallback((type: ActionType, params: Record<string, unknown>, description: string) => {
    setActions(prev => {
      const next = [...prev, { id: `${type}-${Date.now()}`, type, params, description, ts: Date.now() }];
      // Auto-sync code
      setCodeText(prevCode => {
        // Only regenerate if code is currently empty or matches the old generated content
        // We always regenerate for safety
        const serial = selectedSerial || 'device';
        return editorTab === 'pytest' ? genPytest(next, serial) : genYaml(next, serial);
      });
      return next;
    });
  }, [selectedSerial, editorTab]);

  const _run = useCallback(async (fn: () => Promise<void>) => {
    if (!deviceId) { setLastResult({ success: false, message: '请先连接设备' }); return; }
    setIsLoading(true);
    try { await fn(); }
    catch (e) { setLastResult({ success: false, message: `操作失败: ${e}` }); }
    finally { setIsLoading(false); }
  }, [deviceId]);

  // All operations append actions on success
  const _tap = () => _run(async () => {
    const r = await sendTap(DEF_X, DEF_Y, deviceId);
    setLastResult({ success: r.success, message: r.success ? '点击成功' : `失败: ${r.error}` });
    if (r.success) addAction('tap', { x: DEF_X, y: DEF_Y }, `点击 (${DEF_X}, ${DEF_Y})`);
  });
  const _dbclick = () => _run(async () => {
    const r = await sendDoubleTap(DEF_X, DEF_Y, deviceId);
    setLastResult({ success: r.success, message: r.success ? '双击成功' : `失败: ${r.error}` });
    if (r.success) addAction('double_tap', { x: DEF_X, y: DEF_Y }, `双击 (${DEF_X}, ${DEF_Y})`);
  });
  const _longpress = () => _run(async () => {
    const r = await sendLongPress(DEF_X, DEF_Y, DEF_DUR, deviceId);
    setLastResult({ success: r.success, message: r.success ? '长按成功' : `失败: ${r.error}` });
    if (r.success) addAction('long_press', { x: DEF_X, y: DEF_Y, dur: DEF_DUR }, `长按 (${DEF_X}, ${DEF_Y})`);
  });
  const _swipeUp = () => _run(async () => {
    const r = await sendSwipe(DEF_X, DEF_Y + 200, DEF_X, DEF_Y - SWIPE_DIST, 300, deviceId);
    setLastResult({ success: r.success, message: r.success ? '上滑成功' : `失败: ${r.error}` });
    if (r.success) addAction('swipe', { sx: DEF_X, sy: DEF_Y + 200, ex: DEF_X, ey: DEF_Y - SWIPE_DIST, d: 300 }, '上滑');
  });
  const _swipeDown = () => _run(async () => {
    const r = await sendSwipe(DEF_X, DEF_Y - 200, DEF_X, DEF_Y + SWIPE_DIST, 300, deviceId);
    setLastResult({ success: r.success, message: r.success ? '下滑成功' : `失败: ${r.error}` });
    if (r.success) addAction('swipe', { sx: DEF_X, sy: DEF_Y - 200, ex: DEF_X, ey: DEF_Y + SWIPE_DIST, d: 300 }, '下滑');
  });
  const _swipeLeft = () => _run(async () => {
    const r = await sendSwipe(DEF_X + 200, DEF_Y, DEF_X - SWIPE_DIST, DEF_Y, 300, deviceId);
    setLastResult({ success: r.success, message: r.success ? '左滑成功' : `失败: ${r.error}` });
    if (r.success) addAction('swipe', { sx: DEF_X + 200, sy: DEF_Y, ex: DEF_X - SWIPE_DIST, ey: DEF_Y, d: 300 }, '左滑');
  });
  const _swipeRight = () => _run(async () => {
    const r = await sendSwipe(DEF_X - 200, DEF_Y, DEF_X + SWIPE_DIST, DEF_Y, 300, deviceId);
    setLastResult({ success: r.success, message: r.success ? '右滑成功' : `失败: ${r.error}` });
    if (r.success) addAction('swipe', { sx: DEF_X - 200, sy: DEF_Y, ex: DEF_X + SWIPE_DIST, ey: DEF_Y, d: 300 }, '右滑');
  });
  const _back = () => _run(async () => {
    const r = await sendBack(deviceId);
    setLastResult({ success: r.success, message: r.success ? '返回' : `失败: ${r.error}` });
    if (r.success) addAction('back', {}, '返回');
  });
  const _home = () => _run(async () => {
    const r = await sendHome(deviceId);
    setLastResult({ success: r.success, message: r.success ? '主页' : `失败: ${r.error}` });
    if (r.success) addAction('home', {}, '主页');
  });
  const _recent = () => _run(async () => {
    const r = await sendKeyEvent(187, deviceId);
    setLastResult({ success: r.success, message: r.success ? '最近任务' : `失败: ${r.error}` });
    if (r.success) addAction('keyevent', { keycode: 187 }, '最近任务');
  });
  const _power = () => _run(async () => {
    const r = await sendKeyEvent(26, deviceId);
    setLastResult({ success: r.success, message: r.success ? '电源' : `失败: ${r.error}` });
    if (r.success) addAction('keyevent', { keycode: 26 }, '电源键');
  });
  const _volUp = () => _run(async () => {
    const r = await sendKeyEvent(24, deviceId);
    setLastResult({ success: r.success, message: r.success ? '音量+' : `失败: ${r.error}` });
    if (r.success) addAction('keyevent', { keycode: 24 }, '音量+');
  });
  const _volDown = () => _run(async () => {
    const r = await sendKeyEvent(25, deviceId);
    setLastResult({ success: r.success, message: r.success ? '音量-' : `失败: ${r.error}` });
    if (r.success) addAction('keyevent', { keycode: 25 }, '音量-');
  });
  const _doText = () => _run(async () => {
    if (!textVal.trim()) { setLastResult({ success: false, message: '请输入文本' }); return; }
    const r = await sendTextInput(textVal, deviceId);
    setLastResult({ success: r.success, message: r.success ? '输入成功' : `失败: ${r.error}` });
    if (r.success) { addAction('input', { text: textVal }, `输入: ${textVal}`); setTextVal(''); setActiveInput(null); }
  });
  const _doPaste = () => _run(async () => {
    if (!textVal.trim()) { setLastResult({ success: false, message: '请输入内容' }); return; }
    const r = await sendTextInput(textVal, deviceId);
    setLastResult({ success: r.success, message: r.success ? '粘贴成功' : `失败: ${r.error}` });
    if (r.success) { addAction('input', { text: textVal }, `粘贴: ${textVal}`); setTextVal(''); setActiveInput(null); }
  });
  const _doStop = () => _run(async () => {
    if (!pkgVal.trim()) { setLastResult({ success: false, message: '请输入包名' }); return; }
    const r = await forceStopApp(pkgVal, deviceId);
    setLastResult({ success: r.success, message: r.success ? '已停止' : `失败: ${r.error}` });
    if (r.success) addAction('stop', { pkg: pkgVal }, `停止: ${pkgVal}`);
  });
  const _doLaunch = () => _run(async () => {
    if (!pkgVal.trim()) { setLastResult({ success: false, message: '请输入包名' }); return; }
    const r = await sendLaunchApp(pkgVal, deviceId);
    setLastResult({ success: r.success, message: r.success ? '已启动' : `失败: ${r.error}` });
    if (r.success) { addAction('launch', { pkg: pkgVal }, `启动: ${pkgVal}`); setPkgVal(''); setActiveInput(null); }
  });

  // Run code — always refresh before running
  const handleRunCode = async () => {
    const serial = selectedSerial || 'device';
    const freshCode = editorTab === 'pytest' ? genPytest(actions, serial) : genYaml(actions, serial);
    setCodeText(freshCode);
    if (!freshCode.trim()) return;
    setRunningCode(true);
    setRunResult(null);
    try {
      const r = editorTab === 'pytest'
        ? await runPytest(freshCode, 'test_auto.py')
        : await runYaml(freshCode, 'auto_test.yaml');
      setRunResult({ success: r.success, output: r.output || (r.success ? '执行成功' : '执行失败') });
      if (!r.success) setLastResult({ success: false, message: `运行失败: ${r.error}` });
      else setLastResult({ success: true, message: '用例执行成功' });
    } catch (e) { setRunResult({ success: false, output: String(e) }); }
    finally { setRunningCode(false); }
  };

  // Switch editor tab → regenerate code from current actions
  const handleTabSwitch = (tab: 'pytest' | 'yaml') => {
    setEditorTab(tab);
    const serial = selectedSerial || 'device';
    setCodeText(tab === 'pytest' ? genPytest(actions, serial) : genYaml(actions, serial));
  };

  // Delete action → regenerate code
  const deleteAction = useCallback((id: string) => {
    setActions(prev => {
      const next = prev.filter(a => a.id !== id);
      const serial = selectedSerial || 'device';
      setCodeText(editorTab === 'pytest' ? genPytest(next, serial) : genYaml(next, serial));
      return next;
    });
  }, [selectedSerial, editorTab]);

  // Load devices
  useEffect(() => {
    const load = async () => {
      try {
        const r = await listDevices();
        const connected = r.devices.filter((d: Device) => d.state !== 'disconnected');
        setDevices(connected);
        if (connected.length > 0 && !selectedSerial) {
          setSelectedSerial(connected[0].serial);
          setDeviceId(connected[0].id);
        }
      } catch (e) { console.error(e); }
    };
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, [selectedSerial]);

  // 截图轮询由 useScreenshotPolling 统一处理（见上方）

  const currentDevice = devices.find(d => d.serial === selectedSerial);
  const isHarmonyOS = currentDevice?.platform === 'harmonyos';

  const actionIcon = (type: ActionType) => {
    switch (type) {
      case 'tap': return <MousePointerClick className="w-3 h-3 text-blue-400" />;
      case 'double_tap': return <MousePointer2 className="w-3 h-3 text-cyan-400" />;
      case 'long_press': return <Hand className="w-3 h-3 text-violet-400" />;
      case 'swipe': return <ChevronRight className="w-3 h-3 text-emerald-400" />;
      case 'back': return <RotateCcw className="w-3 h-3 text-gray-400" />;
      case 'home': return <Square className="w-3 h-3 text-gray-400" />;
      case 'stop': return <Power className="w-3 h-3 text-amber-400" />;
      case 'input': return <Type className="w-3 h-3 text-yellow-400" />;
      case 'launch': return <Play className="w-3 h-3 text-purple-400" />;
      case 'keyevent': return <Terminal className="w-3 h-3 text-rose-400" />;
    }
  };

  return (
    <div className="flex bg-background" style={{ height: 'calc(100vh - 56px)' }}>
      {/* LEFT: Operations panel */}
      <div className="flex-shrink-0 border-r border-[#1e293b] overflow-y-auto" style={{ width: 264, background: '#0c0f1a' }}>
        <div className="px-4 py-3.5 border-b border-[#1e293b]">
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-xs font-semibold text-white/80">设备操作</span>
            {isHarmonyOS ? <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/20">HDC</span>
              : <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#1e293b] text-[#64748b] border border-[#1e293b]">ADB</span>}
          </div>
          {devices.length > 0 ? (
            <select value={selectedSerial}
              onChange={e => { setSelectedSerial(e.target.value); setDeviceId(devices.find(d => d.serial === e.target.value)?.id || ''); }}
              className="w-full bg-[#131929] border border-[#1e293b] rounded-lg px-2.5 py-1.5 text-xs text-white">
              {devices.map(d => <option key={d.id} value={d.serial}>{d.display_name || d.model || d.serial}</option>)}
            </select>
          ) : <div className="text-[11px] text-[#475569] text-center py-2 rounded-lg bg-[#131929] border border-[#1e293b]">未检测到设备</div>}
        </div>

        {/* App browser */}
        <div className="px-3 pt-3 pb-1">
          <button onClick={() => deviceId ? setShowAppSelector(true) : setLastResult({ success: false, message: '请先连接设备' })}
            className="w-full h-10 rounded-xl border border-purple-500/30 bg-purple-500/8 hover:bg-purple-500/15 active:scale-98 transition-all flex items-center justify-center gap-2 group">
            <Package className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-[11px] font-medium text-purple-300">浏览所有应用</span>
            <ArrowRight className="w-3 h-3 text-purple-400/50 ml-auto" />
          </button>
        </div>

        {/* Result toast */}
        {lastResult && (
          <div className="mx-3 mb-2 px-3 py-2 rounded-xl text-xs flex items-center gap-2" style={{
            background: lastResult.success ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
            color: lastResult.success ? '#6ee7b7' : '#fca5a5',
            border: `1px solid ${lastResult.success ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}`,
          }}>
            {lastResult.success ? <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />}
            <span className="flex-1 truncate">{lastResult.message}</span>
            <button onClick={() => setLastResult(null)} className="opacity-40 hover:opacity-80"><X className="w-3 h-3" /></button>
          </div>
        )}

        {/* Operations */}
        <div className="px-2 pb-3">
          <OpSection title="触控" color="text-blue-400">
            <div className="grid grid-cols-3 gap-1.5 px-1 pb-2">
              <OpBtn icon={MousePointerClick} label="点击" color="text-blue-400" bgColor="bg-blue-500/8 hover:bg-blue-500/15" onClick={_tap} disabled={isLoading} />
              <OpBtn icon={MousePointer2} label="双击" color="text-cyan-400" bgColor="bg-cyan-500/8 hover:bg-cyan-500/15" onClick={_dbclick} disabled={isLoading} />
              <OpBtn icon={Hand} label="长按" color="text-violet-400" bgColor="bg-violet-500/8 hover:bg-violet-500/15" onClick={_longpress} disabled={isLoading} />
            </div>
          </OpSection>
          <OpSection title="滑动" color="text-emerald-400">
            <div className="grid grid-cols-4 gap-1.5 px-1 pb-2">
              <OpBtn icon={ChevronUp} label="上滑" color="text-emerald-400" bgColor="bg-emerald-500/8 hover:bg-emerald-500/15" onClick={_swipeUp} disabled={isLoading} />
              <OpBtn icon={ChevronDown} label="下滑" color="text-emerald-400" bgColor="bg-emerald-500/8 hover:bg-emerald-500/15" onClick={_swipeDown} disabled={isLoading} />
              <OpBtn icon={ChevronLeft} label="左滑" color="text-emerald-400" bgColor="bg-emerald-500/8 hover:bg-emerald-500/15" onClick={_swipeLeft} disabled={isLoading} />
              <OpBtn icon={ChevronRight} label="右滑" color="text-emerald-400" bgColor="bg-emerald-500/8 hover:bg-emerald-500/15" onClick={_swipeRight} disabled={isLoading} />
            </div>
          </OpSection>
          <OpSection title="导航" color="text-[#94a3b8]">
            <div className="grid grid-cols-3 gap-1.5 px-1 pb-2">
              <OpBtn icon={RotateCcw} label="返回" color="text-[#94a3b8]" bgColor="bg-[#1e293b]/60 hover:bg-[#1e293b]" onClick={_back} disabled={isLoading} />
              <OpBtn icon={Square} label="主页" color="text-[#94a3b8]" bgColor="bg-[#1e293b]/60 hover:bg-[#1e293b]" onClick={_home} disabled={isLoading} />
              <OpBtn icon={Clock} label="最近" color="text-[#94a3b8]" bgColor="bg-[#1e293b]/60 hover:bg-[#1e293b]" onClick={_recent} disabled={isLoading} />
            </div>
          </OpSection>
          <OpSection title="系统" color="text-amber-400">
            <div className="grid grid-cols-3 gap-1.5 px-1 pb-2">
              <OpBtn icon={Power} label="电源" color="text-rose-400" bgColor="bg-rose-500/8 hover:bg-rose-500/15" onClick={_power} disabled={isLoading} />
              <OpBtn icon={Volume2} label="音量+" color="text-amber-400" bgColor="bg-amber-500/8 hover:bg-amber-500/15" onClick={_volUp} disabled={isLoading} />
              <OpBtn icon={VolumeX} label="音量-" color="text-amber-400" bgColor="bg-amber-500/8 hover:bg-amber-500/15" onClick={_volDown} disabled={isLoading} />
            </div>
          </OpSection>
          <OpSection title="输入" color="text-yellow-400">
            <div className="grid grid-cols-2 gap-1.5 px-1 pb-1">
              <button onClick={() => setActiveInput(activeInput === 'text' ? null : 'text')}
                className={`h-12 rounded-xl border flex flex-col items-center justify-center gap-1 transition-all active:scale-95 ${activeInput === 'text' ? 'border-yellow-400/40 bg-yellow-500/10' : 'border-[#1e293b] bg-[#1e293b]/40 hover:bg-[#1e293b] hover:border-yellow-400/20'}`}>
                <Type className="w-4 h-4 text-yellow-400" /><span className="text-[10px] font-medium text-yellow-400">文本输入</span>
              </button>
              <button onClick={() => setActiveInput(activeInput === 'paste' ? null : 'paste')}
                className={`h-12 rounded-xl border flex flex-col items-center justify-center gap-1 transition-all active:scale-95 ${activeInput === 'paste' ? 'border-orange-400/40 bg-orange-500/10' : 'border-[#1e293b] bg-[#1e293b]/40 hover:bg-[#1e293b] hover:border-orange-400/20'}`}>
                <ClipboardPaste className="w-4 h-4 text-orange-400" /><span className="text-[10px] font-medium text-orange-400">粘贴</span>
              </button>
            </div>
            {activeInput === 'text' && <InlineInput label="输入文本" placeholder="输入要发送的文本..." value={textVal} onChange={setTextVal} onSubmit={_doText} onCancel={() => { setActiveInput(null); setTextVal(''); }} submitting={isLoading} />}
            {activeInput === 'paste' && <InlineInput label="粘贴内容" placeholder="粘贴要输入的内容..." value={textVal} onChange={setTextVal} onSubmit={_doPaste} onCancel={() => { setActiveInput(null); setTextVal(''); }} submitting={isLoading} />}
          </OpSection>
          <OpSection title="应用" color="text-purple-400">
            <div className="grid grid-cols-2 gap-1.5 px-1 pb-1">
              <button onClick={() => setActiveInput(activeInput === 'launch' ? null : 'launch')}
                className={`h-12 rounded-xl border flex flex-col items-center justify-center gap-1 transition-all active:scale-95 ${activeInput === 'launch' ? 'border-purple-400/40 bg-purple-500/10' : 'border-[#1e293b] bg-[#1e293b]/40 hover:bg-[#1e293b] hover:border-purple-400/20'}`}>
                <Play className="w-4 h-4 text-purple-400" /><span className="text-[10px] font-medium text-purple-400">启动应用</span>
              </button>
              <button onClick={() => setActiveInput(activeInput === 'stop' ? null : 'stop')}
                className={`h-12 rounded-xl border flex flex-col items-center justify-center gap-1 transition-all active:scale-95 ${activeInput === 'stop' ? 'border-red-400/40 bg-red-500/10' : 'border-[#1e293b] bg-[#1e293b]/40 hover:bg-[#1e293b] hover:border-red-400/20'}`}>
                <Trash2 className="w-4 h-4 text-red-400" /><span className="text-[10px] font-medium text-red-400">终止应用</span>
              </button>
            </div>
            {activeInput === 'launch' && <InlineInput label="启动应用" placeholder="输入包名" value={pkgVal} onChange={setPkgVal} onSubmit={_doLaunch} onCancel={() => { setActiveInput(null); setPkgVal(''); }} submitting={isLoading} />}
            {activeInput === 'stop' && <InlineInput label="终止应用" placeholder="输入包名" value={pkgVal} onChange={setPkgVal} onSubmit={_doStop} onCancel={() => { setActiveInput(null); setPkgVal(''); }} submitting={isLoading} />}
          </OpSection>
        </div>
      </div>

      {/* CENTER: Cast / Device preview with mouse control */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0" style={{ background: '#080b12' }}>
        <div className="flex items-center justify-between px-4 flex-shrink-0" style={{ height: 44, borderBottom: '1px solid #1e293b', background: '#0c0f1a' }}>
          <div className="flex items-center gap-2">
            <Monitor className="w-3.5 h-3.5 text-[#64748b]" />
            <span className="text-xs text-[#64748b]">设备投屏</span>
            {actions.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/20">{actions.length} 个动作</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {currentDevice && <span className="text-[11px] text-[#475569]">{currentDevice.model || currentDevice.serial}</span>}
            <button onClick={() => { setActions([]); setCodeText(''); setRunResult(null); setLastResult(null); }}
              className="text-[10px] text-[#475569] hover:text-white px-2 py-1 rounded-lg hover:bg-[#1e293b] transition-colors"
              disabled={actions.length === 0}>清空记录</button>
            <button onClick={() => { setShowEditor(true); }}
              className="text-[10px] px-2.5 py-1 rounded-lg bg-purple-600/80 hover:bg-purple-600 text-white transition-colors flex items-center gap-1">
              <Code2 className="w-3 h-3" /> 用例编辑
            </button>
          </div>
        </div>

        {/* Cast area */}
        <div className="flex-1 flex items-center justify-center overflow-hidden relative">
          {!deviceId ? (
            <div className="text-center">
              <Smartphone className="w-20 h-20 mx-auto mb-4 text-[#1e293b]" />
              <p className="text-sm text-[#1e293b]">等待设备连接...</p>
            </div>
          ) : (
            <>
              <ScrcpyPlayer
                deviceId={deviceId}
                className="w-full h-full"
                enableControl={true}
                fallbackScreenshot={pollScreenshot?.success ? pollScreenshot.image : null}
                onTapSuccess={(x, y) => {
                  triggerFeedback('tap');
                  addAction('tap', { x, y }, `点击 (${x}, ${y})`);
                  setLastResult({ success: true, message: `✓ 点击 (${x}, ${y})` });
                }}
                onTapError={err => setLastResult({ success: false, message: `✗ 点击失败: ${err}` })}
                onSwipeSuccess={(sx, sy, ex, ey) => {
                  triggerFeedback('swipe');
                  addAction('swipe', { sx, sy, ex, ey, d: 300 }, `滑动 (${sx},${sy}) → (${ex},${ey})`);
                  setLastResult({ success: true, message: `✓ 滑动完成` });
                }}
                onSwipeError={err => setLastResult({ success: false, message: `✗ 滑动失败: ${err}` })}
                onControlAction={triggerRefresh}
                isVisible={true}
              />
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-3 z-20">
                <button onClick={_home}
                  className="h-10 w-10 rounded-full bg-black/70 backdrop-blur border border-white/10 shadow-lg hover:bg-white/20 text-white flex items-center justify-center transition-colors">
                  <Square className="w-4 h-4" />
                </button>
                <button onClick={_back}
                  className="h-10 w-10 rounded-full bg-black/70 backdrop-blur border border-white/10 shadow-lg hover:bg-white/20 text-white flex items-center justify-center transition-colors">
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>

              {/* Tap/swipe visual feedback */}
              {feedbackAnim === 'tap' && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-30">
                  <div className="w-16 h-16 rounded-full border-2 border-white/60 animate-[ping_0.5s_ease-out]" />
                </div>
              )}
              {feedbackAnim === 'swipe' && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-30">
                  <div className="w-10 h-10 rounded-full border-2 border-emerald-400/70 animate-[ping_0.5s_ease-out]" />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* RIGHT: Case editor panel */}
      {showEditor && (
        <div className="flex-shrink-0 border-l border-[#1e293b] flex flex-col overflow-hidden" style={{ width: 380, background: '#0c0f1a' }}>
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-[#1e293b] flex-shrink-0">
            <div className="flex items-center gap-2">
              <ScrollText className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-xs font-semibold text-white/80">用例编辑器</span>
              {actions.length > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">{actions.length} 步</span>}
            </div>
            <button onClick={() => setShowEditor(false)} className="p-1 hover:bg-[#1e293b] rounded text-[#64748b] hover:text-white"><X className="w-3.5 h-3.5" /></button>
          </div>

          {/* Action list */}
          <div className="border-b border-[#1e293b] flex-shrink-0" style={{ maxHeight: 180 }}>
            <div className="px-3 py-1.5 flex items-center justify-between">
              <span className="text-[10px] text-[#475569]">操作记录</span>
              {actions.length > 0 && (
                <button onClick={() => { setActions([]); setCodeText(''); setRunResult(null); }}
                  className="text-[10px] text-red-400/60 hover:text-red-400 transition-colors">清空</button>
              )}
            </div>
            <div className="overflow-y-auto" style={{ maxHeight: 140 }}>
              {actions.length === 0 ? (
                <div className="text-center py-4 text-[10px] text-[#475569]">点击投屏或上方按钮录制操作</div>
              ) : (
                actions.map((a, i) => (
                  <div key={a.id} className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#1e293b]/50 group transition-colors">
                    <span className="text-[10px] text-[#475569] w-4 flex-shrink-0 text-right">{i + 1}</span>
                    {actionIcon(a.type)}
                    <span className="flex-1 text-[11px] text-white/70 truncate">{a.description}</span>
                    <button onClick={() => deleteAction(a.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-red-500/20 rounded text-red-400/50 hover:text-red-400">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Code area */}
          <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
            {/* Tab bar */}
            <div className="flex items-center gap-1 px-2 py-1.5 border-b border-[#1e293b] flex-shrink-0">
              <button onClick={() => handleTabSwitch('pytest')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${editorTab === 'pytest' ? 'bg-purple-600 text-white' : 'text-[#64748b] hover:text-white hover:bg-[#1e293b]'}`}>
                <FileCode className="w-3 h-3" /> Pytest
              </button>
              <button onClick={() => handleTabSwitch('yaml')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${editorTab === 'yaml' ? 'bg-emerald-600 text-white' : 'text-[#64748b] hover:text-white hover:bg-[#1e293b]'}`}>
                <FileText className="w-3 h-3" /> YAML
              </button>
              <button onClick={() => { const s = selectedSerial || 'device'; setCodeText(editorTab === 'pytest' ? genPytest(actions, s) : genYaml(actions, s)); }}
                className="ml-auto text-[10px] text-[#475569] hover:text-white px-2 py-1 rounded-lg hover:bg-[#1e293b] transition-colors flex items-center gap-1">
                <Terminal className="w-3 h-3" /> 刷新
              </button>
            </div>

            {/* Code textarea */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <textarea
                value={codeText}
                onChange={e => setCodeText(e.target.value)}
                className="w-full h-full bg-[#0a0e1a] text-[#cdd6f4] p-3 text-[11px] font-mono resize-none focus:outline-none leading-relaxed"
                spellCheck={false}
                placeholder="生成代码或直接编辑..."
              />
            </div>

            {/* Action bar */}
            <div className="px-2 py-2 border-t border-[#1e293b] flex items-center gap-1.5 flex-shrink-0">
              <button onClick={handleRunCode} disabled={!codeText.trim() || runningCode}
                className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-xs rounded-lg transition-colors">
                {runningCode ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                一键运行
              </button>
              <button onClick={() => { if (codeText.trim()) { navigator.clipboard.writeText(codeText); setLastResult({ success: true, message: '已复制到剪贴板' }); } }}
                className="flex items-center gap-1 px-2.5 py-1.5 border border-[#1e293b] hover:border-[#3e5068] text-[#64748b] hover:text-white text-xs rounded-lg transition-colors">
                <Copy className="w-3 h-3" /> 复制
              </button>
              <button onClick={() => { setCodeText(''); setRunResult(null); }}
                className="flex items-center gap-1 px-2.5 py-1.5 border border-[#1e293b] hover:border-[#3e5068] text-[#64748b] hover:text-white text-xs rounded-lg transition-colors">
                清空
              </button>
              {runResult && (
                <span className={`ml-auto text-[10px] px-2 py-1 rounded-lg ${runResult.success ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
                  {runResult.success ? <><CheckCircle2 className="w-3 h-3 inline" /> 成功</> : <><AlertCircle className="w-3 h-3 inline" /> 失败</>}
                </span>
              )}
            </div>

            {/* Run output */}
            {runResult && (
              <div className={`flex-shrink-0 max-h-32 overflow-y-auto px-3 py-2 text-[10px] font-mono border-t ${runResult.success ? 'bg-emerald-500/5 text-emerald-300 border-emerald-500/10' : 'bg-red-500/5 text-red-300 border-red-500/10'}`}>
                <pre className="whitespace-pre-wrap break-all">{runResult.output}</pre>
              </div>
            )}
          </div>
        </div>
      )}

      {showAppSelector && deviceId && (
        <AppSelectorDialog
          deviceId={deviceId}
          onLaunch={pkg => { addAction('launch', { pkg }, `启动: ${pkg}`); setLastResult({ success: true, message: `已启动: ${pkg}` }); }}
          onClose={() => setShowAppSelector(false)}
        />
      )}
    </div>
  );
}
