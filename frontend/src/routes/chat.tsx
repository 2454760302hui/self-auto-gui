import { createFileRoute, Link } from '@tanstack/react-router';
import * as React from 'react';
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  connectWifi,
  disconnectWifi,
  listDevices,
  getConfig,
  saveConfig,
  testConfig,
  getErrorMessage,
  sendBack,
  sendHome,
  sendScroll,
  sendDoubleTap,
  sendLongPress,
  sendKeyEvent,
  sendTap,
  sendSwipe,
  sendPaste,
  sendSelectAll,
  sendClearText,
  sendTextInput,
  type Device,
  type ConfigSaveRequest,
  type ConfigTestResponse,
} from '../api';
import { Toast, type ToastType } from '../components/Toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Settings,
  CheckCircle2,
  Eye,
  EyeOff,
  Smartphone,
  RefreshCw,
  Monitor,
  Loader2,
  ChevronDown,
  ChevronUp,
  Zap,
  Image,
  FileJson,
  MessageSquare,
  Zap as ControlIcon,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  ArrowLeftIcon,
  ArrowRightIcon,
  Home,
  MousePointerClick,
  Hand,
  Volume2,
  VolumeX,
  Power,
  CornerDownLeft,
  Trash2,
  ClipboardPaste,
  ListChecks,
  AppWindow,
  BellOff,
  ScanLine,
  Layers,
  Search,
  Keyboard,
} from 'lucide-react';
import { useTranslation } from '../lib/i18n-context';
import { ChatPanel } from '../components/ChatPanel';
import { ControlPanel } from '../components/ControlPanel';

// 视觉模型预设配置
const DEFAULT_BASE_URL = 'https://open.bigmodel.cn/api/paas/v4';
const DEFAULT_MODEL_NAME = 'autoglm-phone';

type ElectronRelaunchAPI = {
  app?: {
    relaunch: () => Promise<{ success: boolean }>;
  };
};

export const Route = createFileRoute('/chat')({
  component: ChatComponent,
});

function ChatComponent() {
  const t = useTranslation();
  const [devices, setDevices] = useState<Device[]>([]);
  const [currentDeviceId, setCurrentDeviceId] = useState<string>('');
  const [mainMode, setMainMode] = useState<'chat' | 'control'>('chat');
  const [toast, setToast] = useState<{
    message: string;
    type: ToastType;
    visible: boolean;
  }>({ message: '', type: 'info', visible: false });

  const showToast = (message: string, type: ToastType = 'info') => {
    setToast({ message, type, visible: true });
  };

  const [quickActionLoading, setQuickActionLoading] = useState<string | null>(null);
  const [inputText, setInputText] = useState('');

  const execQuick = useCallback(async (label: string, fn: () => Promise<unknown>) => {
    if (!currentDeviceId) return;
    setQuickActionLoading(label);
    try { await fn(); }
    catch (e) { console.error(label, e); }
    finally { setQuickActionLoading(null); }
  }, [currentDeviceId]);

  const [config, setConfig] = useState<ConfigSaveRequest | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [testResult, setTestResult] = useState<ConfigTestResponse | null>(null);
  const [testing, setTesting] = useState(false);
  const [showJsonEditor, setShowJsonEditor] = useState(false);
  const [jsonText, setJsonText] = useState('');
  const isLoadingDevicesRef = useRef(false);
  const currentDeviceIdRef = useRef(currentDeviceId);
  useEffect(() => { currentDeviceIdRef.current = currentDeviceId; }, [currentDeviceId]);
  const [tempConfig, setTempConfig] = useState({
    base_url: DEFAULT_BASE_URL as string,
    model_name: DEFAULT_MODEL_NAME as string,
    api_key: '',
    agent_type: 'glm-async',
    agent_config_params: {} as Record<string, unknown>,
    default_max_steps: 100 as number | '',
    layered_max_turns: 50,
    decision_base_url: '',
    decision_model_name: '',
    decision_api_key: '',
    supports_vision: true,
  });

  useEffect(() => {
    const loadConfiguration = async () => {
      try {
        const data = await getConfig();
        const displayApiKey = data.api_key_masked || data.api_key || '';
        setConfig({
          base_url: data.base_url,
          model_name: data.model_name,
          api_key: displayApiKey || undefined,
          agent_type: data.agent_type || 'glm-async',
          agent_config_params: data.agent_config_params || undefined,
          default_max_steps: data.default_max_steps ?? null,
          layered_max_turns: data.layered_max_turns || 50,
          decision_base_url: data.decision_base_url || undefined,
          decision_model_name: data.decision_model_name || undefined,
          decision_api_key: displayApiKey || undefined,
        });
        const useDefault = !data.base_url;
        setTempConfig({
          base_url: useDefault ? DEFAULT_BASE_URL : data.base_url,
          model_name: useDefault ? DEFAULT_MODEL_NAME : data.model_name,
          api_key: displayApiKey,
          agent_type: data.agent_type || 'glm-async',
          agent_config_params: data.agent_config_params || {},
          default_max_steps: data.default_max_steps ?? '',
          layered_max_turns: data.layered_max_turns || 50,
          decision_base_url: data.decision_base_url || '',
          decision_model_name: data.decision_model_name || '',
          decision_api_key: displayApiKey,
          supports_vision: data.supports_vision !== false,
        });
        if (useDefault) {
          setShowConfig(true);
        }
      } catch {
        setShowConfig(true);
      }
    };
    loadConfiguration();
  }, []);

  const loadDevices = useCallback(async () => {
    if (isLoadingDevicesRef.current) return;
    isLoadingDevicesRef.current = true;
    try {
      const response = await listDevices();
      const connectedDevices = response.devices.filter(device => device.state !== 'disconnected');
      setDevices(connectedDevices);
      const currentId = currentDeviceIdRef.current;
      if (connectedDevices.length > 0 && !currentId) {
        setCurrentDeviceId(connectedDevices[0].id);
      }
    } catch (err) {
      console.error('Failed to load devices:', err);
    } finally {
      isLoadingDevicesRef.current = false;
    }
  }, []);

  useEffect(() => {
    loadDevices();
    const interval = setInterval(loadDevices, 10000);
    return () => clearInterval(interval);
  }, [loadDevices]);

  const handleSaveConfig = async () => {
    try {
      const saveResult = await saveConfig({
        base_url: tempConfig.base_url,
        model_name: tempConfig.model_name,
        api_key: tempConfig.api_key || undefined,
        agent_type: tempConfig.agent_type,
        agent_config_params: Object.keys(tempConfig.agent_config_params).length > 0 ? tempConfig.agent_config_params : undefined,
        default_max_steps: tempConfig.default_max_steps === '' ? null : tempConfig.default_max_steps,
        layered_max_turns: tempConfig.layered_max_turns,
        decision_base_url: tempConfig.decision_base_url || undefined,
        decision_model_name: tempConfig.decision_model_name || undefined,
        decision_api_key: tempConfig.decision_api_key || undefined,
        supports_vision: tempConfig.supports_vision,
      });
      showToast(t.toasts.configSaved, 'success');
      const electronApp = (window as Window & { electronAPI?: ElectronRelaunchAPI }).electronAPI?.app;
      if (saveResult.restart_required && electronApp?.relaunch) {
        showToast('配置已保存，应用将立即重启以应用新配置', 'warning');
        await new Promise(resolve => setTimeout(resolve, 600));
        await electronApp.relaunch();
        return;
      }
      setShowConfig(false);
    } catch (err) {
      showToast(`保存失败: ${getErrorMessage(err)}`, 'error');
    }
  };

  const handleTestConfig = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testConfig({
        base_url: tempConfig.base_url,
        api_key: tempConfig.api_key,
        model_name: tempConfig.model_name,
      });
      setTestResult(result);
      if (result.success && result.supports_vision !== undefined) {
        setTempConfig(prev => ({ ...prev, supports_vision: result.supports_vision! }));
      }
    } catch (err) {
      setTestResult({ success: false, error: getErrorMessage(err) });
    } finally {
      setTesting(false);
    }
  };

  const syncJsonToFields = (jsonStr: string) => {
    try {
      const parsed = JSON.parse(jsonStr);
      setTempConfig(prev => ({
        ...prev,
        base_url: parsed.base_url ?? prev.base_url,
        model_name: parsed.model_name ?? prev.model_name,
        api_key: parsed.api_key ?? prev.api_key,
        supports_vision: parsed.supports_vision ?? prev.supports_vision,
        default_max_steps: parsed.default_max_steps ?? prev.default_max_steps,
        layered_max_turns: parsed.layered_max_turns ?? prev.layered_max_turns,
      }));
    } catch { /* ignore parse errors while typing */ }
  };

  const syncFieldsToJson = () => {
    const obj: Record<string, unknown> = {
      base_url: tempConfig.base_url,
      model_name: tempConfig.model_name,
      api_key: tempConfig.api_key,
      supports_vision: tempConfig.supports_vision,
      default_max_steps: tempConfig.default_max_steps,
      layered_max_turns: tempConfig.layered_max_turns,
    };
    if (tempConfig.decision_base_url) obj.decision_base_url = tempConfig.decision_base_url;
    if (tempConfig.decision_model_name) obj.decision_model_name = tempConfig.decision_model_name;
    if (tempConfig.decision_api_key) obj.decision_api_key = tempConfig.decision_api_key;
    setJsonText(JSON.stringify(obj, null, 2));
  };

  const handleConnectWifi = async (deviceId: string) => {
    try {
      const res = await connectWifi({ device_id: deviceId });
      if (res.success && res.device_id) {
        setCurrentDeviceId(res.device_id);
        showToast(t.toasts.wifiConnected, 'success');
      } else {
        showToast(res.message || res.error || t.toasts.connectionFailed, 'error');
      }
    } catch {
      showToast(t.toasts.wifiConnectionError, 'error');
    }
  };

  const handleDisconnectWifi = async (deviceId: string) => {
    try {
      const res = await disconnectWifi(deviceId);
      if (res.success) {
        showToast(t.toasts.wifiDisconnected, 'success');
      } else {
        showToast(res.message || res.error || t.toasts.disconnectFailed, 'error');
      }
    } catch {
      showToast(t.toasts.wifiDisconnectError, 'error');
    }
  };

  const currentDevice = devices.find(d => d.id === currentDeviceId);

  return (
    <div className="h-screen flex flex-col bg-background">
      {toast.visible && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(prev => ({ ...prev, visible: false }))}
        />
      )}

      {/* 顶部导航栏 */}
      <header className="h-16 border-b border-border bg-card/80 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-40">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">A</span>
          </div>
          <h1 className="text-lg font-bold autoglm-gradient-text">Auto</h1>
        </div>

        <div className="flex-1 flex justify-center">
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary/50">
            <div className={`w-2 h-2 rounded-full ${
              currentDevice?.agent?.state === 'idle' ? 'bg-success animate-pulse' :
              currentDevice?.agent?.state === 'busy' ? 'bg-warning animate-pulse' :
              'bg-muted-foreground'
            }`} />
            <span className="text-sm text-foreground">
              {currentDevice ? `${currentDevice.display_name || currentDevice.model} - ${
                currentDevice.agent?.state === 'idle' ? '就绪' :
                currentDevice.agent?.state === 'busy' ? '运行中' :
                '未启动'
              }` : '未选择设备'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowConfig(true)}
            className="gap-2"
          >
            <Settings className="w-4 h-4" />
            设置
          </Button>
        </div>
      </header>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧设备面板 */}
        <div className="w-64 border-r border-border bg-background flex flex-col overflow-hidden">
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-sm">设备列表</h2>
                <p className="text-xs text-muted-foreground">
                  {devices.length} 台设备
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={loadDevices}
                title="刷新设备"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {devices.map(device => (
              <button
                key={device.id}
                onClick={() => setCurrentDeviceId(device.id)}
                className={`w-full text-left p-3 rounded-lg transition-all ${
                  device.id === currentDeviceId
                    ? 'bg-primary/10 border border-primary/30'
                    : 'hover:bg-secondary/50 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                    device.agent?.state === 'idle' ? 'bg-success' :
                    device.agent?.state === 'busy' ? 'bg-warning' :
                    'bg-muted-foreground'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-xs truncate">
                      {device.display_name || device.model}
                    </p>
                    <p className="text-xs text-muted-foreground truncate font-mono">
                      {device.serial}
                    </p>
                  </div>
                </div>
              </button>
            ))}

            {devices.length === 0 && (
              <div className="text-center py-8">
                <Smartphone className="w-8 h-8 mx-auto mb-2 text-muted-foreground/50" />
                <p className="text-xs text-muted-foreground">暂无设备</p>
              </div>
            )}
          </div>
        </div>

        {/* 右侧主内容区 */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          {currentDevice ? (
            <>
              <div className="px-6 py-4 border-b border-border bg-card/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${
                      currentDevice.agent?.state === 'idle' ? 'bg-success' :
                      currentDevice.agent?.state === 'busy' ? 'bg-warning animate-pulse' :
                      'bg-muted-foreground'
                    }`} />
                    <div>
                      <h3 className="font-semibold">
                        {currentDevice.display_name || currentDevice.model}
                      </h3>
                      <p className="text-xs text-muted-foreground font-mono">
                        {currentDevice.serial}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="default"
                      size="sm"
                      asChild
                      className="gap-1 text-xs"
                    >
                      <Link to="/cast" search={{ serial: currentDevice.serial }} target="_blank">
                        <Monitor className="w-3.5 h-3.5" />
                        投屏
                      </Link>
                    </Button>
                  </div>
                </div>
              </div>

              {/* 自动化快捷操作栏 */}
              <div className="border-b border-border bg-card/30 px-4 py-2 overflow-x-auto">
                <div className="flex items-center gap-1 min-w-max">
                  <span className="text-[10px] text-muted-foreground font-medium mr-1 shrink-0">快捷操作</span>
                  {/* 导航 */}
                  {[
                    { label: '返回', icon: ArrowLeft, fn: () => sendBack(currentDevice.id) },
                    { label: '主页', icon: Home, fn: () => sendHome(currentDevice.id) },
                    { label: '最近', icon: AppWindow, fn: () => sendKeyEvent(187, currentDevice.id) },
                  ].map(({ label, icon: Icon, fn }) => (
                    <button key={label} onClick={() => execQuick(label, fn)}
                      disabled={quickActionLoading !== null}
                      className="flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg hover:bg-secondary/70 transition-colors min-w-[44px] text-emerald-600 border border-emerald-200/50 hover:border-emerald-300">
                      {quickActionLoading === label ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                      <span className="text-[9px] leading-none">{label}</span>
                    </button>
                  ))}
                  <div className="w-px h-6 bg-border mx-0.5" />
                  {/* 滑动 */}
                  {[
                    { label: '上滑', icon: ArrowUp, fn: () => sendScroll('up', 500, currentDevice.id), cls: 'text-blue-600 border-blue-200/50 hover:border-blue-300' },
                    { label: '下滑', icon: ArrowDown, fn: () => sendScroll('down', 500, currentDevice.id), cls: 'text-green-600 border-green-200/50 hover:border-green-300' },
                    { label: '左滑', icon: ArrowLeftIcon, fn: () => sendScroll('left', 500, currentDevice.id), cls: 'text-purple-600 border-purple-200/50 hover:border-purple-300' },
                    { label: '右滑', icon: ArrowRightIcon, fn: () => sendScroll('right', 500, currentDevice.id), cls: 'text-orange-600 border-orange-200/50 hover:border-orange-300' },
                  ].map(({ label, icon: Icon, fn, cls }) => (
                    <button key={label} onClick={() => execQuick(label, fn)}
                      disabled={quickActionLoading !== null}
                      className={`flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg hover:bg-secondary/70 transition-colors min-w-[44px] border ${cls}`}>
                      {quickActionLoading === label ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                      <span className="text-[9px] leading-none">{label}</span>
                    </button>
                  ))}
                  <div className="w-px h-6 bg-border mx-0.5" />
                  {/* 触控 */}
                  {[
                    { label: '双击', icon: MousePointerClick, fn: () => sendDoubleTap(540, 960, currentDevice.id) },
                    { label: '长按', icon: Hand, fn: () => sendLongPress(540, 960, 3000, currentDevice.id) },
                  ].map(({ label, icon: Icon, fn }) => (
                    <button key={label} onClick={() => execQuick(label, fn)}
                      disabled={quickActionLoading !== null}
                      className="flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg hover:bg-secondary/70 transition-colors min-w-[44px] text-purple-600 border border-purple-200/50 hover:border-purple-300">
                      {quickActionLoading === label ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                      <span className="text-[9px] leading-none">{label}</span>
                    </button>
                  ))}
                  <div className="w-px h-6 bg-border mx-0.5" />
                  {/* 输入 */}
                  <div className="flex items-center gap-1">
                    <input
                      value={inputText}
                      onChange={e => setInputText(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter' && inputText) { execQuick('输入', () => sendTextInput(inputText, currentDevice.id).then(() => setInputText(''))); } }}
                      placeholder="输入文字..."
                      className="h-7 w-28 text-[10px] px-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button onClick={() => inputText && execQuick('输入', () => sendTextInput(inputText, currentDevice.id).then(() => setInputText('')))}
                      disabled={!inputText || quickActionLoading !== null}
                      className="flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg hover:bg-secondary/70 transition-colors min-w-[44px] text-amber-600 border border-amber-200/50 hover:border-amber-300 disabled:opacity-40">
                      {quickActionLoading === '输入' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Keyboard className="w-3.5 h-3.5" />}
                      <span className="text-[9px] leading-none">输入</span>
                    </button>
                  </div>
                  <div className="w-px h-6 bg-border mx-0.5" />
                  {/* 编辑 */}
                  {[
                    { label: '粘贴', icon: ClipboardPaste, fn: () => sendPaste(currentDevice.id) },
                    { label: '全选', icon: ListChecks, fn: () => sendSelectAll(currentDevice.id) },
                    { label: '清除', icon: Trash2, fn: () => sendClearText(currentDevice.id) },
                  ].map(({ label, icon: Icon, fn }) => (
                    <button key={label} onClick={() => execQuick(label, fn)}
                      disabled={quickActionLoading !== null}
                      className="flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg hover:bg-secondary/70 transition-colors min-w-[44px] text-slate-600 border border-slate-200/50 hover:border-slate-300">
                      {quickActionLoading === label ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                      <span className="text-[9px] leading-none">{label}</span>
                    </button>
                  ))}
                  <div className="w-px h-6 bg-border mx-0.5" />
                  {/* 按键 */}
                  {[
                    { label: '音量+', icon: Volume2, fn: () => sendKeyEvent(24, currentDevice.id) },
                    { label: '音量-', icon: VolumeX, fn: () => sendKeyEvent(25, currentDevice.id) },
                    { label: '电源', icon: Power, fn: () => sendKeyEvent(26, currentDevice.id) },
                    { label: '回车', icon: CornerDownLeft, fn: () => sendKeyEvent(66, currentDevice.id) },
                    { label: '删除', icon: Trash2, fn: () => sendKeyEvent(67, currentDevice.id) },
                    { label: 'Tab', icon: Layers, fn: () => sendKeyEvent(61, currentDevice.id) },
                    { label: '搜索', icon: Search, fn: () => sendKeyEvent(84, currentDevice.id) },
                  ].map(({ label, icon: Icon, fn }) => (
                    <button key={label} onClick={() => execQuick(label, fn)}
                      disabled={quickActionLoading !== null}
                      className="flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg hover:bg-secondary/70 transition-colors min-w-[44px] text-rose-600 border border-rose-200/50 hover:border-rose-300">
                      {quickActionLoading === label ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                      <span className="text-[9px] leading-none">{label}</span>
                    </button>
                  ))}
                  <div className="w-px h-6 bg-border mx-0.5" />
                  {/* 系统 */}
                  {[
                    { label: '锁屏', icon: BellOff, fn: () => sendKeyEvent(26, currentDevice.id) },
                    { label: '截屏', icon: ScanLine, fn: () => sendKeyEvent(120, currentDevice.id) },
                    { label: '下拉通知', icon: ChevronDown, fn: () => sendSwipe(540, 0, 540, 800, 300, currentDevice.id) },
                    { label: '关闭通知', icon: ChevronUp, fn: () => sendSwipe(540, 800, 540, 0, 300, currentDevice.id) },
                  ].map(({ label, icon: Icon, fn }) => (
                    <button key={label} onClick={() => execQuick(label, fn)}
                      disabled={quickActionLoading !== null}
                      className="flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg hover:bg-secondary/70 transition-colors min-w-[44px] text-indigo-600 border border-indigo-200/50 hover:border-indigo-300">
                      {quickActionLoading === label ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                      <span className="text-[9px] leading-none">{label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex-1 min-h-0 overflow-auto">
                {mainMode === 'chat' ? (
                  <div className="h-full p-6">
                    <ChatPanel
                      deviceId={currentDevice.id}
                      deviceSerial={currentDevice.serial}
                      deviceName={currentDevice.display_name || currentDevice.model}
                      deviceConnectionType={currentDevice.connection_type}
                      isConfigured={!!config?.base_url}
                      unlimitedStepsEnabled={config?.default_max_steps === null}
                    />
                  </div>
                ) : (
                  <div className="h-full p-6">
                    <ControlPanel
                      deviceId={currentDevice.id}
                      deviceName={currentDevice.display_name || currentDevice.model}
                      deviceSerial={currentDevice.serial}
                    />
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Smartphone className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
                <h3 className="font-semibold text-lg mb-2">未选择设备</h3>
                <p className="text-muted-foreground text-sm mb-6">
                  请从左侧选择一台设备开始使用
                </p>
                <Button variant="outline" onClick={loadDevices}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  刷新设备
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 配置对话框 */}
      <Dialog open={showConfig} onOpenChange={setShowConfig}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>API 配置</DialogTitle>
            <DialogDescription>设置 AI 模型连接参数</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label className="text-sm">Base URL</Label>
              <Input
                value={tempConfig.base_url}
                onChange={e => setTempConfig({ ...tempConfig, base_url: e.target.value })}
                placeholder="https://api.example.com/v1"
              />
              <p className="text-xs text-muted-foreground">OpenAI 兼容 API 地址</p>
            </div>

            <div className="space-y-1.5">
              <Label className="text-sm">API Key <span className="text-red-500">*</span></Label>
              <div className="relative">
                <Input
                  type={showApiKey ? 'text' : 'password'}
                  value={tempConfig.api_key}
                  onChange={e => setTempConfig({ ...tempConfig, api_key: e.target.value })}
                  placeholder="输入您的 API Key"
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                >
                  {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-sm">Model</Label>
              <Input
                value={tempConfig.model_name}
                onChange={e => setTempConfig({ ...tempConfig, model_name: e.target.value })}
                placeholder="model-name"
              />
              <p className="text-xs text-muted-foreground">模型名称（如 glm-4.7、gpt-4o 等）</p>
            </div>

            <div className="space-y-2">
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={handleTestConfig}
                disabled={testing || !tempConfig.base_url || !tempConfig.api_key}
              >
                {testing ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />测试中...</>
                ) : (
                  <><Zap className="w-4 h-4 mr-2" />测试连接</>
                )}
              </Button>

              {testResult && (
                <div className={`rounded-lg border p-3 text-sm ${
                  testResult.success ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950' : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950'
                }`}>
                  {testResult.success ? (
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-green-700 dark:text-green-400">
                          连接成功
                        </span>
                        {testResult.response_time_ms !== undefined && (
                          <span className="text-xs text-muted-foreground">
                            {testResult.response_time_ms < 1000
                              ? `${Math.round(testResult.response_time_ms)}ms`
                              : `${(testResult.response_time_ms / 1000).toFixed(1)}s`}
                          </span>
                        )}
                      </div>
                      {testResult.supports_vision !== undefined && (
                        <div className={`flex items-center gap-1.5 text-xs ${
                          testResult.supports_vision
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}>
                          {testResult.supports_vision ? (
                            <><Image className="w-3.5 h-3.5" /> <span className="font-medium">支持视觉</span> — 模型可以分析截图</>
                          ) : (
                            <><FileJson className="w-3.5 h-3.5" /> <span className="font-medium">不支持视觉</span> — 将使用 UI 元素列表模式</>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-red-600 dark:text-red-400">
                      连接失败: {testResult.error}
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium">视觉模式</Label>
                <p className="text-xs text-muted-foreground">
                  {tempConfig.supports_vision
                    ? '模型支持图像识别，通过截图分析屏幕'
                    : '模型不支持图像，通过 UI 元素列表分析屏幕'}
                </p>
              </div>
              <Switch
                checked={tempConfig.supports_vision}
                onCheckedChange={(checked: boolean) =>
                  setTempConfig(prev => ({ ...prev, supports_vision: checked }))
                }
              />
            </div>

            <div className="space-y-2">
              <button
                type="button"
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                onClick={() => {
                  if (!showJsonEditor) syncFieldsToJson();
                  setShowJsonEditor(!showJsonEditor);
                }}
              >
                {showJsonEditor ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                <FileJson className="w-3.5 h-3.5" />
                高级配置 (JSON)
              </button>
              {showJsonEditor && (
                <textarea
                  className="w-full h-48 rounded-md border border-border bg-muted/50 p-3 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                  value={jsonText}
                  onChange={e => {
                    setJsonText(e.target.value);
                    syncJsonToFields(e.target.value);
                  }}
                  spellCheck={false}
                />
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfig(false)}>
              取消
            </Button>
            <Button onClick={handleSaveConfig} disabled={!tempConfig.api_key}>
              <CheckCircle2 className="w-4 h-4 mr-2" />
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
