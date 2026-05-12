import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  ArrowLeft, ArrowUp, ArrowDown, ArrowLeftIcon, ArrowRightIcon,
  Home, Copy, ClipboardPaste, ListChecks, Trash2, Loader2,
  Camera, FileSearch, Smartphone, Zap, CirclePlay, CircleStop,
  Play, Search, X, Film, Monitor, MousePointerClick,
  Volume2, VolumeX, Power, Menu, CornerDownLeft, RefreshCw,
  Clipboard, Hand, ScanLine, AppWindow, Layers,
  BellOff, ChevronUp, ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  sendBack, sendHome, sendDoubleTap, sendLongPress, sendClearText,
  sendScroll, getControlScreenshot, getUiDump, getCurrentApp,
  getClipboard, sendPaste, sendSelectAll, sendLaunchApp,
  sendKeyEvent, sendTap, sendSwipe, getInstalledApps,
  runPytest, generateGif, startScreenRecord, stopScreenRecord,
  type ScreenshotControlResponse, type UiDumpResponse,
  type InstalledAppsResponse, type InstalledAppInfo, type PytestRunResponse,
} from '../api';
import { ImagePreview } from '@/components/ui/image-preview';

interface QuickControlPanelProps { deviceId: string; deviceName: string; }
interface RecordedAction { type: string; params: Record<string, unknown>; label: string; }
type TabKey = 'control' | 'elements' | 'apps';

function buildPytestCode(actions: RecordedAction[], deviceId: string): string {
  const header = [
    '"""Auto-generated device control test."""',
    'import subprocess, time',
    `DEVICE_ID = "${deviceId}"`,
    'def adb(cmd): subprocess.run(["adb","-s",DEVICE_ID,"shell",cmd],check=True)',
    'def tap(x,y): adb(f"input tap {x} {y}"); time.sleep(0.8)',
    'def dtap(x,y): tap(x,y); time.sleep(0.1); tap(x,y)',
    'def lpress(x,y,d=3000): adb(f"input swipe {x} {y} {x} {y} {d}"); time.sleep(1)',
    'def swipe(sx,sy,ex,ey,d=300): adb(f"input swipe {sx} {sy} {ex} {ey} {d}"); time.sleep(0.8)',
    'def scroll_up(): swipe(540,1500,540,500)',
    'def scroll_down(): swipe(540,500,540,1500)',
    'def scroll_left(): swipe(900,960,100,960)',
    'def scroll_right(): swipe(100,960,900,960)',
    'def back(): adb("input keyevent 4"); time.sleep(0.5)',
    'def home(): adb("input keyevent 3"); time.sleep(0.5)',
    'def launch(pkg): adb(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"); time.sleep(2)',
    "def text(t): adb(f'input text \"{t}\"'); time.sleep(0.5)",
    'def key(k): adb(f"input keyevent {k}"); time.sleep(0.5)',
    '',
  ];
  const steps = actions.length === 0 ? ['# no actions recorded'] : actions.map(a => {
    const p = a.params;
    switch (a.type) {
      case 'tap': return `tap(${p.x}, ${p.y})`;
      case 'double_tap': return `dtap(${p.x}, ${p.y})`;
      case 'long_press': return `lpress(${p.x}, ${p.y}, ${p.duration||3000})`;
      case 'scroll': return `scroll_${p.direction}()`;
      case 'swipe': return `swipe(${p.start_x},${p.start_y},${p.end_x},${p.end_y},${p.duration||300})`;
      case 'back': return 'back()';
      case 'home': return 'home()';
      case 'launch': return `launch("${(p.app as string).replace(/"/g,'\\"')}")`;
      case 'type_text': return `text("${(p.text as string).replace(/"/g,'\\"')}")`;
      case 'keyevent': return `key(${p.keycode})`;
      default: return `# ${a.type}: ${JSON.stringify(p)}`;
    }
  });
  return [...header, ...steps].join('\n');
}

function buildYamlCode(actions: RecordedAction[], deviceId: string): string {
  const steps = actions.map(a => {
    const p = a.params;
    const action = a.type;
    let step = `  - action: ${action}`;
    
    if (action === 'tap') {
      step += `\n    x: ${p.x}\n    y: ${p.y}`;
    } else if (action === 'double_tap') {
      step += `\n    x: ${p.x}\n    y: ${p.y}`;
    } else if (action === 'long_press') {
      step += `\n    x: ${p.x}\n    y: ${p.y}\n    duration: ${p.duration || 3000}`;
    } else if (action === 'swipe') {
      step += `\n    start_x: ${p.start_x}\n    start_y: ${p.start_y}\n    end_x: ${p.end_x}\n    end_y: ${p.end_y}\n    duration: ${p.duration || 300}`;
    } else if (action === 'scroll') {
      step += `\n    direction: ${p.direction}\n    distance: ${p.distance || 500}`;
    } else if (action === 'launch') {
      step += `\n    app: ${(p.app as string).replace(/"/g, '\\"')}`;
    } else if (action === 'type_text') {
      step += `\n    text: ${(p.text as string).replace(/"/g, '\\"')}`;
    } else if (action === 'keyevent') {
      step += `\n    keycode: ${p.keycode}`;
    }
    
    return step;
  });

  return `device_id: ${deviceId}\nsteps:\n${steps.join('\n')}`;
}

export function QuickControlPanel({ deviceId, deviceName }: QuickControlPanelProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [screenshot, setScreenshot] = useState<ScreenshotControlResponse | null>(null);
  const [uiElements, setUiElements] = useState<UiDumpResponse | null>(null);
  const [currentApp, setCurrentApp] = useState<string>('');
  const [clipboardText, setClipboardText] = useState('');
  const [activeTab, setActiveTab] = useState<TabKey>('control');
  const [apps, setApps] = useState<InstalledAppsResponse | null>(null);
  const [appTab, setAppTab] = useState<'third_party' | 'system'>('third_party');
  const [appSearch, setAppSearch] = useState('');
  const [recording, setRecording] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [actions, setActions] = useState<RecordedAction[]>([]);
  const [recordedScreenshots, setRecordedScreenshots] = useState<string[]>([]);
  const [pytestCode, setPytestCode] = useState('');
  const [yamlCode, setYamlCode] = useState('');
  const [pytestResult, setPytestResult] = useState<PytestRunResponse | null>(null);
  const [gifData, setGifData] = useState<string | null>(null);
  const [gifLoading, setGifLoading] = useState(false);
  const screenImgRef = useRef<HTMLImageElement>(null);
  const [mirrorShot, setMirrorShot] = useState<ScreenshotControlResponse | null>(null);
  const [dragStart, setDragStart] = useState<{ cx: number; cy: number } | null>(null);
  const [touchMode, setTouchMode] = useState<'tap' | 'long_press'>('tap');
  const [mirrorLoading, setMirrorLoading] = useState(false);


  const recordAction = useCallback((type: string, params: Record<string, unknown>, label: string) => {
    if (recording) setActions(prev => [...prev, { type, params, label }]);
  }, [recording]);

  const exec = useCallback(async (label: string, fn: () => Promise<void>, rec?: { type: string; params: Record<string, unknown> }) => {
    setLoading(label);
    try { await fn(); if (rec) recordAction(rec.type, rec.params, label); }
    catch (e) { console.error(label, e); }
    finally { setLoading(null); }
  }, [recordAction]);

  const refreshMirror = useCallback(async (gif = false) => {
    await new Promise(r => setTimeout(r, 500));
    const res = await getControlScreenshot(deviceId);
    if (res.success) { setMirrorShot(res); if (gif && recording) setRecordedScreenshots(p => [...p, res.image!]); }
  }, [deviceId, recording]);

  const getCoords = useCallback((cx: number, cy: number) => {
    if (!screenImgRef.current || !mirrorShot) return null;
    const r = screenImgRef.current.getBoundingClientRect();
    return { x: Math.round((cx - r.left) * mirrorShot.width / r.width), y: Math.round((cy - r.top) * mirrorShot.height / r.height) };
  }, [mirrorShot]);

  useEffect(() => {
    if (showModal && !mirrorShot) getControlScreenshot(deviceId).then(r => { if (r.success) setMirrorShot(r); });
  }, [showModal, deviceId, mirrorShot]);

  useEffect(() => {
    if (recording) {
      setPytestCode(buildPytestCode(actions, deviceId));
      setYamlCode(buildYamlCode(actions, deviceId));
    }
  }, [actions, recording, deviceId]);

  const handleScreenshot = () => exec('截图', async () => { const r = await getControlScreenshot(deviceId); if (r.success) setScreenshot(r); });
  const handleUiDump = () => exec('UI分析', async () => { const r = await getUiDump(deviceId); if (r.success) { setUiElements(r); setActiveTab('elements'); } });
  const handleCurrentApp = () => exec('当前App', async () => { const r = await getCurrentApp(deviceId); if (r.success) setCurrentApp(r.app_name || '未知'); });
  const handleGetClipboard = () => exec('获取剪贴板', async () => { const r = await getClipboard(deviceId); if (r.success) setClipboardText(r.text || ''); });
  const handleScroll = (dir: 'up'|'down'|'left'|'right') => {
    const lbl = ({up:'上滑',down:'下滑',left:'左滑',right:'右滑'})[dir];
    exec(lbl, () => sendScroll(dir, 500, deviceId).then(()=>{}), {type:'scroll',params:{direction:dir,distance:500}});
  };
  const handleKey = (kc: number, lbl: string) => exec(lbl, () => sendKeyEvent(kc, deviceId).then(()=>{}), {type:'keyevent',params:{keycode:kc}});
  const handleLoadApps = () => exec('获取应用', async () => { const r = await getInstalledApps(deviceId); if (r.success) { setApps(r); setActiveTab('apps'); } });
  const handleLaunchPkg = (pkg: string) => exec('启动', () => sendLaunchApp(pkg, deviceId).then(()=>{}), {type:'launch',params:{app:pkg}});

  const onMouseDown = (e: React.MouseEvent) => { e.preventDefault(); setDragStart({cx:e.clientX,cy:e.clientY}); };
  const onMouseUp = async (e: React.MouseEvent) => {
    if (!dragStart) return;
    const s = getCoords(dragStart.cx, dragStart.cy);
    const en = getCoords(e.clientX, e.clientY);
    if (!s || !en) { setDragStart(null); return; }
    const dist = Math.hypot(en.x-s.x, en.y-s.y);
    setMirrorLoading(true);
    try {
      if (dist < 30) {
        if (touchMode === 'long_press') { await sendLongPress(s.x, s.y, 3000, deviceId); recordAction('long_press', {x:s.x,y:s.y,duration:3000}, `长按(${s.x},${s.y})`); }
        else { await sendTap(s.x, s.y, deviceId); recordAction('tap', {x:s.x,y:s.y}, `点击(${s.x},${s.y})`); }
      } else { await sendSwipe(s.x, s.y, en.x, en.y, 300, deviceId); recordAction('swipe', {start_x:s.x,start_y:s.y,end_x:en.x,end_y:en.y,duration:300}, `滑动(${s.x},${s.y})→(${en.x},${en.y})`); }
      refreshMirror(true);
    } catch(e){ console.error(e); } finally { setDragStart(null); setMirrorLoading(false); }
  };
  const mirrorScroll = async (dir: 'up'|'down'|'left'|'right') => {
    setMirrorLoading(true);
    try { await sendScroll(dir, 500, deviceId); recordAction('scroll', {direction:dir,distance:500}, ({up:'上滑',down:'下滑',left:'左滑',right:'右滑'})[dir]); refreshMirror(true); }
    catch(e){console.error(e);} finally{setMirrorLoading(false);}
  };
  const mirrorNav = async (type: 'back'|'home') => {
    setMirrorLoading(true);
    try { await (type==='back' ? sendBack : sendHome)(deviceId); recordAction(type, {}, type==='back' ? '返回' : '主页'); refreshMirror(true); }
    catch(e){console.error(e);} finally{setMirrorLoading(false);}
  };

  const startRecording = async () => {
    // Start recording on backend
    const startRes = await startScreenRecord(deviceId);
    if (!startRes.success) {
      console.error('Failed to start recording:', startRes.error);
      return;
    }
    
    setRecording(true);
    setActions([]);
    setRecordedScreenshots([]);
    setGifData(null);
    setPytestResult(null);
    setMirrorShot(null);
    setPytestCode(buildPytestCode([], deviceId));
    setShowModal(true);
  };
  
  const stopRecording = async () => {
    // Stop recording on backend
    const stopRes = await stopScreenRecord(deviceId);
    if (stopRes.success) {
      setRecording(false);
      setPytestCode(stopRes.pytest_code || buildPytestCode(actions, deviceId));
      // Optionally save to file or show YAML code
      console.log('Recording stopped. Pytest code generated.');
    } else {
      console.error('Failed to stop recording:', stopRes.error);
      setRecording(false);
    }
  };
  const closeModal = () => { if (recording) stopRecording(); setShowModal(false); };
  const handleRunCode = () => exec('运行', async () => { setPytestResult(await runPytest(pytestCode)); });
  const handleGif = async () => {
    if (!recordedScreenshots.length) return;
    setGifLoading(true);
    try { const r = await generateGif(recordedScreenshots, 500); if (r.success) setGifData(r.gif); }
    catch(e){console.error(e);} finally{setGifLoading(false);}
  };

  const btn = (label: string, Icon: React.ElementType, onClick: () => void, cls = '') => (
    <Button key={label} variant="outline" size="sm" className={`h-14 text-[11px] gap-1 flex-col py-1 px-1 ${cls}`} onClick={onClick} disabled={loading !== null}>
      {loading === label ? <Loader2 className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
      <span className="text-[9px] leading-none text-center">{label}</span>
    </Button>
  );

  const filteredApps = apps ? (apps[appTab]||[]).filter((a: InstalledAppInfo) => !appSearch || a.package_name.toLowerCase().includes(appSearch.toLowerCase()) || (a.app_name && a.app_name.toLowerCase().includes(appSearch.toLowerCase()))) : [];
  const tabs = [{key:'control' as TabKey, label:'控制', icon:Zap},{key:'elements' as TabKey, label:'元素', icon:FileSearch},{key:'apps' as TabKey, label:'应用', icon:Smartphone}];


  return (<>
    <Card className="flex flex-col h-full border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between p-2 border-b border-border bg-card">
        <div className="flex items-center gap-1.5">
          <div className="w-6 h-6 rounded bg-amber-500/10 flex items-center justify-center"><Zap className="h-3 w-3 text-amber-500" /></div>
          <div><h2 className="font-semibold text-[11px]">快速控制</h2><p className="text-[9px] text-muted-foreground">{deviceName}</p></div>
        </div>
        <div className="flex items-center gap-1">
          {currentApp && <Badge variant="secondary" className="text-[9px] h-4"><Smartphone className="w-2 h-2 mr-0.5" />{currentApp}</Badge>}
          <Button variant="outline" size="sm" className="h-6 text-[10px] gap-0.5 border-red-200 text-red-600 hover:bg-red-50" onClick={startRecording}>
            <CirclePlay className="w-3 h-3" />录屏
          </Button>
        </div>
      </div>
      <div className="flex border-b border-border bg-card/50">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex-1 flex items-center justify-center gap-0.5 py-1 text-[10px] font-medium transition-all border-b-2 ${activeTab===t.key?'text-primary border-primary':'text-muted-foreground border-transparent hover:text-foreground'}`}>
            <t.icon className="w-3 h-3" />{t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {activeTab === 'control' && (<>
          {screenshot?.success && screenshot.image && (
            <div className="rounded-lg overflow-hidden border border-border">
              <ImagePreview src={`data:image/png;base64,${screenshot.image}`} alt="Screenshot" maxHeight="160px" />
              <div className="flex items-center justify-between px-1 py-0.5 bg-secondary/50">
                <span className="text-[9px] text-muted-foreground">{screenshot.width}×{screenshot.height}</span>
                <Button variant="ghost" size="sm" className="h-4 text-[9px] px-1" onClick={() => setScreenshot(null)}>关闭</Button>
              </div>
            </div>
          )}
          <section>
            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">基础操作</p>
            <div className="grid grid-cols-4 gap-1">
              {btn('截图', Camera, handleScreenshot)}
              {btn('UI分析', FileSearch, handleUiDump)}
              {btn('当前App', Smartphone, handleCurrentApp)}
              {btn('刷新截图', RefreshCw, handleScreenshot)}
            </div>
          </section>
          <section>
            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">导航</p>
            <div className="grid grid-cols-4 gap-1">
              {btn('返回', ArrowLeft, () => exec('返回', () => sendBack(deviceId).then(()=>{}), {type:'back',params:{}}))}
              {btn('主页', Home, () => exec('主页', () => sendHome(deviceId).then(()=>{}), {type:'home',params:{}}))}
              {btn('双击', MousePointerClick, () => exec('双击', () => sendDoubleTap(540,960,deviceId).then(()=>{}), {type:'double_tap',params:{x:540,y:960}}))}
              {btn('长按', Hand, () => exec('长按', () => sendLongPress(540,960,3000,deviceId).then(()=>{}), {type:'long_press',params:{x:540,y:960,duration:3000}}))}
            </div>
          </section>
          <section>
            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">滑动</p>
            <div className="grid grid-cols-4 gap-1">
              {btn('上滑', ArrowUp, () => handleScroll('up'), 'text-blue-600 border-blue-200 hover:bg-blue-50')}
              {btn('下滑', ArrowDown, () => handleScroll('down'), 'text-green-600 border-green-200 hover:bg-green-50')}
              {btn('左滑', ArrowLeftIcon, () => handleScroll('left'), 'text-purple-600 border-purple-200 hover:bg-purple-50')}
              {btn('右滑', ArrowRightIcon, () => handleScroll('right'), 'text-orange-600 border-orange-200 hover:bg-orange-50')}
            </div>
          </section>
          <section>
            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">剪贴板 & 编辑</p>
            <div className="grid grid-cols-4 gap-1">
              {btn('粘贴', ClipboardPaste, () => exec('粘贴', () => sendPaste(deviceId).then(()=>{}), {type:'paste',params:{}}))}
              {btn('全选', ListChecks, () => exec('全选', () => sendSelectAll(deviceId).then(()=>{}), {type:'select_all',params:{}}))}
              {btn('清除文字', Trash2, () => exec('清除文字', () => sendClearText(deviceId).then(()=>{}), {type:'clear_text',params:{}}))}
              {btn('获取剪贴板', Clipboard, handleGetClipboard)}
            </div>
            {clipboardText && <div className="mt-1 p-1.5 bg-secondary/50 rounded text-[10px] break-all"><span className="text-muted-foreground">剪贴板：</span><span className="font-mono">{clipboardText}</span></div>}
          </section>
          <section>
            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">按键事件</p>
            <div className="grid grid-cols-4 gap-1">
              {btn('音量+', Volume2, () => handleKey(24,'音量+'))}
              {btn('音量-', VolumeX, () => handleKey(25,'音量-'))}
              {btn('电源键', Power, () => handleKey(26,'电源键'))}
              {btn('菜单键', Menu, () => handleKey(82,'菜单键'))}
              {btn('回车', CornerDownLeft, () => handleKey(66,'回车'))}
              {btn('删除', Trash2, () => handleKey(67,'删除'))}
              {btn('Tab键', Layers, () => handleKey(61,'Tab键'))}
              {btn('搜索键', Search, () => handleKey(84,'搜索键'))}
            </div>
          </section>
          <section>
            <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">系统操作</p>
            <div className="grid grid-cols-4 gap-1">
              {btn('锁屏', BellOff, () => handleKey(26,'锁屏'))}
              {btn('截屏', ScanLine, () => handleKey(120,'截屏'))}
              {btn('最近任务', AppWindow, () => handleKey(187,'最近任务'))}
              {btn('下拉通知', ChevronDown, () => exec('下拉通知', async () => { await sendSwipe(540,0,540,800,300,deviceId); }, {type:'swipe',params:{start_x:540,start_y:0,end_x:540,end_y:800,duration:300}}))}
              {btn('关闭通知', ChevronUp, () => exec('关闭通知', async () => { await sendSwipe(540,800,540,0,300,deviceId); }, {type:'swipe',params:{start_x:540,start_y:800,end_x:540,end_y:0,duration:300}}))}
              {btn('获取应用', Smartphone, handleLoadApps)}
            </div>
          </section>
        </>)}
        {activeTab === 'elements' && (<>
          {!uiElements?.success || !uiElements.elements || uiElements.elements.length === 0 ? (
            <div className="text-center py-6">
              <FileSearch className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-[11px] text-muted-foreground mb-2">点击"UI分析"获取元素列表</p>
              {btn('UI分析', FileSearch, handleUiDump)}
            </div>
          ) : (
            <section>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-muted-foreground">{uiElements.elements.length} 个元素</span>
                <Button variant="ghost" size="sm" className="h-4 text-[9px] px-1" onClick={() => setUiElements(null)}><X className="w-2.5 h-2.5" /></Button>
              </div>
              <div className="max-h-[calc(100vh-240px)] overflow-y-auto rounded-lg border border-border">
                <table className="w-full text-[10px]">
                  <thead className="bg-secondary/50 sticky top-0">
                    <tr><th className="p-1 text-left">文本</th><th className="p-1 text-left">类型</th><th className="p-1 text-center">可点击</th><th className="p-1 text-center">操作</th></tr>
                  </thead>
                  <tbody>
                    {uiElements.elements.map((el, idx) => {
                      const isClickable = !!el.clickable;
                      const hasCenter = el.center && el.center.length >= 2;
                      return (
                        <tr key={idx} className={`border-t border-border ${isClickable?'bg-emerald-50/50 dark:bg-emerald-950/20 cursor-pointer hover:bg-emerald-100/50':'opacity-60'}`}
                          onClick={() => { if (!isClickable||!hasCenter) return; const [x,y]=el.center!; exec('点击',async()=>{await sendTap(x,y,deviceId);},{type:'tap',params:{x,y}}); }}>
                          <td className="p-1 max-w-[100px] truncate">{el.text||el.content_desc||'-'}</td>
                          <td className="p-1">{el.class_name?.split('.').pop()||'-'}</td>
                          <td className="p-1 text-center">{isClickable?<Badge className="bg-emerald-100 text-emerald-700 text-[9px] h-3.5 px-1">Yes</Badge>:<Badge variant="secondary" className="text-[9px] h-3.5 px-1">No</Badge>}</td>
                          <td className="p-1 text-center">{isClickable&&hasCenter&&<Button variant="ghost" size="sm" className="h-4 text-[9px] px-0.5" onClick={e=>{e.stopPropagation();const[x,y]=el.center!;exec('点击',async()=>{await sendTap(x,y,deviceId);},{type:'tap',params:{x,y}});}} disabled={loading!==null}>点击</Button>}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>)}
        {activeTab === 'apps' && (<>
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground">应用管理</span>
            {btn('获取应用列表', Smartphone, handleLoadApps)}
          </div>
          {apps && (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1">
                <div className="flex bg-secondary/50 rounded p-0.5 border border-border">
                  <button onClick={()=>setAppTab('third_party')} className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${appTab==='third_party'?'bg-primary text-primary-foreground':'text-muted-foreground'}`}>三方 ({apps.third_party.length})</button>
                  <button onClick={()=>setAppTab('system')} className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${appTab==='system'?'bg-primary text-primary-foreground':'text-muted-foreground'}`}>系统 ({apps.system.length})</button>
                </div>
                <div className="relative flex-1">
                  <Search className="absolute left-1.5 top-1/2 -translate-y-1/2 w-2.5 h-2.5 text-muted-foreground" />
                  <Input placeholder="搜索..." value={appSearch} onChange={e=>setAppSearch(e.target.value)} className="h-6 text-[10px] pl-5" />
                </div>
              </div>
              <div className="max-h-[calc(100vh-260px)] overflow-y-auto rounded-lg border border-border">
                {filteredApps.length===0?<div className="p-3 text-center text-[10px] text-muted-foreground">无匹配应用</div>:filteredApps.map((app:InstalledAppInfo)=>(
                  <div key={app.package_name} className="flex items-center justify-between px-1.5 py-1 border-b border-border last:border-0 hover:bg-secondary/30">
                    <div className="min-w-0 flex-1">
                      <span className="text-[10px] font-medium truncate block">{app.app_name||app.package_name}</span>
                      {app.app_name&&<span className="text-[9px] text-muted-foreground font-mono truncate block">{app.package_name}</span>}
                    </div>
                    <Button variant="ghost" size="sm" className="h-5 text-[9px] px-1" onClick={()=>handleLaunchPkg(app.package_name)} disabled={loading!==null}><Play className="w-2 h-2 mr-0.5" />启动</Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>)}
      </div>
    </Card>
    {showModal && (
      <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-background border border-border rounded-2xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card flex-shrink-0">
            <div className="flex items-center gap-3">
              <Film className="w-4 h-4 text-red-500" />
              <div><h2 className="font-semibold text-sm">录屏控制</h2><p className="text-[10px] text-muted-foreground">{deviceName}</p></div>
              {recording&&<Badge className="bg-red-500 text-white text-[10px] h-5 animate-pulse"><CircleStop className="w-2.5 h-2.5 mr-1" />录制中 {actions.length} 步</Badge>}
            </div>
            <div className="flex items-center gap-2">
              {recording?<Button size="sm" className="bg-red-500 hover:bg-red-600 text-white gap-1.5" onClick={stopRecording}><CircleStop className="w-3.5 h-3.5" />停止录制</Button>:<Badge variant="secondary" className="text-[10px] h-5">已停止 · {actions.length} 步</Badge>}
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={closeModal}><X className="w-4 h-4" /></Button>
            </div>
          </div>
          <div className="flex-1 flex min-h-0 overflow-hidden">
            <div className="flex flex-col border-r border-border" style={{width:'40%'}}>
              <div className="px-3 py-2 border-b border-border bg-card/50 flex items-center justify-between flex-shrink-0">
                <span className="text-[11px] font-medium text-muted-foreground">投屏</span>
                <div className="flex items-center gap-1">
                  <div className="flex bg-secondary/50 rounded p-0.5 border border-border">
                    <button onClick={()=>setTouchMode('tap')} className={`px-2 py-0.5 rounded text-[9px] font-medium transition-all ${touchMode==='tap'?'bg-primary text-primary-foreground':'text-muted-foreground'}`}>点击</button>
                    <button onClick={()=>setTouchMode('long_press')} className={`px-2 py-0.5 rounded text-[9px] font-medium transition-all ${touchMode==='long_press'?'bg-primary text-primary-foreground':'text-muted-foreground'}`}>长按</button>
                  </div>
                  <Button variant="ghost" size="sm" className="h-5 text-[9px] px-1" onClick={()=>refreshMirror(false)}><RefreshCw className="w-2.5 h-2.5" /></Button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden bg-black flex items-center justify-center relative">
                {mirrorShot?.success&&mirrorShot.image?(
                  <img ref={screenImgRef} src={`data:image/png;base64,${mirrorShot.image}`} alt="Device screen"
                    className={`max-w-full max-h-full object-contain select-none ${mirrorLoading?'opacity-70':''}`}
                    style={{cursor:dragStart?'grabbing':'crosshair',touchAction:'none'}}
                    onMouseDown={onMouseDown} onMouseUp={onMouseUp} onMouseLeave={()=>setDragStart(null)} draggable={false} />
                ):(
                  <div className="flex flex-col items-center justify-center text-white/50"><Monitor className="w-10 h-10 mb-2" /><p className="text-sm">加载中...</p></div>
                )}
                {mirrorLoading&&<div className="absolute inset-0 flex items-center justify-center bg-black/30"><Loader2 className="w-6 h-6 animate-spin text-white" /></div>}
                {recording&&<div className="absolute top-2 right-2"><Badge className="bg-red-500 text-white text-[9px] h-4 animate-pulse">REC {actions.length}</Badge></div>}
              </div>
              <div className="p-2 border-t border-border bg-card/50 flex-shrink-0">
                <div className="grid grid-cols-6 gap-1">
                  <Button variant="outline" size="sm" className="h-6 text-[10px] gap-0.5" onClick={()=>mirrorNav('back')}><ArrowLeft className="w-3 h-3" />返回</Button>
                  <Button variant="outline" size="sm" className="h-6 text-[10px] gap-0.5" onClick={()=>mirrorNav('home')}><Home className="w-3 h-3" />主页</Button>
                  <Button variant="outline" size="sm" className="h-6 text-[10px] gap-0.5 text-blue-600 border-blue-200" onClick={()=>mirrorScroll('up')}><ArrowUp className="w-3 h-3" />上滑</Button>
                  <Button variant="outline" size="sm" className="h-6 text-[10px] gap-0.5 text-green-600 border-green-200" onClick={()=>mirrorScroll('down')}><ArrowDown className="w-3 h-3" />下滑</Button>
                  <Button variant="outline" size="sm" className="h-6 text-[10px] gap-0.5 text-purple-600 border-purple-200" onClick={()=>mirrorScroll('left')}><ArrowLeftIcon className="w-3 h-3" />左滑</Button>
                  <Button variant="outline" size="sm" className="h-6 text-[10px] gap-0.5 text-orange-600 border-orange-200" onClick={()=>mirrorScroll('right')}><ArrowRightIcon className="w-3 h-3" />右滑</Button>
                </div>
              </div>
            </div>
            <div className="flex flex-col flex-1 min-w-0">
              <div className="px-3 py-2 border-b border-border bg-card/50 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-medium text-muted-foreground">Pytest 代码</span>
                  <span className="text-[10px] text-muted-foreground">|</span>
                  <span className="text-[11px] font-medium text-muted-foreground">YAML 代码</span>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" className="h-5 text-[9px] px-1.5" onClick={()=>navigator.clipboard.writeText(pytestCode)}><Copy className="w-2.5 h-2.5 mr-0.5" />复制Pytest</Button>
                  <Button variant="ghost" size="sm" className="h-5 text-[9px] px-1.5" onClick={handleRunCode}><Play className="w-2.5 h-2.5 mr-0.5" />运行</Button>
                  <Button variant="ghost" size="sm" className="h-5 text-[9px] px-1.5" onClick={()=>{setActions([]);setPytestCode(buildPytestCode([],deviceId));setPytestResult(null);setRecordedScreenshots([]);setGifData(null);}}><Trash2 className="w-2.5 h-2.5 mr-0.5" />清空</Button>
                  {recordedScreenshots.length>0&&<Button variant="ghost" size="sm" className="h-5 text-[9px] px-1.5" onClick={handleGif} disabled={gifLoading}>{gifLoading?<Loader2 className="w-2.5 h-2.5 animate-spin mr-0.5" />:<Film className="w-2.5 h-2.5 mr-0.5" />}GIF</Button>}
                </div>
              </div>
              <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-2 gap-2">
                <div className="flex-1 flex gap-2 min-h-0">
                  <div className="flex-1 flex flex-col min-h-0">
                    <div className="text-[9px] text-muted-foreground mb-1">Pytest 代码</div>
                    <textarea className="flex-1 bg-zinc-900 text-zinc-200 rounded-lg p-3 text-[11px] font-mono border border-border resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                      value={pytestCode} onChange={e=>setPytestCode(e.target.value)} spellCheck={false} placeholder="录制操作后将自动生成 pytest 代码..." />
                  </div>
                  <div className="flex-1 flex flex-col min-h-0">
                    <div className="text-[9px] text-muted-foreground mb-1">YAML 代码</div>
                    <textarea className="flex-1 bg-zinc-900 text-zinc-200 rounded-lg p-3 text-[11px] font-mono border border-border resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                      value={yamlCode} onChange={e=>setYamlCode(e.target.value)} spellCheck={false} placeholder="录制操作后将自动生成 YAML 代码..." />
                  </div>
                </div>
                {pytestResult&&(
                  <div className={`rounded-lg p-2 text-[10px] font-mono max-h-32 overflow-y-auto border flex-shrink-0 ${pytestResult.success?'bg-emerald-50 border-emerald-200 text-emerald-800':'bg-red-50 border-red-200 text-red-800'}`}>
                    <div className="font-semibold mb-0.5">{pytestResult.success?'✓ PASS':'✗ FAIL'}</div>
                    <pre className="whitespace-pre-wrap">{pytestResult.output}</pre>
                  </div>
                )}
                {gifData&&<div className="rounded-lg overflow-hidden border border-border flex-shrink-0"><img src={`data:image/gif;base64,${gifData}`} alt="GIF" className="w-full max-h-40 object-contain" /></div>}
                {actions.length>0&&(
                  <div className="border border-border rounded-lg p-1.5 max-h-28 overflow-y-auto flex-shrink-0">
                    <div className="text-[9px] text-muted-foreground mb-1">操作记录 ({actions.length} 步)</div>
                    {actions.map((a,i)=><div key={i} className="text-[10px] py-0.5 border-b border-border/50 last:border-0"><span className="text-muted-foreground">{i+1}.</span> {a.label}</div>)}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )}
  </>);
}
