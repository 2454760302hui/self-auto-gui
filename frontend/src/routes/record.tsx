import { createFileRoute } from '@tanstack/react-router';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearch } from '@tanstack/react-router';
import { ScrcpyPlayer } from '../components/ScrcpyPlayer';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '../hooks/useToast';
import {
  listDevices,
  type Device,
  runPytest,
  runYaml,
  getControlScreenshot,
  sendTap,
  sendSwipe,
  sendKeyEvent,
  sendTextInput,
  sendBack,
  sendHome,
  sendLaunchApp,
  sendDoubleTap,
  sendLongPress,
  sendScroll,
} from '../api';
import { useTranslation } from '../lib/i18n-context';
import {
  CircleDot,
  Circle,
  Square,
  MousePointer,
  Type,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  CornerDownLeft,
  Home,
  ChevronLeft,
  Play,
  Pause,
  Download,
  Code,
  FileCode,
  Smartphone,
  Tablet,
  Monitor,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Copy,
  Trash2,
  Plus,
  Minus,
} from 'lucide-react';

interface RecordedAction {
  id: string;
  type: 'tap' | 'swipe' | 'input' | 'keyevent' | 'launch' | 'double_tap' | 'long_press' | 'scroll';
  timestamp: number;
  params: Record<string, unknown>;
  description: string;
  screenWidth: number;
  screenHeight: number;
}

interface CodeTemplate {
  pytest: string;
  yaml: string;
}

export const Route = createFileRoute('/record')({
  component: RecordPage,
});

function RecordPage() {
  const t = useTranslation();
  const { toast } = useToast();
  const searchParams = useSearch({ from: '/record' }) as { serial?: string };

  // Device state
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedSerial, setSelectedSerial] = useState<string>(searchParams?.serial || '');
  const [deviceId, setDeviceId] = useState<string>('');

  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordedActions, setRecordedActions] = useState<RecordedAction[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(0);

  // Code generation state
  const [codeTemplate, setCodeTemplate] = useState<CodeTemplate | null>(null);
  const [activeCodeTab, setActiveCodeTab] = useState<'pytest' | 'yaml'>('pytest');
  const [generatedCode, setGeneratedCode] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [runOutput, setRunOutput] = useState<{ success: boolean; output: string } | null>(null);

  // Screen dimensions
  const [screenWidth, setScreenWidth] = useState(1080);
  const [screenHeight, setScreenHeight] = useState(1920);

  // Load devices
  useEffect(() => {
    const loadDevices = async () => {
      try {
        const response = await listDevices();
        const connectedDevices = response.devices.filter(
          device => device.state !== 'disconnected'
        );
        setDevices(connectedDevices);

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

  const currentDevice = devices.find(d => d.serial === selectedSerial);

  // Handle tap action from screen
  const handleTap = useCallback(async (x: number, y: number) => {
    if (!isRecording || !deviceId) return;

    const action: RecordedAction = {
      id: `tap-${Date.now()}`,
      type: 'tap',
      timestamp: Date.now(),
      params: { x, y },
      description: `点击 (${x}, ${y})`,
      screenWidth,
      screenHeight,
    };

    setRecordedActions(prev => [...prev, action]);
  }, [isRecording, deviceId, screenWidth, screenHeight]);

  // Generate code from recorded actions
  const generateCode = useCallback(() => {
    setIsGenerating(true);

    const pytestCode = generatePytestCode(recordedActions);
    const yamlCode = generateYamlCode(recordedActions);

    setCodeTemplate({ pytest: pytestCode, yaml: yamlCode });
    setGeneratedCode(pytestCode);
    setIsGenerating(false);
  }, [recordedActions]);

  const generatePytestCode = (actions: RecordedAction[]): string => {
    const deviceSerial = selectedSerial || 'emulator-5554';

    let code = `"""Auto-generated pytest code for device automation."""
import pytest
import subprocess
import time

DEVICE_ID = "${deviceSerial}"

def adb_shell(cmd: str) -> str:
    """Execute ADB shell command."""
    result = subprocess.run(
        ["adb", "-s", DEVICE_ID, "shell", cmd],
        capture_output=True,
        text=True
    )
    return result.stdout

def tap(x: int, y: int, delay: float = 1.0):
    """Tap at coordinates."""
    adb_shell(f"input tap {x} {y}")
    time.sleep(delay)

def swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 300, delay: float = 1.0):
    """Swipe from start to end coordinates."""
    adb_shell(f"input swipe {start_x} {start_y} {end_x} {end_y} {duration}")
    time.sleep(delay)

def input_text(text: str, delay: float = 1.0):
    """Input text."""
    adb_shell(f'input text "{text.replace('"', '\\\\"')}"')
    time.sleep(delay)

def press_keyevent(keycode: int, delay: float = 0.5):
    """Press key event."""
    adb_shell(f"input keyevent {keycode}")
    time.sleep(delay)

def launch_app(package_name: str, delay: float = 2.0):
    """Launch app by package name."""
    adb_shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
    time.sleep(delay)

def scroll_up(distance: int = 500, delay: float = 1.0):
    """Scroll up."""
    adb_shell(f"input swipe 540 1500 540 {1500 - distance} 300")
    time.sleep(delay)

def scroll_down(distance: int = 500, delay: float = 1.0):
    """Scroll down."""
    adb_shell(f"input swipe 540 500 540 {500 + distance} 300")
    time.sleep(delay)

def scroll_left(distance: int = 500, delay: float = 1.0):
    """Scroll left."""
    adb_shell(f"input swipe 900 1200 {900 + distance} 1200 300")
    time.sleep(delay)

def scroll_right(distance: int = 500, delay: float = 1.0):
    """Scroll right."""
    adb_shell(f"input swipe 300 1200 {300 - distance} 1200 300")
    time.sleep(delay)

@pytest.fixture(scope="module")
def setup_device():
    """Setup device connection."""
    print(f"Connected to device: {DEVICE_ID}")
    yield
    print("Test completed")

def test_automation_flow(setup_device):
    """Recorded automation flow."""
`;

    actions.forEach((action, index) => {
      switch (action.type) {
        case 'tap':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          code += `    tap(${action.params.x}, ${action.params.y})\n`;
          break;
        case 'swipe':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          code += `    swipe(${action.params.start_x}, ${action.params.start_y}, ${action.params.end_x}, ${action.params.end_y})\n`;
          break;
        case 'input':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          code += `    input_text("${action.params.text}")\n`;
          break;
        case 'keyevent':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          code += `    press_keyevent(${action.params.keycode})\n`;
          break;
        case 'launch':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          code += `    launch_app("${action.params.package}")\n`;
          break;
        case 'double_tap':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          code += `    tap(${action.params.x}, ${action.params.y})\n`;
          code += `    tap(${action.params.x}, ${action.params.y})\n`;
          break;
        case 'long_press':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          code += `    adb_shell("input swipe ${action.params.x} ${action.params.y} ${action.params.x} ${action.params.y} ${action.params.duration || 1000}")\n`;
          break;
        case 'scroll':
          code += `\n    # Step ${index + 1}: ${action.description}\n`;
          const direction = action.params.direction;
          if (direction === 'up') code += `    scroll_up()\n`;
          else if (direction === 'down') code += `    scroll_down()\n`;
          else if (direction === 'left') code += `    scroll_left()\n`;
          else if (direction === 'right') code += `    scroll_right()\n`;
          break;
      }
    });

    return code;
  };

  const generateYamlCode = (actions: RecordedAction[]): string => {
    const deviceSerial = selectedSerial || 'emulator-5554';

    let yaml = `# Auto-generated YAML automation script
device_id: "${deviceSerial}"
steps:
`;

    actions.forEach((action, index) => {
      switch (action.type) {
        case 'tap':
          yaml += `  - action: tap
    x: ${action.params.x}
    y: ${action.params.y}
    delay: 1
`;
          break;
        case 'swipe':
          yaml += `  - action: swipe
    start_x: ${action.params.start_x}
    start_y: ${action.params.start_y}
    end_x: ${action.params.end_x}
    end_y: ${action.params.end_y}
    duration: ${action.params.duration || 300}
    delay: 1
`;
          break;
        case 'input':
          yaml += `  - action: input_text
    text: "${action.params.text}"
    delay: 1
`;
          break;
        case 'keyevent':
          yaml += `  - action: keyevent
    keycode: ${action.params.keycode}
    delay: 0.5
`;
          break;
        case 'launch':
          yaml += `  - action: launch
    package: "${action.params.package}"
    delay: 2
`;
          break;
        case 'double_tap':
          yaml += `  - action: double_tap
    x: ${action.params.x}
    y: ${action.params.y}
    delay: 0.3
`;
          break;
        case 'long_press':
          yaml += `  - action: long_press
    x: ${action.params.x}
    y: ${action.params.y}
    duration: ${action.params.duration || 1000}
    delay: 1
`;
          break;
        case 'scroll':
          yaml += `  - action: scroll_${action.params.direction}
    distance: ${action.params.distance || 500}
    delay: 1
`;
          break;
      }
    });

    return yaml;
  };

  // Run the generated code
  const handleRunCode = async () => {
    if (!generatedCode) return;

    setIsRunning(true);
    setRunOutput(null);
    toast({
      title: '正在运行...',
      description: '代码执行中，请稍候',
      variant: 'info',
    });

    try {
      const filename = activeCodeTab === 'pytest' ? 'test_recorded.py' : 'recorded_test.yaml';
      const response = activeCodeTab === 'pytest'
        ? await runPytest(generatedCode, filename)
        : await runYaml(generatedCode, filename);

      setRunOutput({ success: response.success, output: response.output });
      
      if (response.success) {
        toast({
          title: '✓ 执行成功',
          description: '代码已成功执行',
          variant: 'success',
        });
      } else {
        toast({
          title: '✗ 执行失败',
          description: '代码执行出错，请查看输出详情',
          variant: 'error',
        });
      }
    } catch (error) {
      setRunOutput({ success: false, output: String(error) });
      toast({
        title: '✗ 执行异常',
        description: String(error),
        variant: 'error',
      });
    } finally {
      setIsRunning(false);
    }
  };

  // Copy code to clipboard
  const handleCopyCode = () => {
    navigator.clipboard.writeText(generatedCode).then(() => {
      toast({
        title: '✓ 已复制',
        description: '代码已复制到剪贴板',
        variant: 'success',
      });
    }).catch(() => {
      toast({
        title: '✗ 复制失败',
        description: '无法复制到剪贴板',
        variant: 'error',
      });
    });
  };

  // Clear recorded actions
  const handleClearActions = () => {
    setRecordedActions([]);
    setCodeTemplate(null);
    setGeneratedCode('');
    setRunOutput(null);
  };

  // Manual action recording
  const handleManualAction = (type: RecordedAction['type'], params: Record<string, unknown>, description: string) => {
    if (!isRecording) return;

    const action: RecordedAction = {
      id: `${type}-${Date.now()}`,
      type,
      timestamp: Date.now(),
      params,
      description,
      screenWidth,
      screenHeight,
    };

    setRecordedActions(prev => [...prev, action]);
  };

  // Action buttons configuration
  const actionButtons = [
    {
      icon: MousePointer,
      label: '点击',
      action: () => handleManualAction('tap', { x: 540, y: 960 }, '点击中心位置'),
    },
    {
      icon: ArrowUp,
      label: '上滑',
      action: () => handleManualAction('scroll', { direction: 'up', distance: 500 }, '向上滑动'),
    },
    {
      icon: ArrowDown,
      label: '下滑',
      action: () => handleManualAction('scroll', { direction: 'down', distance: 500 }, '向下滑动'),
    },
    {
      icon: ArrowLeft,
      label: '左滑',
      action: () => handleManualAction('scroll', { direction: 'left', distance: 500 }, '向左滑动'),
    },
    {
      icon: ArrowRight,
      label: '右滑',
      action: () => handleManualAction('scroll', { direction: 'right', distance: 500 }, '向右滑动'),
    },
    {
      icon: ChevronLeft,
      label: '返回',
      action: () => handleManualAction('keyevent', { keycode: 4 }, '按下返回键'),
    },
    {
      icon: Home,
      label: '主页',
      action: () => handleManualAction('keyevent', { keycode: 3 }, '按下主页键'),
    },
  ];

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-card/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold">
                <span className="xnext-gradient-text">录制 & 回放</span>
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                录制操作步骤，生成可复用的自动化脚本
              </p>
            </div>
          </div>

          {/* Device selector */}
          <div className="flex items-center gap-3">
            {devices.length > 0 && (
              <select
                value={selectedSerial}
                onChange={(e) => setSelectedSerial(e.target.value)}
                className="bg-background border border-border rounded-lg px-3 py-2 text-sm"
              >
                {devices.map(device => (
                  <option key={device.id} value={device.serial}>
                    {device.display_name || device.model} ({device.serial})
                  </option>
                ))}
              </select>
            )}

            {/* Platform indicator */}
            {currentDevice && (
              <Badge
                variant={currentDevice.platform === 'harmonyos' ? 'default' : 'secondary'}
                className={currentDevice.platform === 'harmonyos' ? 'bg-blue-500/20 text-blue-500 border-blue-500/30' : ''}
              >
                {currentDevice.platform === 'harmonyos' ? 'HarmonyOS' : 'Android'}
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Screen preview */}
        <div className="w-1/2 flex flex-col border-r border-border">
          {/* Recording controls */}
          <div className="p-4 border-b border-border flex items-center justify-between bg-card/30">
            <div className="flex items-center gap-3">
              <Button
                variant={isRecording ? 'destructive' : 'default'}
                size="sm"
                onClick={() => setIsRecording(!isRecording)}
              >
                {isRecording ? (
                  <>
                    <Pause className="w-4 h-4 mr-2" />
                    停止录制
                  </>
                ) : (
                  <>
                    <CircleDot className="w-4 h-4 mr-2" />
                    开始录制
                  </>
                )}
              </Button>

              {isRecording && (
                <div className="flex items-center gap-2 text-red-500">
                  <Circle className="w-3 h-3 fill-current animate-pulse" />
                  <span className="text-sm font-medium">录制中...</span>
                </div>
              )}

              <span className="text-sm text-muted-foreground">
                {recordedActions.length} 个操作
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={generateCode}
                disabled={recordedActions.length === 0 || isGenerating}
              >
                {isGenerating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Code className="w-4 h-4 mr-2" />
                )}
                生成代码
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearActions}
                disabled={recordedActions.length === 0}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                清空
              </Button>
            </div>
          </div>

          {/* Screen preview */}
          <div className="flex-1 flex items-center justify-center p-6 bg-black/5 dark:bg-white/5 overflow-hidden">
            {deviceId ? (
              <Card className="overflow-hidden bg-black border-0 shadow-2xl rounded-xl" style={{ maxHeight: '100%' }}>
                <ScrcpyPlayer
                  deviceId={deviceId}
                  className="w-full h-full"
                  enableControl={true}
                  onTapSuccess={(x, y) => { if (x !== undefined && y !== undefined) handleTap(x, y); }}
                  fallbackTimeout={20000}
                  isVisible={true}
                />
              </Card>
            ) : (
              <div className="text-center">
                <Smartphone className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
                <p className="text-muted-foreground">请先选择设备</p>
              </div>
            )}
          </div>

          {/* Manual action buttons */}
          <div className="p-4 border-t border-border bg-card/30">
            <p className="text-xs text-muted-foreground mb-3">快捷操作（录制时点击记录）</p>
            <div className="flex flex-wrap gap-2">
              {actionButtons.map((btn, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={btn.action}
                  disabled={!isRecording}
                  className="gap-1.5"
                >
                  <btn.icon className="w-3.5 h-3.5" />
                  {btn.label}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Actions list and code */}
        <div className="w-1/2 flex flex-col">
          <Tabs defaultValue="actions" className="flex-1 flex flex-col">
            <TabsList className="w-full justify-start rounded-none border-b px-4 h-12 bg-card/30">
              <TabsTrigger value="actions">操作记录</TabsTrigger>
              <TabsTrigger value="code">代码生成</TabsTrigger>
              <TabsTrigger value="output">运行输出</TabsTrigger>
            </TabsList>

            {/* Actions list */}
            <TabsContent value="actions" className="flex-1 m-0">
              <ScrollArea className="h-full">
                <div className="p-4 space-y-2">
                  {recordedActions.length === 0 ? (
                    <div className="text-center py-12">
                      <CircleDot className="w-12 h-12 mx-auto mb-4 text-muted-foreground/30" />
                      <p className="text-muted-foreground">暂无录制操作</p>
                      <p className="text-sm text-muted-foreground/60 mt-1">
                        点击"开始录制"后在屏幕上操作
                      </p>
                    </div>
                  ) : (
                    recordedActions.map((action, index) => (
                      <Card key={action.id} className="p-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-semibold text-sm">
                              {index + 1}
                            </div>
                            <div>
                              <p className="font-medium text-sm">{action.description}</p>
                              <p className="text-xs text-muted-foreground font-mono">
                                {action.type}
                                {Object.keys(action.params).length > 0 && (
                                  <> - {JSON.stringify(action.params)}</>
                                )}
                              </p>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                            onClick={() => setRecordedActions(prev => prev.filter(a => a.id !== action.id))}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Code generation */}
            <TabsContent value="code" className="flex-1 m-0">
              <div className="flex flex-col h-full">
                {codeTemplate ? (
                  <>
                    <div className="flex items-center justify-between p-4 border-b">
                      <div className="flex gap-2">
                        <Button 
                          variant={activeCodeTab === 'pytest' ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            setActiveCodeTab('pytest');
                            setGeneratedCode(codeTemplate.pytest);
                          }}
                          className="transition-all duration-200"
                        >
                          <Code className="w-3.5 h-3.5 mr-1.5" />
                          Pytest
                        </Button>
                        <Button
                          variant={activeCodeTab === 'yaml' ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            setActiveCodeTab('yaml');
                            setGeneratedCode(codeTemplate.yaml);
                          }}
                          className="transition-all duration-200"
                        >
                          <FileCode className="w-3.5 h-3.5 mr-1.5" />
                          YAML
                        </Button>
                      </div>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={handleCopyCode}
                          className="hover:bg-emerald-50 hover:border-emerald-300 hover:text-emerald-700 dark:hover:bg-emerald-900/20 dark:hover:border-emerald-700 dark:hover:text-emerald-300 transition-all duration-200"
                        >
                          <Copy className="w-3.5 h-3.5 mr-1.5" />
                          复制代码
                        </Button>
                        <Button
                          variant="default"
                          size="sm"
                          onClick={handleRunCode}
                          disabled={isRunning}
                          className="bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-md hover:shadow-lg transition-all duration-200"
                        >
                          {isRunning ? (
                            <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                          ) : (
                            <Play className="w-3.5 h-3.5 mr-1.5" />
                          )}
                          运行
                        </Button>
                      </div>
                    </div>
                    <ScrollArea className="flex-1">
                      <pre className="p-4 text-sm font-mono whitespace-pre-wrap">
                        {generatedCode}
                      </pre>
                    </ScrollArea>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center">
                      <Code className="w-12 h-12 mx-auto mb-4 text-muted-foreground/30" />
                      <p className="text-muted-foreground">暂无生成代码</p>
                      <p className="text-sm text-muted-foreground/60 mt-1">
                        录制操作后点击"生成代码"
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Run output */}
            <TabsContent value="output" className="flex-1 m-0">
              <ScrollArea className="h-full">
                <div className="p-4">
                  {runOutput ? (
                    <div className={`rounded-xl border-2 p-6 transition-all duration-300 ${
                      runOutput.success 
                        ? 'border-emerald-300 bg-gradient-to-br from-emerald-50 to-emerald-50/50 dark:border-emerald-700 dark:from-emerald-900/20 dark:to-emerald-900/10' 
                        : 'border-red-300 bg-gradient-to-br from-red-50 to-red-50/50 dark:border-red-700 dark:from-red-900/20 dark:to-red-900/10'
                    }`}>
                      <div className="flex items-center gap-3 mb-4">
                        {runOutput.success ? (
                          <>
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/40">
                              <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                            </div>
                            <span className="text-lg font-semibold text-emerald-700 dark:text-emerald-300">
                              ✓ 执行成功
                            </span>
                          </>
                        ) : (
                          <>
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/40">
                              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
                            </div>
                            <span className="text-lg font-semibold text-red-700 dark:text-red-300">
                              ✗ 执行失败
                            </span>
                          </>
                        )}
                      </div>
                      <div className="bg-zinc-900 dark:bg-zinc-950 rounded-lg p-4 border border-zinc-700 dark:border-zinc-800 overflow-x-auto">
                        <pre className="text-sm font-mono whitespace-pre-wrap text-zinc-200 dark:text-zinc-300 leading-relaxed">
                          {runOutput.output}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-16">
                      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-secondary/50 mx-auto mb-4">
                        <Play className="w-8 h-8 text-muted-foreground/40" />
                      </div>
                      <p className="text-lg font-medium text-muted-foreground">暂无运行输出</p>
                      <p className="text-sm text-muted-foreground/60 mt-2">
                        生成代码后点击"运行"查看输出
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
