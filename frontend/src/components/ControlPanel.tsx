import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  ArrowLeft, ArrowUp, ArrowDown, ArrowLeftIcon, ArrowRightIcon,
  Home, Copy, ClipboardPaste, ListChecks, Trash2, Loader2,
  Camera, FileSearch, Smartphone, Play, Search, X, Film,
  Volume2, VolumeX, Power, RefreshCw, AppWindow, Monitor,
  SmartphoneIcon, RotateCcw, MousePointer2, Edit3, Maximize2,
  Minimize2, Square, CircleDot, Settings, Keyboard, Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  sendBack, sendHome, sendDoubleTap, sendLongPress, sendClearText,
  sendScroll, getControlScreenshot, getUiDump, getCurrentApp,
  sendPaste, sendSelectAll, sendLaunchApp, startScreenRecord, stopScreenRecord,
  sendKeyEvent, sendTap, getInstalledApps,
  type ScreenshotControlResponse, type UiDumpResponse,
  type InstalledAppsResponse, type InstalledAppInfo,
} from '../api';
import { ScrcpyPlayer } from './ScrcpyPlayer';
import { useScreenshotPolling } from '../hooks/useScreenshotPolling';

interface OperationLog {
  id: string;
  time: string;
  action: string;
  params: string;
  status: 'success' | 'error';
  duration?: number;
}

interface RecordedAction {
  id: string;
  type: 'tap' | 'swipe' | 'input' | 'keyevent' | 'launch' | 'double_tap' | 'long_press' | 'scroll';
  timestamp: number;
  params: Record<string, unknown>;
  description: string;
  screenWidth: number;
  screenHeight: number;
}

interface ControlPanelProps {
  deviceId: string;
  deviceName: string;
  deviceSerial?: string;
}

// 操作项分组
const CONTROL_GROUPS = [
  {
    title: '📸 截图与分析',
    color: 'text-blue-600',
    items: [
      { id: 'screenshot', label: '截图', icon: Camera },
      { id: 'ui_dump', label: 'UI分析', icon: FileSearch },
      { id: 'current_app', label: '当前App', icon: Smartphone },
    ],
  },
  {
    title: '🔙 导航操作',
    color: 'text-emerald-600',
    items: [
      { id: 'back', label: '返回', icon: ArrowLeft },
      { id: 'home', label: '主页', icon: Home },
      { id: 'recent', label: '最近任务', icon: AppWindow },
    ],
  },
  {
    title: '👆 触控操作',
    color: 'text-purple-600',
    items: [
      { id: 'tap', label: '点击', icon: MousePointer2 },
      { id: 'double_tap', label: '双击', icon: CircleDot },
      { id: 'long_press', label: '长按', icon: Square },
    ],
  },
  {
    title: '🔄 滑动操作',
    color: 'text-orange-600',
    items: [
      { id: 'swipe_up', label: '上滑', icon: ArrowUp },
      { id: 'swipe_down', label: '下滑', icon: ArrowDown },
      { id: 'swipe_left', label: '左滑', icon: ArrowLeftIcon },
      { id: 'swipe_right', label: '右滑', icon: ArrowRightIcon },
    ],
  },
  {
    title: '⌨️ 文本输入',
    color: 'text-amber-600',
    items: [
      { id: 'text', label: '输入文本', icon: Edit3 },
      { id: 'paste', label: '粘贴', icon: ClipboardPaste },
      { id: 'select_all', label: '全选', icon: ListChecks },
      { id: 'clear', label: '清除', icon: Trash2 },
    ],
  },
  {
    title: '⚙️ 系统控制',
    color: 'text-red-600',
    items: [
      { id: 'volume_up', label: '音量+', icon: Volume2 },
      { id: 'volume_down', label: '音量-', icon: VolumeX },
      { id: 'power', label: '电源', icon: Power },
    ],
  },
];

// 生成 pytest 代码
function genPytestCode(actions: RecordedAction[], serial: string): string {
  const deviceId = serial || 'your_device_serial';
  let code = `"""Auto-generated device control test."""
import subprocess, time

DEVICE_ID = "${deviceId}"

def adb(cmd):
    subprocess.run(["adb", "-s", DEVICE_ID, "shell", cmd], check=True)

def tap(x, y):
    adb(f"input tap {x} {y}")
    time.sleep(0.8)

def swipe(sx, sy, ex, ey, d=300):
    adb(f"input swipe {sx} {sy} {ex} {ey} {d}")
    time.sleep(0.8)

def back():
    adb("input keyevent 4")
    time.sleep(0.5)

def home():
    adb("input keyevent 3")
    time.sleep(0.5)

def text(t):
    adb(f'input text "{t}"')
    time.sleep(0.5)


def test_main():
    # 在此编写测试步骤
`;
  actions.forEach((a, i) => {
    switch (a.type) {
      case 'tap':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    tap(${a.params.x}, ${a.params.y})\n`;
        break;
      case 'swipe':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    swipe(${a.params.sx}, ${a.params.sy}, ${a.params.ex}, ${a.params.ey}, ${a.params.d || 300})\n`;
        break;
      case 'keyevent':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    adb("input keyevent ${a.params.keycode}")\n`;
        break;
      case 'input':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    text("${a.params.text}")\n`;
        break;
      case 'scroll':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    swipe(${a.params.sx}, ${a.params.sy}, ${a.params.ex}, ${a.params.ey}, ${a.params.d || 300})\n`;
        break;
      case 'double_tap':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    tap(${a.params.x}, ${a.params.y})\n`;
        code += `    time.sleep(0.1)\n`;
        code += `    tap(${a.params.x}, ${a.params.y})\n`;
        break;
      case 'long_press':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    swipe(${a.params.x}, ${a.params.y}, ${a.params.x}, ${a.params.y}, 3000)\n`;
        break;
      case 'launch':
        code += `    # Step ${i + 1}: ${a.description}\n`;
        code += `    adb("am start -n ${a.params.package}/.MainActivity")\n`;
        break;
    }
  });
  if (actions.length === 0) {
    code += `    tap(540, 960)\n`;
    code += `    time.sleep(1)\n`;
  }
  return code;
}

// 生成 yml 代码
function genYamlCode(actions: RecordedAction[]): string {
  let yaml = `# AutoGLM 自动化用例配置
name: 示例用例
description: 设备自动化测试

steps:
`;
  actions.forEach((a) => {
    switch (a.type) {
      case 'tap':
        yaml += `  - action: tap
    x: ${a.params.x}
    y: ${a.params.y}
    description: ${a.description}

`;
        break;
      case 'swipe':
        yaml += `  - action: swipe
    start_x: ${a.params.sx}
    start_y: ${a.params.sy}
    end_x: ${a.params.ex}
    end_y: ${a.params.ey}
    duration: ${a.params.d || 300}
    description: ${a.description}

`;
        break;
      case 'keyevent':
        yaml += `  - action: keyevent
    keycode: ${a.params.keycode}
    description: ${a.description}

`;
        break;
      case 'input':
        yaml += `  - action: text
    content: "${a.params.text}"
    description: ${a.description}

`;
        break;
      case 'scroll':
        yaml += `  - action: swipe
    start_x: ${a.params.sx}
    start_y: ${a.params.sy}
    end_x: ${a.params.ex}
    end_y: ${a.params.ey}
    duration: ${a.params.d || 300}
    description: ${a.description}

`;
        break;
      case 'double_tap':
        yaml += `  - action: double_tap
    x: ${a.params.x}
    y: ${a.params.y}
    description: ${a.description}

`;
        break;
      case 'long_press':
        yaml += `  - action: long_press
    x: ${a.params.x}
    y: ${a.params.y}
    duration: 3000
    description: ${a.description}

`;
        break;
      case 'launch':
        yaml += `  - action: launch
    package: "${a.params.package}"
    description: ${a.description}

`;
        break;
    }
  });
  if (actions.length === 0) {
    yaml += `  - action: tap
    x: 540
    y: 960
    description: 点击屏幕中心

`;
  }
  return yaml;
}

// 生成代码（操作日志映射）
function generateCode(log: OperationLog): string {
  const codeMap: Record<string, string> = {
    '截图': 'device.screenshot()',
    '返回': 'device.press("back")',
    '主页': 'device.press("home")',
    '最近任务': 'device.press("recent")',
    '双击': 'device.double_tap(540, 960)',
    '长按': 'device.long_press(540, 960, 3000)',
    '上滑': 'device.swipe(540, 1500, 540, 500)',
    '下滑': 'device.swipe(540, 500, 540, 1500)',
    '左滑': 'device.swipe(900, 960, 100, 960)',
    '右滑': 'device.swipe(100, 960, 900, 960)',
    '粘贴': 'device.paste()',
    '全选': 'device.select_all()',
    '清除': 'device.clear_text()',
    '音量+': 'device.press("volume_up")',
    '音量-': 'device.press("volume_down")',
    '电源': 'device.press("power")',
    '点击': 'device.tap(540, 960)',
  };
  return codeMap[log.action] || `# ${log.action}`;
}

export function ControlPanel({ deviceId, deviceName, deviceSerial }: ControlPanelProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [currentApp, setCurrentApp] = useState<string>('');
  const [operationLogs, setOperationLogs] = useState<OperationLog[]>([]);
  const [generatedCode, setGeneratedCode] = useState<string[]>([]);
  const [showApps, setShowApps] = useState(false);
  const [showElements, setShowElements] = useState(false);
  const [uiElements, setUiElements] = useState<UiDumpResponse | null>(null);
  const [apps, setApps] = useState<InstalledAppsResponse | null>(null);
  const [appTab, setAppTab] = useState<'third_party' | 'system'>('third_party');
  const [appSearch, setAppSearch] = useState('');
  const [textInput, setTextInput] = useState('');
  const [showTextInput, setShowTextInput] = useState(false);
  const [showCode, setShowCode] = useState(true);
  const [tapFeedback, setTapFeedback] = useState<{ x: number; y: number } | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [editorTab, setEditorTab] = useState<'pytest' | 'yml'>('pytest');
  const [pytestCode, setPytestCode] = useState('');
  const [ymlCode, setYmlCode] = useState('');

  const logContainerRef = useRef<HTMLDivElement>(null);
  const screenRef = useRef<{ width: number; height: number }>({ width: 1080, height: 1920 });

  // 操作录制列表
  const [recordedActions, setRecordedActions] = useState<RecordedAction[]>([]);

  // 截图轮询 - 用于设备实时同步
  const { screenshot, triggerRefresh } = useScreenshotPolling({
    deviceId,
    enabled: true,
    pollDelayMs: 1200,
  });

  // 每当有操作记录变化，同步更新右侧编辑器代码
  useEffect(() => {
    if (recordedActions.length === 0) {
      setPytestCode(genPytestCode([], deviceSerial || ''));
      setYmlCode(genYamlCode([]));
      return;
    }
    setPytestCode(genPytestCode(recordedActions, deviceSerial || ''));
    setYmlCode(genYamlCode(recordedActions));
  }, [recordedActions, deviceSerial]);

  // 记录操作到录制列表
  const recordAction = useCallback((
    type: RecordedAction['type'],
    params: Record<string, unknown>,
    description: string
  ) => {
    setRecordedActions(prev => [
      ...prev,
      {
        id: `${type}-${Date.now()}`,
        type,
        timestamp: Date.now(),
        params,
        description,
        screenWidth: screenRef.current.width,
        screenHeight: screenRef.current.height,
      },
    ]);
  }, []);

  // 添加操作日志
  const addLog = useCallback((action: string, params: string = '', status: 'success' | 'error' = 'success', duration?: number) => {
    const now = new Date();
    const time = now.toLocaleTimeString('zh-CN', { hour12: false });
    const log: OperationLog = { id: `${Date.now()}`, time, action, params, status, duration };
    setOperationLogs(prev => [...prev.slice(-99), log]);
    setGeneratedCode(prev => [...prev.slice(-99), generateCode(log)]);
    setTimeout(() => {
      if (logContainerRef.current) logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }, 50);
  }, []);

  // 执行操作（带录制）
  const exec = useCallback(async (
    label: string,
    fn: () => Promise<void>,
    params: string = '',
    recordInfo?: { type: RecordedAction['type']; actionParams: Record<string, unknown>; description: string }
  ) => {
    setLoading(label);
    const start = Date.now();
    try {
      await fn();
      addLog(label, params, 'success', Date.now() - start);
      if (recordInfo) {
        recordAction(recordInfo.type, recordInfo.actionParams, recordInfo.description);
      }
      // 操作完成后刷新截图，实现设备实时同步
      triggerRefresh();
    } catch (e) {
      addLog(label, params, 'error');
    } finally {
      setLoading(null);
    }
  }, [addLog, recordAction, triggerRefresh]);

  // 点击投屏成功回调
  const handleTapSuccess = useCallback((x?: number, y?: number) => {
    if (x !== undefined && y !== undefined) {
      addLog('点击', `(${x}, ${y})`);
      recordAction('tap', { x, y }, `点击 (${x}, ${y})`);
      setTapFeedback({ x, y });
      setTimeout(() => setTapFeedback(null), 500);
      // 触发截图刷新，实现设备实时同步
      triggerRefresh();
    }
  }, [addLog, recordAction, triggerRefresh]);

  // 滑动成功回调
  const handleSwipeSuccess = useCallback((sx: number, sy: number, ex: number, ey: number) => {
    addLog('滑动', `(${sx},${sy})→(${ex},${ey})`);
    recordAction('swipe', { sx, sy, ex, ey, d: 300 }, `滑动 (${sx},${sy})→(${ex},${ey})`);
    triggerRefresh();
  }, [addLog, recordAction, triggerRefresh]);

  // 执行操作
  const handleAction = (actionId: string) => {
    switch (actionId) {
      case 'screenshot':
        exec('截图', async () => {
          const r = await getControlScreenshot(deviceId);
          if (r.success) console.log('Screenshot:', r.width, r.height);
        });
        break;
      case 'ui_dump':
        exec('UI分析', async () => {
          const r = await getUiDump(deviceId);
          if (r.success) { setUiElements(r); setShowElements(true); }
        });
        break;
      case 'current_app':
        exec('当前App', async () => {
          const r = await getCurrentApp(deviceId);
          if (r.success) setCurrentApp(r.app_name || '未知');
        });
        break;
      case 'back':
        exec('返回', () => sendBack(deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 4 }, description: '返回键' });
        break;
      case 'home':
        exec('主页', () => sendHome(deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 3 }, description: 'Home键' });
        break;
      case 'recent':
        exec('最近任务', () => sendKeyEvent(187, deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 187 }, description: '最近任务键' });
        break;
      case 'double_tap':
        exec('双击', () => sendDoubleTap(540, 960, deviceId).then(() => {}), '', { type: 'double_tap', actionParams: { x: 540, y: 960 }, description: '双击 (540, 960)' });
        break;
      case 'long_press':
        exec('长按', () => sendLongPress(540, 960, 3000, deviceId).then(() => {}), '', { type: 'long_press', actionParams: { x: 540, y: 960 }, description: '长按 (540, 960)' });
        break;
      case 'swipe_up':
        exec('上滑', () => sendScroll('up', 500, deviceId).then(() => {}), '', { type: 'scroll', actionParams: { sx: 540, sy: 1500, ex: 540, ey: 500, d: 300 }, description: '上滑' });
        break;
      case 'swipe_down':
        exec('下滑', () => sendScroll('down', 500, deviceId).then(() => {}), '', { type: 'scroll', actionParams: { sx: 540, sy: 500, ex: 540, ey: 1500, d: 300 }, description: '下滑' });
        break;
      case 'swipe_left':
        exec('左滑', () => sendScroll('left', 500, deviceId).then(() => {}), '', { type: 'scroll', actionParams: { sx: 900, sy: 960, ex: 100, ey: 960, d: 300 }, description: '左滑' });
        break;
      case 'swipe_right':
        exec('右滑', () => sendScroll('right', 500, deviceId).then(() => {}), '', { type: 'scroll', actionParams: { sx: 100, sy: 960, ex: 900, ey: 960, d: 300 }, description: '右滑' });
        break;
      case 'paste':
        exec('粘贴', () => sendPaste(deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 277 }, description: '粘贴' });
        break;
      case 'select_all':
        exec('全选', () => sendSelectAll(deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 278 }, description: '全选' });
        break;
      case 'clear':
        exec('清除', () => sendClearText(deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 67 }, description: '清除文本' });
        break;
      case 'volume_up':
        exec('音量+', () => sendKeyEvent(24, deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 24 }, description: '音量+' });
        break;
      case 'volume_down':
        exec('音量-', () => sendKeyEvent(25, deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 25 }, description: '音量-' });
        break;
      case 'power':
        exec('电源', () => sendKeyEvent(26, deviceId).then(() => {}), '', { type: 'keyevent', actionParams: { keycode: 26 }, description: '电源键' });
        break;
      case 'text':
        if (textInput.trim()) {
          const inputText = textInput;
          exec('输入', async () => {
            const { sendTextInput } = await import('../api');
            await sendTextInput(inputText, deviceId);
            setTextInput('');
            setShowTextInput(false);
          }, inputText, { type: 'input', actionParams: { text: inputText }, description: `输入 "${inputText}"` });
        }
        break;
    }
  };

  // 录屏控制
  const handleRecord = async () => {
    if (isRecording) {
      await stopScreenRecord(deviceId);
      setIsRecording(false);
      addLog('停止录屏');
    } else {
      await startScreenRecord(deviceId);
      setIsRecording(true);
      addLog('开始录屏');
    }
  };

  // 加载应用列表
  const handleLoadApps = () => exec('获取应用', async () => {
    const r = await getInstalledApps(deviceId);
    if (r.success) { setApps(r); setShowApps(true); }
  });

  // 启动应用
  const handleLaunchPkg = (pkg: string) => exec('启动', () => sendLaunchApp(pkg, deviceId).then(() => {}), pkg, { type: 'launch', actionParams: { package: pkg }, description: `启动 ${pkg}` });

  // 复制代码
  const copyCode = () => {
    const code = editorTab === 'pytest' ? pytestCode : ymlCode;
    navigator.clipboard.writeText(code);
  };

  // 清除日志
  const clearLogs = () => {
    setOperationLogs([]);
    setGeneratedCode([]);
    setRecordedActions([]);
    setPytestCode(genPytestCode([], deviceSerial || ''));
    setYmlCode(genYamlCode([]));
  };

  const filteredApps = apps?.[appTab]?.filter((a: InstalledAppInfo) =>
    !appSearch || a.package_name.toLowerCase().includes(appSearch.toLowerCase()) ||
    (a.app_name?.toLowerCase().includes(appSearch.toLowerCase()))
  ) || [];

  return (
    <div className="flex h-full bg-background">
      {/* 左侧：实时投屏区域 */}
      <div className="flex-1 flex flex-col border-r">
        {/* 投屏头部 */}
        <div className="flex items-center justify-between px-4 py-2 bg-card border-b">
          <div className="flex items-center gap-3">
            <Monitor className="w-5 h-5 text-primary" />
            <span className="font-medium">实时投屏</span>
            <Badge variant="outline" className="text-xs">点击画面直接控制</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant={isRecording ? "destructive" : "outline"}
              className="gap-1"
              onClick={handleRecord}
            >
              <Film className={`w-4 h-4 ${isRecording ? 'animate-pulse' : ''}`} />
              {isRecording ? '停止录屏' : '开始录屏'}
            </Button>
          </div>
        </div>

        {/* 投屏画面 */}
        <div className="flex-1 relative bg-zinc-950 overflow-hidden flex items-center justify-center">
          <ScrcpyPlayer
            deviceId={deviceId}
            enableControl={true}
            onTapSuccess={handleTapSuccess}
            onSwipeSuccess={handleSwipeSuccess}
            onControlAction={triggerRefresh}
            isVisible={true}
            onScreenInfo={info => {
              screenRef.current = { width: info.width, height: info.height };
            }}
            fallbackScreenshot={screenshot?.success ? screenshot.image : null}
            className="w-full h-full max-w-full max-h-full object-contain"
          />
          {/* 点击反馈 */}
          {tapFeedback && (
            <div
              className="absolute pointer-events-none transition-all duration-300"
              style={{
                left: `${(tapFeedback.x / 1080) * 100}%`,
                top: `${(tapFeedback.y / 1920) * 100}%`,
              }}
            >
              <div className="w-10 h-10 rounded-full border-2 border-red-500 bg-red-500/30 animate-ping" />
            </div>
          )}
        </div>

        {/* 快捷操作栏 */}
        <div className="flex items-center justify-center gap-2 p-2 border-t bg-card">
          <Button size="sm" variant="outline" className="gap-1" onClick={() => handleAction('back')}>
            <ArrowLeft className="w-4 h-4" /> 返回
          </Button>
          <Button size="sm" variant="outline" className="gap-1" onClick={() => handleAction('home')}>
            <Home className="w-4 h-4" /> 主页
          </Button>
          <Button size="sm" variant="outline" className="gap-1 text-blue-600" onClick={() => handleAction('swipe_up')}>
            <ArrowUp className="w-4 h-4" /> 上滑
          </Button>
          <Button size="sm" variant="outline" className="gap-1 text-green-600" onClick={() => handleAction('swipe_down')}>
            <ArrowDown className="w-4 h-4" /> 下滑
          </Button>
          <Button size="sm" variant="outline" className="gap-1" onClick={() => handleAction('screenshot')}>
            <Camera className="w-4 h-4" /> 截图
          </Button>
        </div>
      </div>

      {/* 右侧：操作控制面板 */}
      <div className="w-80 flex-shrink-0 flex flex-col bg-card">
        {/* 设备信息头部 */}
        <div className="p-3 border-b bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Smartphone className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{deviceName}</p>
              <p className="text-xs text-muted-foreground truncate">{currentApp || '未获取当前应用'}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleAction('current_app')}
              disabled={loading !== null}
            >
              <RefreshCw className={`w-4 h-4 ${loading === '当前App' ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* 操作分组 */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {CONTROL_GROUPS.map(group => (
            <div key={group.title} className="space-y-2">
              <div className={`text-xs font-semibold ${group.color}`}>
                {group.title}
              </div>
              <div className={`grid gap-1 ${group.items.length <= 3 ? 'grid-cols-3' : 'grid-cols-4'}`}>
                {group.items.map(item => {
                  const Icon = item.icon;
                  const isLoading = loading === item.label;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleAction(item.id)}
                      disabled={loading !== null}
                      className="flex flex-col items-center justify-center gap-1 p-2 rounded-lg border border-border bg-background hover:bg-accent hover:border-primary/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Icon className="w-4 h-4 text-foreground" />
                      )}
                      <span className="text-[10px] text-foreground text-center leading-tight">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {/* 文本输入 */}
          {showTextInput && (
            <div className="space-y-2 pt-2 border-t">
              <div className="text-xs font-semibold text-foreground">📝 文本输入</div>
              <div className="flex gap-1">
                <Input
                  value={textInput}
                  onChange={e => setTextInput(e.target.value)}
                  placeholder="输入文本..."
                  className="h-8 text-xs"
                  onKeyDown={e => { if (e.key === 'Enter') handleAction('text'); }}
                />
                <Button size="sm" className="h-8 px-2" onClick={() => handleAction('text')} disabled={!textInput.trim()}>
                  发送
                </Button>
              </div>
            </div>
          )}

          {/* 其他功能按钮 */}
          <div className="pt-2 border-t space-y-1">
            <Button
              variant="outline"
              className="w-full justify-start text-xs h-8 gap-2"
              onClick={() => setShowTextInput(!showTextInput)}
            >
              <Edit3 className="w-3 h-3" />
              {showTextInput ? '隐藏输入框' : '显示文本输入'}
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start text-xs h-8 gap-2"
              onClick={handleLoadApps}
            >
              <SmartphoneIcon className="w-3 h-3" />
              应用管理
            </Button>
          </div>
        </div>

        {/* 操作日志 */}
        <div className="flex flex-col h-48 border-t">
          <div className="flex items-center justify-between px-3 py-1.5 bg-muted/50">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium">操作日志</span>
              <Badge variant="secondary" className="text-[10px]">{operationLogs.length}</Badge>
            </div>
            <Button variant="ghost" size="sm" className="h-5 text-[10px]" onClick={clearLogs}>
              <Trash2 className="w-3 h-3 mr-0.5" />
              清空
            </Button>
          </div>
          <div ref={logContainerRef} className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
            {operationLogs.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <p className="text-[10px]">执行操作后将记录在此</p>
              </div>
            ) : (
              operationLogs.slice(-20).map(log => (
                <div
                  key={log.id}
                  className={`flex items-center gap-1 p-1 rounded text-[10px] ${
                    log.status === 'success' ? 'bg-emerald-50 dark:bg-emerald-950/30' : 'bg-red-50 dark:bg-red-950/30'
                  }`}
                >
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-white text-[8px] font-bold ${
                    log.status === 'success' ? 'bg-emerald-500' : 'bg-red-500'
                  }`}>
                    {log.status === 'success' ? '✓' : '✗'}
                  </span>
                  <span className="font-medium">{log.action}</span>
                  {log.params && <span className="text-muted-foreground truncate">{log.params}</span>}
                </div>
              ))
            )}
          </div>
        </div>

        {/* 生成代码 - pytest/yml 编辑器 */}
        {showCode && (
          <div className="border-t">
            <div className="flex items-center justify-between px-3 py-1.5 bg-muted/50">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium">生成代码</span>
                <Badge variant="outline" className="text-[10px]">{recordedActions.length} 步</Badge>
                {/* Tab 切换 */}
                <div className="flex bg-white/5 rounded p-0.5 border border-border">
                  <button
                    onClick={() => setEditorTab('pytest')}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${
                      editorTab === 'pytest' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Pytest
                  </button>
                  <button
                    onClick={() => setEditorTab('yml')}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${
                      editorTab === 'yml' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    YAML
                  </button>
                </div>
              </div>
              <Button variant="ghost" size="sm" className="h-5 text-[10px]" onClick={copyCode}>
                <Copy className="w-3 h-3 mr-0.5" />
                复制
              </Button>
            </div>
            <pre className="p-2 text-[10px] font-mono bg-zinc-950 text-zinc-200 overflow-auto h-32 whitespace-pre-wrap break-all">
              {editorTab === 'pytest' ? pytestCode : ymlCode}
            </pre>
          </div>
        )}
      </div>

      {/* 应用管理弹窗 */}
      {showApps && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center" onClick={() => setShowApps(false)}>
          <div className="bg-background border rounded-xl shadow-2xl w-[480px] max-h-[70vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="font-semibold">应用管理</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowApps(false)}><X className="w-4 h-4" /></Button>
            </div>
            <div className="p-3 space-y-2">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder="搜索应用..." value={appSearch} onChange={e => setAppSearch(e.target.value)} className="pl-8" />
              </div>
              <div className="flex gap-1">
                <Button variant={appTab === 'third_party' ? 'default' : 'outline'} size="sm" onClick={() => setAppTab('third_party')}>
                  第三方 ({apps?.third_party.length || 0})
                </Button>
                <Button variant={appTab === 'system' ? 'default' : 'outline'} size="sm" onClick={() => setAppTab('system')}>
                  系统 ({apps?.system.length || 0})
                </Button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              {filteredApps.map((app: InstalledAppInfo) => (
                <div key={app.package_name} className="flex items-center justify-between p-2 rounded-lg hover:bg-accent">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{app.app_name || app.package_name}</p>
                    {app.app_name && <p className="text-xs text-muted-foreground font-mono truncate">{app.package_name}</p>}
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => handleLaunchPkg(app.package_name)}>
                    <Play className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* UI元素弹窗 */}
      {showElements && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center" onClick={() => setShowElements(false)}>
          <div className="bg-background border rounded-xl shadow-2xl w-[560px] max-h-[70vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="font-semibold">UI 元素 ({uiElements?.elements.length || 0})</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowElements(false)}><X className="w-4 h-4" /></Button>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              {uiElements?.elements?.map((el, idx) => (
                <div
                  key={idx}
                  className={`p-2 rounded-lg border cursor-pointer hover:bg-accent ${el.clickable ? 'bg-emerald-50/50 dark:bg-emerald-950/30' : 'bg-card'}`}
                  onClick={() => {
                    if (el.clickable && el.center) {
                      exec('点击元素', () => sendTap(el.center[0], el.center[1], deviceId).then(() => {}));
                      setShowElements(false);
                    }
                  }}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm truncate flex-1">{el.text || el.content_desc || '-'}</p>
                    {el.clickable && <Badge variant="default" className="text-xs ml-2">可点击</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">{el.class_name?.split('.').pop()} | {el.package}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
