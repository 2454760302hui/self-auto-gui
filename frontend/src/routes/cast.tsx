import { createFileRoute } from '@tanstack/react-router';
import React, { useState, useEffect, useRef } from 'react';
import { useSearch } from '@tanstack/react-router';
import { ScrcpyPlayer } from '../components/ScrcpyPlayer';
import { ResizableHandle } from '../components/ResizableHandle';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { useScreenshotPolling } from '../hooks/useScreenshotPolling';
import {
  Fingerprint,
  ArrowUpDown,
  AlertCircle,
  CheckCircle2,
  Loader2,
  X,
  RefreshCw,
  Home,
  ChevronLeft,
  Copy,
  Play,
  FileCode,
  FileText,
  Trash2,
  ChevronRight,
} from 'lucide-react';
import { XNextLogo } from '../components/XNextLogo';
import {
  shouldShowWebCodecsWarning,
  dismissWebCodecsWarning,
} from '../lib/webcodecs-utils';
import {
  listDevices,
  sendKeyEvent,
  sendTextInput,
  runPytest,
  type Device,
  type PytestRunResponse,
} from '../api';

function getScreenshotPollDelay(mode: 'auto' | 'video' | 'screenshot'): number {
  return mode === 'screenshot' ? 750 : 1200;
}

export const Route = createFileRoute('/cast')({
  component: CastPage,
});

function CastPage() {
  // 从URL获取设备序列号 - 使用类型断言处理
  const searchParams = useSearch({ from: '/cast' }) as { serial?: string };
  const serial = searchParams?.serial;
  const [deviceId, setDeviceId] = useState<string>('');
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedSerial, setSelectedSerial] = useState<string>(serial || '');
  const [useVideoStream, setUseVideoStream] = useState(true);
  const [videoStreamFailed, setVideoStreamFailed] = useState(false);
  const [displayMode, setDisplayMode] = useState<'auto' | 'video' | 'screenshot'>('auto');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [feedbackType, setFeedbackType] = useState<'tap' | 'swipe' | 'error' | 'success'>('success');
  const [showControlArea, setShowControlArea] = useState(false);
  const [panelWidth, setPanelWidth] = useLocalStorage<number | 'auto'>(
    'cast-monitor-width',
    'auto'
  );
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
  const [showWebCodecsWarning, setShowWebCodecsWarning] = useState(false);
  const [showEditorPanel, setShowEditorPanel] = useState(true);
  const [editorTab, setEditorTab] = useState<'pytest' | 'yml'>('pytest');
  const [pytestCode, setPytestCode] = useState(`"""Auto-generated device control test."""
import subprocess, time

DEVICE_ID = "${serial || 'your_device_serial'}"

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
    tap(540, 960)
    time.sleep(1)
`);
  const [ymlCode, setYmlCode] = useState(`# AutoGLM 自动化用例配置
name: 示例用例
description: 设备自动化测试

steps:
  - action: tap
    x: 540
    y: 960
    description: 点击屏幕中心

  - action: swipe
    start_x: 540
    start_y: 1500
    end_x: 540
    end_y: 500
    duration: 300
    description: 向上滑动

  - action: back
    description: 返回上一页

  - action: home
    description: 回到主页

  - action: text
    content: "Hello World"
    description: 输入文字
`);
  const [pytestResult, setPytestResult] = useState<PytestRunResponse | null>(null);
  const [runningCode, setRunningCode] = useState(false);

  const videoStreamRef = useRef<{ close: () => void } | null>(null);
  const feedbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controlsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 加载设备列表
  useEffect(() => {
    const loadDevices = async () => {
      try {
        const response = await listDevices();
        const connectedDevices = response.devices.filter(
          device => device.state !== 'disconnected'
        );
        setDevices(connectedDevices);

        // 如果有传入的serial，查找对应设备
        if (selectedSerial) {
          const device = connectedDevices.find(d => d.serial === selectedSerial);
          if (device) {
            setDeviceId(device.id);
          }
        } else if (connectedDevices.length > 0 && !deviceId) {
          setSelectedSerial(connectedDevices[0].serial);
          setDeviceId(connectedDevices[0].id);
        }
      } catch (error) {
        console.error('Failed to load devices:', error);
      }
    };

    loadDevices();
    const interval = setInterval(loadDevices, 5000);
    return () => clearInterval(interval);
  }, [selectedSerial, deviceId]);

  const isVisible = true;
  const currentDevice = devices.find(d => d.serial === selectedSerial);
  const isHarmonyOS = currentDevice?.platform === 'harmonyos';

  // 截图模式 或 (自动模式+视频流失败/HarmonyOS) 或 视频模式但不支持(HarmonyOS) 时使用截图
  const shouldUseScreenshot =
    displayMode === 'screenshot' ||
    (displayMode === 'auto' && (!useVideoStream || videoStreamFailed || isHarmonyOS)) ||
    (displayMode === 'video' && isHarmonyOS);

  const shouldPollScreenshots = isVisible && shouldUseScreenshot;

  const { screenshot, triggerRefresh } = useScreenshotPolling({
    deviceId,
    enabled: shouldPollScreenshots,
    pollDelayMs: getScreenshotPollDelay(displayMode),
  });

  const showFeedback = (
    message: string,
    duration = 2000,
    type: 'tap' | 'swipe' | 'error' | 'success' = 'success'
  ) => {
    if (feedbackTimeoutRef.current) {
      clearTimeout(feedbackTimeoutRef.current);
    }
    setFeedbackType(type);
    setFeedbackMessage(message);
    feedbackTimeoutRef.current = setTimeout(() => {
      setFeedbackMessage(null);
    }, duration);
  };

  const handleMouseEnter = () => {
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    setShowControlArea(true);
  };

  const handleMouseLeave = () => {
    controlsTimeoutRef.current = setTimeout(() => {
      setShowControlArea(false);
    }, 500);
  };

  const handleWidthChange = (width: number | 'auto') => {
    setPanelWidth(width);
  };

  const handleResize = (deltaX: number) => {
    if (typeof panelWidth !== 'number') {
      setPanelWidth(320);
      return;
    }
    const newWidth = Math.min(800, Math.max(320, panelWidth + deltaX));
    setPanelWidth(newWidth);
  };

  const handleDeviceChange = (newSerial: string) => {
    setSelectedSerial(newSerial);
    const device = devices.find(d => d.serial === newSerial);
    if (device) {
      setDeviceId(device.id);
    }
  };

  const handleVideoStreamReady = (stream: { close: () => void } | null) => {
    videoStreamRef.current = stream;
  };

  const handleFallback = (reason?: string) => {
    setVideoStreamFailed(true);
    setUseVideoStream(false);
    setFallbackReason(reason || null);

    if (displayMode === 'video' && reason && shouldShowWebCodecsWarning()) {
      setShowWebCodecsWarning(true);
    }
  };

  const toggleDisplayMode = (mode: 'auto' | 'video' | 'screenshot') => {
    setDisplayMode(mode);
  };

  // --- 操作录制 & 代码生成相关 state & helpers ---
  const [recordedActions, setRecordedActions] = useState<
    Array<{
      id: string;
      type: 'tap' | 'swipe' | 'input' | 'keyevent' | 'launch' | 'double_tap' | 'long_press' | 'scroll';
      timestamp: number;
      params: Record<string, unknown>;
      description: string;
      screenWidth: number;
      screenHeight: number;
    }>
  >([]);

  const screenRef = useRef<{ width: number; height: number }>({
    width: 1080,
    height: 1920,
  });

  const genPytestCode = (actions: typeof recordedActions): string => {
    const serial = selectedSerial || 'your_device_serial';
    let code = `"""Auto-generated device control test."""
import subprocess, time

DEVICE_ID = "${serial}"

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

def scroll_up():
    swipe(540, 1500, 540, 500)

def scroll_down():
    swipe(540, 500, 540, 1500)

def scroll_left():
    swipe(900, 960, 100, 960)

def scroll_right():
    swipe(100, 960, 900, 960)


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
          const dir = (a.params as Record<string, unknown>).direction;
          if (dir === 'up') code += `    scroll_up()\n`;
          else if (dir === 'down') code += `    scroll_down()\n`;
          else if (dir === 'left') code += `    scroll_left()\n`;
          else if (dir === 'right') code += `    scroll_right()\n`;
          else code += `    swipe(${a.params.sx}, ${a.params.sy}, ${a.params.ex}, ${a.params.ey}, ${a.params.d || 300})\n`;
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
          code += `    adb("monkey -p ${a.params.package} -c android.intent.category.LAUNCHER 1")\n`;
          break;
      }
    });
    return code;
  };

  const genYamlCode = (actions: typeof recordedActions): string => {
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
          yaml += `  - action: scroll
    direction: ${(a.params as Record<string, unknown>).direction || 'up'}
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
    return yaml;
  };

  // 每当有操作记录变化，同步更新右侧编辑器代码
  useEffect(() => {
    setPytestCode(genPytestCode(recordedActions));
    setYmlCode(genYamlCode(recordedActions));
    console.log('[CastPage] Generated code for', recordedActions.length, 'actions');
  }, [recordedActions, selectedSerial]);

  // 记录操作
  const recordAction = (
    type: typeof recordedActions[0]['type'],
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
  };

  useEffect(() => {
    return () => {
      if (feedbackTimeoutRef.current) {
        clearTimeout(feedbackTimeoutRef.current);
      }
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
      if (videoStreamRef.current) {
        videoStreamRef.current.close();
      }
    };
  }, []);

  // Keyboard input: map keys to Android keycodes / text input
  // Use ref for deviceId to avoid stale closure issues
  const deviceIdRef = useRef(deviceId);
  const triggerRefreshRef = useRef(triggerRefresh);
  useEffect(() => { deviceIdRef.current = deviceId; }, [deviceId]);
  useEffect(() => { triggerRefreshRef.current = triggerRefresh; }, [triggerRefresh]);

  useEffect(() => {
    const KEYCODE_MAP: Record<string, number> = {
      Backspace: 67,
      Delete: 112,
      Enter: 66,
      Tab: 61,
      Escape: 111,
      ArrowUp: 19,
      ArrowDown: 20,
      ArrowLeft: 21,
      ArrowRight: 22,
      Home: 3,
      End: 123,
      PageUp: 92,
      PageDown: 93,
      ' ': 62,
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      const did = deviceIdRef.current;
      if (!did) return;

      // Skip when user is typing in an input/textarea/select
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      // Allow browser shortcuts
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const keycode = KEYCODE_MAP[e.key];
      if (keycode !== undefined) {
        e.preventDefault();
        e.stopPropagation();
        sendKeyEvent(keycode, did).then(() => {
          const label =
            keycode === 66 ? 'Enter' :
            keycode === 67 ? '⌫' :
            keycode === 111 ? 'Esc' :
            keycode === 3 ? 'Home' :
            keycode === 62 ? 'Space' :
            e.key;
          showFeedback(`按键: ${label}`, 1200, 'tap');
          triggerRefreshRef.current?.();
        }).catch((err: unknown) => {
          showFeedback(`按键失败: ${err}`, 2000, 'error');
        });
        return;
      }

      // Printable single character → text input
      if (e.key.length === 1) {
        e.preventDefault();
        e.stopPropagation();
        sendTextInput(e.key, did).then(() => {
          showFeedback(`输入: ${e.key}`, 800, 'tap');
          triggerRefreshRef.current?.();
        }).catch((err: unknown) => {
          showFeedback(`输入失败: ${err}`, 2000, 'error');
        });
      }
    };

    // Use capture phase to intercept before anything else
    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, []); // empty deps - uses ref for deviceId

  const handleRunPytest = async () => {
    setRunningCode(true);
    setPytestResult(null);
    try {
      const result = await runPytest(pytestCode);
      setPytestResult(result);
    } catch (e) {
      console.error(e);
    } finally {
      setRunningCode(false);
    }
  };

  const getReasonMessage = (reason: string): string => {
    const messages: Record<string, string> = {
      insecure_context: '视频流需要 HTTPS 或 localhost 环境',
      browser_unsupported: '当前浏览器不支持 WebCodecs API，请使用最新版 Chrome 或 Edge',
      decoder_error: '视频解码器初始化失败',
      decoder_unsupported: '设备编解码器不支持',
    };
    return messages[reason] || '未知错误';
  };


  return (
    <div className="h-screen w-screen bg-black overflow-hidden flex flex-col">
      {/* 顶部工具栏 */}
      <div
        className={`absolute top-0 left-0 right-0 z-30 transition-all duration-300 ${
          showControlArea ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2 pointer-events-none'
        }`}
      >
        <div className="bg-gradient-to-b from-black/80 to-transparent p-4">
          <div className="flex items-center justify-between max-w-2xl mx-auto">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <XNextLogo size="small" />
              <div>
                <p className="text-white/60 text-xs">
                  {currentDevice ? (
                    <>
                      {currentDevice.display_name || currentDevice.model}
                      {isHarmonyOS && (
                        <span className="ml-2 px-1.5 py-0.5 bg-blue-500/30 text-blue-300 text-[10px] rounded">
                          HarmonyOS
                        </span>
                      )}
                    </>
                  ) : '未选择设备'}
                  {/* 显示模式切换 */}
                  <span className="ml-2 flex items-center gap-1">
                    <button
                      onClick={() => toggleDisplayMode('video')}
                      className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
                        displayMode === 'video'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white/10 text-white/60 hover:bg-white/20'
                      }`}
                    >
                      视频
                    </button>
                    <button
                      onClick={() => toggleDisplayMode('screenshot')}
                      className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
                        displayMode === 'screenshot'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white/10 text-white/60 hover:bg-white/20'
                      }`}
                    >
                      截图
                    </button>
                  </span>
                  {recordedActions.length > 0 && (
                    <span className="ml-2 px-1.5 py-0.5 bg-emerald-500/30 text-emerald-300 text-[10px] rounded flex items-center gap-1">
                      {recordedActions.length} 条操作
                      <button
                        className="ml-1 hover:text-white/80 transition-colors"
                        onClick={() => {
                          setRecordedActions([]);
                          setPytestCode(`"""Auto-generated device control test."""
import subprocess, time

DEVICE_ID = "${selectedSerial || 'your_device_serial'}"

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
    tap(540, 960)
    time.sleep(1)`);
                          setYmlCode(`# AutoGLM 自动化用例配置
name: 示例用例
description: 设备自动化测试

steps:
  - action: tap
    x: 540
    y: 960
    description: 点击屏幕中心

  - action: swipe
    start_x: 540
    start_y: 1500
    end_x: 540
    end_y: 500
    duration: 300
    description: 向上滑动

  - action: back
    description: 返回上一页

  - action: home
    description: 回到主页

  - action: text
    content: "Hello World"
    description: 输入文字
`);
                          setPytestResult(null);
                        }}
                        title="清空所有操作"
                      >
                        ✕
                      </button>
                    </span>
                  )}
                </p>
              </div>
            </div>

            {/* 设备选择 */}
            {devices.length > 1 && (
              <select
                value={selectedSerial}
                onChange={(e) => handleDeviceChange(e.target.value)}
                className="bg-white/10 backdrop-blur text-white text-sm rounded-lg px-3 py-2 border border-white/20 outline-none"
              >
                {devices.map(device => (
                  <option key={device.id} value={device.serial} className="bg-gray-800">
                    {device.display_name || device.model} ({device.serial})
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>
      </div>

      {/* 主内容区：投屏 + 右侧编辑器 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 投屏区域 */}
        <div className="flex-1 flex items-center justify-center overflow-hidden">
          {!deviceId ? (
            <div className="text-center">
              <p className="text-white/50">等待设备连接...</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4 border-white/20 text-white hover:bg-white/10 bg-gradient-to-r from-indigo-500/20 to-cyan-500/20"
                onClick={() => window.location.reload()}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                刷新
              </Button>
            </div>
          ) : (
            <Card
              className="relative overflow-hidden bg-black border-0 shadow-2xl rounded-xl"
              style={{
                width: typeof panelWidth === 'number' ? `${panelWidth}px` : 'auto',
                maxWidth: '420px',
                maxHeight: 'calc(100vh - 20px)',
                aspectRatio: typeof panelWidth !== 'number' ? '9/16' : undefined,
              }}
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
            >
              {/* 左侧可调整大小手柄 */}
              {typeof panelWidth === 'number' && (
                <ResizableHandle
                  onResize={handleResize}
                  minWidth={280}
                  maxWidth={420}
                  className="z-20"
                />
              )}

              {/* 操作反馈消息 */}
              {feedbackMessage && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 px-3 py-2 bg-white/90 text-black text-sm rounded-xl shadow-lg">
                  {feedbackType === 'error' && <AlertCircle className="w-4 h-4 text-red-500" />}
                  {feedbackType === 'tap' && <Fingerprint className="w-4 h-4" />}
                  {feedbackType === 'swipe' && <ArrowUpDown className="w-4 h-4" />}
                  {feedbackType === 'success' && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                  <span>{feedbackMessage}</span>
                </div>
              )}

              {/* 底部虚拟按键 */}
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-4">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    if (!deviceId) return;
                    sendKeyEvent(3, deviceId).then(() => {
                      showFeedback('Home 键', 800, 'tap');
                      recordAction('keyevent', { keycode: 3 }, 'Home 键');
                    }).catch((err: unknown) => {
                      showFeedback(`Home 键失败: ${err}`, 2000, 'error');
                    });
                  }}
                  className="h-12 w-12 rounded-full bg-black/80 backdrop-blur border border-white/10 shadow-lg hover:bg-white/20 text-white"
                  title="返回主屏幕"
                >
                  <Home className="w-6 h-6" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    if (!deviceId) return;
                    sendKeyEvent(4, deviceId).then(() => {
                      showFeedback('返回键', 800, 'tap');
                      recordAction('keyevent', { keycode: 4 }, '返回键');
                    }).catch((err: unknown) => {
                      showFeedback(`返回键失败: ${err}`, 2000, 'error');
                    });
                  }}
                  className="h-12 w-12 rounded-full bg-black/80 backdrop-blur border border-white/10 shadow-lg hover:bg-white/20 text-white"
                  title="返回上一页"
                >
                  <ChevronLeft className="w-6 h-6" />
                </Button>
              </div>

              {/* WebCodecs 警告 */}
              {showWebCodecsWarning && fallbackReason && (
                <div className="absolute top-0 left-0 right-0 z-20 bg-amber-50/95 dark:bg-amber-950/95 border-b border-amber-200 dark:border-amber-800 backdrop-blur-sm">
                  <div className="px-4 py-3 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                          视频流不可用
                        </p>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-5 w-5 -mr-2 hover:bg-amber-100 dark:hover:bg-amber-900"
                          onClick={() => {
                            setShowWebCodecsWarning(false);
                            dismissWebCodecsWarning();
                          }}
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </div>
                      <p className="text-xs text-amber-700 dark:text-amber-300">
                        {getReasonMessage(fallbackReason)}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* 视频流或截图 */}
              {shouldUseScreenshot ? (
                screenshot?.success ? (
                  <ScrcpyPlayer
                    deviceId={deviceId}
                    className="w-full h-full"
                    enableControl={true}
                    fallbackScreenshot={screenshot.image}
                    onTapSuccess={(x, y) => {
                      showFeedback(`点击成功`, 2000, 'tap');
                      recordAction('tap', { x, y }, `点击 (${x}, ${y})`);
                    }}
                    onSwipeSuccess={(sx, sy, ex, ey) => {
                      showFeedback('滑动成功', 2000, 'swipe');
                      recordAction('swipe', { sx, sy, ex, ey }, `滑动 (${sx},${sy})→(${ex},${ey})`);
                    }}
                    onControlAction={triggerRefresh}
                    onScreenInfo={info => {
                      screenRef.current = { width: info.width, height: info.height };
                    }}
                  />
                ) : screenshot?.error ? (
                  <div className="w-full h-full flex items-center justify-center bg-gray-900">
                    <div className="text-center text-red-400">
                      <AlertCircle className="w-8 h-8 mx-auto mb-2" />
                      <p className="font-medium">截图失败</p>
                      <p className="text-xs mt-1 opacity-60">{screenshot.error}</p>
                    </div>
                  </div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gray-900">
                    <div className="text-center text-white/50">
                      <Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin" />
                      <p className="text-sm">加载中...</p>
                    </div>
                  </div>
                )
              ) : (
                <ScrcpyPlayer
                  deviceId={deviceId}
                  className="w-full h-full"
                  enableControl={true}
                  onFallback={handleFallback}
                  onTapSuccess={(x, y) => {
                    showFeedback(`点击成功`, 2000, 'tap');
                    recordAction('tap', { x, y }, `点击 (${x}, ${y})`);
                  }}
                  onTapError={error => showFeedback(`点击失败: ${error}`, 3000, 'error')}
                  onSwipeSuccess={(sx, sy, ex, ey) => {
                    showFeedback('滑动成功', 2000, 'swipe');
                    recordAction('swipe', { sx, sy, ex, ey }, `滑动 (${sx},${sy})→(${ex},${ey})`);
                  }}
                  onSwipeError={error => showFeedback(`滑动失败: ${error}`, 3000, 'error')}
                  onStreamReady={handleVideoStreamReady}
                  fallbackTimeout={8000}
                  isVisible={isVisible}
                  onScreenInfo={info => {
                    screenRef.current = { width: info.width, height: info.height };
                  }}
                  fallbackScreenshot={screenshot?.success ? screenshot.image : null}
                  onControlAction={triggerRefresh}
                />
              )}
            </Card>
          )}
        </div>

        {/* 右侧编辑器面板切换按钮 */}
        <button
          onClick={() => setShowEditorPanel(v => !v)}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-40 bg-indigo-600 hover:bg-indigo-700 text-white rounded-l-lg px-1 py-3 shadow-lg transition-colors"
          title={showEditorPanel ? '收起编辑器' : '展开编辑器'}
        >
          {showEditorPanel ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        {/* 右侧代码编辑器面板 */}
        {showEditorPanel && (
          <div className="w-[480px] flex-shrink-0 bg-[#1e1e2e] border-l border-white/10 flex flex-col overflow-hidden">
            {/* 面板头部 */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-[#16162a]">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-indigo-400" />
                <span className="text-white text-sm font-medium">用例编辑器</span>
              </div>
              <div className="flex items-center gap-1">
                {/* Tab 切换 */}
                <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/10">
                  <button
                    onClick={() => setEditorTab('pytest')}
                    className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                      editorTab === 'pytest'
                        ? 'bg-indigo-600 text-white'
                        : 'text-white/50 hover:text-white'
                    }`}
                  >
                    <FileCode className="w-3 h-3 inline mr-1" />
                    Pytest
                  </button>
                  <button
                    onClick={() => setEditorTab('yml')}
                    className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                      editorTab === 'yml'
                        ? 'bg-indigo-600 text-white'
                        : 'text-white/50 hover:text-white'
                    }`}
                  >
                    <FileText className="w-3 h-3 inline mr-1" />
                    YAML
                  </button>
                </div>
              </div>
            </div>

            {/* 操作按钮栏 */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-white/10 bg-[#16162a]">
              <Button
                size="sm"
                className="h-7 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={handleRunPytest}
                disabled={runningCode || editorTab !== 'pytest'}
              >
                {runningCode ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Play className="w-3 h-3" />
                )}
                一键执行
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5 border-white/20 text-white/70 hover:text-white hover:bg-white/10"
                onClick={() => navigator.clipboard.writeText(editorTab === 'pytest' ? pytestCode : ymlCode)}
              >
                <Copy className="w-3 h-3" />
                复制
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5 border-white/20 text-white/70 hover:text-white hover:bg-white/10"
                onClick={() => {
                  if (editorTab === 'pytest') setPytestCode('');
                  else setYmlCode('');
                  setPytestResult(null);
                }}
              >
                <Trash2 className="w-3 h-3" />
                清空
              </Button>
              {pytestResult && (
                <Badge
                  className={`ml-auto text-xs ${
                    pytestResult.success
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                      : 'bg-red-500/20 text-red-400 border-red-500/30'
                  }`}
                >
                  {pytestResult.success ? (
                    <><CheckCircle2 className="w-3 h-3 mr-1" />执行成功</>
                  ) : (
                    <><AlertCircle className="w-3 h-3 mr-1" />执行失败</>
                  )}
                </Badge>
              )}
            </div>

            {/* 代码编辑区 */}
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              {editorTab === 'pytest' ? (
                <textarea
                  className="flex-1 bg-[#1e1e2e] text-[#cdd6f4] p-4 text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500/50 leading-relaxed"
                  value={pytestCode}
                  onChange={e => setPytestCode(e.target.value)}
                  spellCheck={false}
                  placeholder="# 在此编写 pytest 测试代码..."
                />
              ) : (
                <textarea
                  className="flex-1 bg-[#1e1e2e] text-[#cdd6f4] p-4 text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500/50 leading-relaxed"
                  value={ymlCode}
                  onChange={e => setYmlCode(e.target.value)}
                  spellCheck={false}
                  placeholder="# 在此编写 YAML 用例配置..."
                />
              )}

              {/* 执行结果 */}
              {pytestResult && (
                <div className={`border-t border-white/10 p-3 max-h-40 overflow-y-auto ${
                  pytestResult.success ? 'bg-emerald-950/30' : 'bg-red-950/30'
                }`}>
                  <p className="text-[10px] font-semibold mb-1 text-white/60">执行输出</p>
                  <pre className={`text-[10px] font-mono whitespace-pre-wrap break-all ${
                    pytestResult.success ? 'text-emerald-300' : 'text-red-300'
                  }`}>
                    {pytestResult.output || (pytestResult.success ? '执行成功，无输出' : '执行失败')}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
