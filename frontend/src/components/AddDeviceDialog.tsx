import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Smartphone, Wifi, AlertCircle, Loader2, CheckCircle, XCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { QRCodeSVG } from 'qrcode.react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  generateQRPairing, getQRPairingStatus, cancelQRPairing,
} from '../api';
import { useTranslation } from '../lib/i18n-context';

interface QRPairingSession {
  sessionId: string;
  payload: string;
  status: 'listening' | 'pairing' | 'paired' | 'connecting' | 'connected' | 'timeout' | 'error';
  expiresAt: number;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onConnected?: () => void;
}

// ── QR Status Helpers ──────────────────────────────────────────────────────────
function QRSessionStatus({ status, t }: { status: QRPairingSession['status']; t: ReturnType<typeof useTranslation> }) {
  const labels: Record<string, { icon: React.ReactNode; className: string; text: string }> = {
    listening:  { icon: <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />,                          className: '', text: t.deviceSidebar.qrWaitingForScan },
    pairing:    { icon: <Loader2 className="h-4 w-4 animate-spin text-primary" />,                                   className: '', text: t.deviceSidebar.qrPairing },
    connected:  { icon: <CheckCircle className="h-4 w-4 text-emerald-500" />,                                       className: 'text-emerald-600 dark:text-emerald-400', text: t.deviceSidebar.qrConnected },
    timeout:    { icon: <XCircle className="h-4 w-4 text-amber-500" />,                                           className: 'text-amber-600 dark:text-amber-400', text: t.deviceSidebar.qrTimeout },
    error:      { icon: <XCircle className="h-4 w-4 text-red-500" />,                                              className: 'text-red-600 dark:text-red-400', text: t.deviceSidebar.qrError },
  };
  const s = labels[status] ?? labels.listening;
  return (
    <div className="flex items-center gap-2">
      {s.icon}
      <span className={`text-sm ${s.className}`}>{s.text}</span>
    </div>
  );
}

// ── Tab 1: Direct Connect ──────────────────────────────────────────────────────
function DirectConnectTab({
  discoveredDevices, isScanning, isConnecting, scanError,
  ipError, selectedEmulator, manualConnectIp, manualConnectPort,
  portError, EMULATOR_PRESETS, t,
  onScan, onManualConnect, onDeviceClick,
  setSelectedEmulator, setManualConnectIp, setManualConnectPort,
}: {
  discoveredDevices: Array<{ ip: string; port: number; name: string; has_pairing: boolean; pairing_port?: number }>;
  isScanning: boolean; isConnecting: boolean; scanError: string;
  ipError: string; selectedEmulator: string; manualConnectIp: string;
  manualConnectPort: string; portError: string;
  EMULATOR_PRESETS: Array<{ id: string; nameKey: string; ip: string; port: number }>;
  t: ReturnType<typeof useTranslation>;
  onScan: () => void; onManualConnect: () => void; onDeviceClick: (d: typeof discoveredDevices[0], inPairing: false) => void;
  setSelectedEmulator: (id: string) => void;
  setManualConnectIp: (v: string) => void; setManualConnectPort: (v: string) => void;
}) {
  const directDevices = discoveredDevices.filter(d => !d.has_pairing);
  return (
    <TabsContent value="direct" className="space-y-4 mt-4">
      {/* Scan row */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">{t.deviceSidebar.discoveredDevices}</h3>
        <Button variant="outline" size="sm" onClick={onScan} disabled={isScanning} className="h-8">
          {isScanning ? (
            <><span className="mr-2 h-3 w-3 animate-spin rounded-full border-2 border-zinc-400 border-t-transparent" />{t.deviceSidebar.scanning}</>
          ) : t.deviceSidebar.scanAgain}
        </Button>
      </div>

      {scanError && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950/20 p-3">
          <p className="text-sm text-red-700 dark:text-red-300">{scanError}</p>
        </div>
      )}

      {/* Discovered devices */}
      {!isScanning && directDevices.length === 0 ? (
        <div className="rounded-lg bg-secondary/50 p-4 text-center">
          <Wifi className="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p className="mt-2 text-sm text-muted-foreground">{t.deviceSidebar.noDirectDevices}</p>
        </div>
      ) : directDevices.length > 0 && (
        <div className="space-y-2">
          {directDevices.map(d => (
            <button key={`${d.ip}:${d.port}`}
              onClick={() => onDeviceClick(d, false)}
              disabled={isConnecting}
              className="w-full rounded-lg border border-border p-3 text-left transition-colors hover:bg-secondary/50 disabled:opacity-50">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Smartphone className="h-4 w-4 text-primary" />
                    <span className="font-medium">{d.name}</span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{d.ip}:{d.port}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {ipError && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950/20 p-3">
          <p className="text-sm text-red-700 dark:text-red-300">{ipError}</p>
        </div>
      )}

      <div className="relative my-4">
        <Separator />
        <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-2 text-sm text-muted-foreground">
          {t.deviceSidebar.orManualConnect}
        </span>
      </div>

      {/* Emulator presets */}
      <div className="space-y-2">
        <Label>{t.deviceSidebar.emulatorPreset}</Label>
        <div className="grid grid-cols-3 gap-2">
          {EMULATOR_PRESETS.map(preset => (
            <button key={preset.id}
              onClick={() => {
                setSelectedEmulator(preset.id);
                if (preset.id !== 'custom') {
                  setManualConnectIp(preset.ip);
                  setManualConnectPort(String(preset.port));
                }
              }}
              className={`rounded-lg border p-2 text-xs text-center transition-colors ${
                selectedEmulator === preset.id
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300'
                  : 'border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800'
              }`}>
              {t.deviceSidebar[preset.nameKey as keyof typeof t.deviceSidebar] ?? preset.nameKey}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-lg bg-blue-50 dark:bg-blue-950/20 p-3 text-sm">
        <p className="text-blue-800 dark:text-blue-200">{t.deviceSidebar.emulatorNote}</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="ip">{t.deviceSidebar.ipAddress}</Label>
        <Input id="ip" placeholder="192.168.1.100" value={manualConnectIp}
          onChange={e => { setManualConnectIp(e.target.value); if (selectedEmulator !== 'custom') setSelectedEmulator('custom'); }}
          onKeyDown={e => e.key === 'Enter' && onManualConnect()}
          className={ipError ? 'border-red-500' : ''} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="port">{t.deviceSidebar.port}</Label>
        <Input id="port" type="number" placeholder="5555" value={manualConnectPort}
          onChange={e => { setManualConnectPort(e.target.value); if (selectedEmulator !== 'custom') setSelectedEmulator('custom'); }}
          onKeyDown={e => e.key === 'Enter' && onManualConnect()}
          className={portError ? 'border-red-500' : ''} />
        {portError && <p className="text-sm text-red-500">{portError}</p>}
      </div>
      <Button onClick={onManualConnect} disabled={isConnecting} className="w-full">
        {isConnecting ? t.common.loading : t.deviceSidebar.connect}
      </Button>
    </TabsContent>
  );
}

// ── Tab 2: WiFi Pairing ───────────────────────────────────────────────────────
function PairingTab({
  discoveredDevices, isScanning, isConnecting, scanError,
  ipError, pairingPort, pairingCode, pairingCodeError,
  connectionPort, manualConnectIp, portError, t,
  onScan, onPair, onDeviceClick, qrSession, isGeneratingQR,
  onGenerateQR, onCancelQR, setManualConnectIp, setPairingPort,
  setPairingCode, setConnectionPort,
}: {
  discoveredDevices: Array<{ ip: string; port: number; name: string; has_pairing: boolean; pairing_port?: number }>;
  isScanning: boolean; isConnecting: boolean; scanError: string;
  ipError: string; pairingPort: string; pairingCode: string;
  pairingCodeError: string; connectionPort: string;
  manualConnectIp: string; portError: string;
  t: ReturnType<typeof useTranslation>;
  onScan: () => void; onPair: () => void; onDeviceClick: (d: typeof discoveredDevices[0], inPairing: true) => void;
  qrSession: QRPairingSession | null; isGeneratingQR: boolean;
  onGenerateQR: () => void; onCancelQR: () => void;
  setManualConnectIp: (v: string) => void; setPairingPort: (v: string) => void;
  setPairingCode: (v: string) => void; setConnectionPort: (v: string) => void;
}) {
  const pairingDevices = discoveredDevices.filter(d => d.has_pairing);
  return (
    <TabsContent value="pair" className="space-y-4 mt-4">
      {/* Scan row */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">{t.deviceSidebar.discoveredDevices}</h3>
        <Button variant="outline" size="sm" onClick={onScan} disabled={isScanning} className="h-8">
          {isScanning ? (
            <><span className="mr-2 h-3 w-3 animate-spin rounded-full border-2 border-zinc-400 border-t-transparent" />{t.deviceSidebar.scanning}</>
          ) : t.deviceSidebar.scanAgain}
        </Button>
      </div>

      {scanError && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950/20 p-3">
          <p className="text-sm text-red-700 dark:text-red-300">{scanError}</p>
        </div>
      )}

      {/* Discovered pairing devices */}
      {!isScanning && pairingDevices.length === 0 ? (
        <div className="rounded-lg bg-secondary/50 p-4 text-center">
          <Wifi className="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p className="mt-2 text-sm text-muted-foreground">{t.deviceSidebar.noPairingDevices}</p>
        </div>
      ) : pairingDevices.length > 0 && (
        <div className="space-y-2">
          {pairingDevices.map(d => (
            <button key={`${d.ip}:${d.port}`}
              onClick={() => onDeviceClick(d, true)}
              disabled={isConnecting}
              className="w-full rounded-lg border border-border p-3 text-left transition-colors hover:bg-secondary/50 disabled:opacity-50">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Smartphone className="h-4 w-4 text-primary" />
                    <span className="font-medium">{d.name}</span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{d.ip}:{d.port}</p>
                  <div className="mt-2 flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                    <AlertCircle className="h-3 w-3" />
                    <span>{t.deviceSidebar.pairingRequired}</span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* QR Section */}
      <div className="space-y-3">
        <div className="relative my-4">
          <Separator />
          <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-2 text-sm text-muted-foreground">
            {t.deviceSidebar.orQrPair}
          </span>
        </div>

        <div className="rounded-lg bg-accent p-3 text-sm">
          <p className="font-medium mb-2">{t.deviceSidebar.qrPairingTitle}</p>
          <ol className="space-y-1 text-muted-foreground text-xs">
            <li>{t.deviceSidebar.qrStep1}</li>
            <li>{t.deviceSidebar.qrStep2}</li>
            <li>{t.deviceSidebar.qrStep3}</li>
          </ol>
        </div>

        {/* QR Display */}
        {qrSession ? (
          <div className="rounded-lg border border-border p-4 bg-card">
            <div className="flex flex-col items-center space-y-3">
              <div className="bg-white p-4 rounded-lg">
                <QRCodeSVG value={qrSession.payload} size={200} level="M" />
              </div>
              <QRSessionStatus status={qrSession.status} t={t} />
              <div className="flex gap-2 w-full">
                {(qrSession.status === 'timeout' || qrSession.status === 'error') && (
                  <Button variant="outline" onClick={onGenerateQR} className="flex-1">{t.deviceSidebar.qrRegenerate}</Button>
                )}
                {qrSession.status === 'listening' && (
                  <Button variant="outline" onClick={onCancelQR} className="flex-1">{t.common.cancel}</Button>
                )}
                {qrSession.status === 'connected' && (
                  <Button onClick={() => {}} className="flex-1">{t.common.confirm}</Button>
                )}
              </div>
            </div>
          </div>
        ) : isGeneratingQR ? (
          <div className="flex items-center justify-center gap-2 py-4 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">{t.common.loading}</span>
          </div>
        ) : null}
      </div>

      {/* Manual Pair Form */}
      <div className="relative my-4">
        <Separator />
        <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-2 text-sm text-muted-foreground">
          {t.deviceSidebar.orManualPair}
        </span>
      </div>

      <div className="rounded-lg bg-secondary/50 p-3 text-sm">
        <p className="font-medium mb-2">{t.deviceSidebar.pairingInstructions}</p>
        <ol className="space-y-1 text-muted-foreground text-xs">
          <li>{t.deviceSidebar.pairingStep1}</li>
          <li>{t.deviceSidebar.pairingStep2}</li>
          <li>{t.deviceSidebar.pairingStep3}</li>
          <li>{t.deviceSidebar.pairingStep4}</li>
        </ol>
        <p className="mt-2 text-xs text-muted-foreground/80">{t.deviceSidebar.pairingNote}</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="pair-ip">{t.deviceSidebar.ipAddress}</Label>
        <Input id="pair-ip" placeholder="192.168.1.100" value={manualConnectIp}
          onChange={e => setManualConnectIp(e.target.value)}
          className={ipError ? 'border-red-500' : ''} />
        {ipError && <p className="text-sm text-red-500">{ipError}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="pairing-port">{t.deviceSidebar.pairingPort}</Label>
        <Input id="pairing-port" type="number" placeholder="37831" value={pairingPort}
          onChange={e => setPairingPort(e.target.value)}
          className={portError ? 'border-red-500' : ''} />
        {portError && <p className="text-sm text-red-500">{portError}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="pairing-code">{t.deviceSidebar.pairingCode}</Label>
        <Input id="pairing-code" type="text" placeholder="123456" maxLength={6} value={pairingCode}
          onChange={e => setPairingCode(e.target.value.replace(/\D/g, ''))}
          onKeyDown={e => e.key === 'Enter' && onPair()}
          className={pairingCodeError ? 'border-red-500' : ''} />
        {pairingCodeError && <p className="text-sm text-red-500">{pairingCodeError}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="connection-port">{t.deviceSidebar.connectionPort}</Label>
        <Input id="connection-port" type="number" value={connectionPort}
          onChange={e => setConnectionPort(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onPair()} />
      </div>
      <Button onClick={onPair} disabled={isConnecting} className="w-full">
        {isConnecting ? t.common.loading : t.deviceSidebar.pairAndConnect}
      </Button>
    </TabsContent>
  );
}

// ── Tab 3: Remote ──────────────────────────────────────────────────────────────
function RemoteTab({
  remoteBaseUrl, remoteUrlError, isDiscoveringRemote,
  discoveredRemoteDevices, selectedRemoteDevice, isConnectingRemote,
  onDiscover, onAdd, setRemoteBaseUrl, setSelectedRemoteDevice,
}: {
  remoteBaseUrl: string; remoteUrlError: string; isDiscoveringRemote: boolean;
  discoveredRemoteDevices: Array<{ device_id: string; model: string; platform: string }>;
  selectedRemoteDevice: string | null; isConnectingRemote: boolean;
  onDiscover: () => void; onAdd: () => void;
  setRemoteBaseUrl: (v: string) => void; setSelectedRemoteDevice: (v: string | null) => void;
}) {
  return (
    <TabsContent value="remote" className="space-y-4 mt-4">
      <div className="space-y-2">
        <Label htmlFor="remote-url">远程服务器地址</Label>
        <Input id="remote-url" placeholder="http://192.168.1.100:8001"
          value={remoteBaseUrl}
          onChange={e => { setRemoteBaseUrl(e.target.value); }}
          disabled={isDiscoveringRemote}
          onKeyDown={e => e.key === 'Enter' && onDiscover()}
          className={remoteUrlError ? 'border-red-500' : ''} />
        {remoteUrlError && <p className="text-sm text-red-500">{remoteUrlError}</p>}
        <p className="text-xs text-muted-foreground">运行 Device Agent Server 的地址</p>
        <Button onClick={onDiscover} disabled={isDiscoveringRemote || !remoteBaseUrl} className="w-full">
          {isDiscoveringRemote ? '正在发现...' : '发现设备'}
        </Button>
      </div>

      {discoveredRemoteDevices.length > 0 && (
        <div className="space-y-2">
          <Label>可用设备</Label>
          <div className="space-y-2">
            {discoveredRemoteDevices.map(d => (
              <button key={d.device_id}
                onClick={() => setSelectedRemoteDevice(d.device_id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  selectedRemoteDevice === d.device_id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-secondary/50'
                }`}>
                <div className="flex items-center gap-2">
                  <Smartphone className="h-4 w-4 text-primary" />
                  <div className="flex-1">
                    <p className="font-medium text-sm">{d.device_id}</p>
                    <p className="text-xs text-muted-foreground">{d.model} · {d.platform}</p>
                  </div>
                  {selectedRemoteDevice === d.device_id && (
                    <CheckCircle className="h-4 w-4 text-primary" />
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedRemoteDevice && (
        <Button onClick={onAdd} disabled={isConnectingRemote} className="w-full">
          {isConnectingRemote ? '正在连接...' : '连接远程设备'}
        </Button>
      )}
    </TabsContent>
  );
}

// ── Main Dialog Component ──────────────────────────────────────────────────────
const EMULATOR_PRESETS = [
  { id: 'mumu', nameKey: 'emulatorMumu', ip: '127.0.0.1', port: 7555 },
  { id: 'nox', nameKey: 'emulatorNox', ip: '127.0.0.1', port: 62001 },
  { id: 'ldplayer', nameKey: 'emulatorLdplayer', ip: '127.0.0.1', port: 5555 },
  { id: 'bluestacks', nameKey: 'emulatorBluestacks', ip: '127.0.0.1', port: 5555 },
  { id: 'custom', nameKey: 'emulatorCustom', ip: '', port: 5555 },
];

export function AddDeviceDialog({ open, onClose }: Props) {
  const t = useTranslation();
  const [activeTab, setActiveTab] = useState('direct');
  const [manualConnectIp, setManualConnectIp] = useState('');
  const [manualConnectPort, setManualConnectPort] = useState('5555');
  const [pairingCode, setPairingCode] = useState('');
  const [pairingPort, setPairingPort] = useState('');
  const [connectionPort, setConnectionPort] = useState('5555');
  const [ipError, setIpError] = useState('');
  const [portError, setPortError] = useState('');
  const [pairingCodeError, setPairingCodeError] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [selectedEmulator, setSelectedEmulator] = useState('custom');
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState('');
  const [discoveredDevices, setDiscoveredDevices] = useState<Array<{ ip: string; port: number; name: string; has_pairing: boolean; pairing_port?: number }>>([]);
  const [qrSession, setQrSession] = useState<QRPairingSession | null>(null);
  const [isGeneratingQR, setIsGeneratingQR] = useState(false);
  const [remoteBaseUrl, setRemoteBaseUrl] = useState('');
  const [remoteUrlError, setRemoteUrlError] = useState('');
  const [isDiscoveringRemote, setIsDiscoveringRemote] = useState(false);
  const [discoveredRemoteDevices, setDiscoveredRemoteDevices] = useState<Array<{ device_id: string; model: string; platform: string }>>([]);
  const [selectedRemoteDevice, setSelectedRemoteDevice] = useState<string | null>(null);
  const [isConnectingRemote, setIsConnectingRemote] = useState(false);
  const qrPollRef = useRef<number | null>(null);

  // Cleanup on close
  useEffect(() => {
    if (!open) {
      setActiveTab('direct');
      setManualConnectIp(''); setManualConnectPort('5555');
      setPairingCode(''); setPairingPort(''); setConnectionPort('5555');
      setIpError(''); setPortError(''); setPairingCodeError('');
      setScanError(''); setDiscoveredDevices([]);
      setQrSession(null); setIsGeneratingQR(false);
      setRemoteBaseUrl(''); setRemoteUrlError('');
      setDiscoveredRemoteDevices([]); setSelectedRemoteDevice(null);
      if (qrPollRef.current) { clearInterval(qrPollRef.current); qrPollRef.current = null; }
    }
  }, [open]);

  const stopQRPoll = useCallback(() => {
    if (qrPollRef.current !== null) { clearInterval(qrPollRef.current); qrPollRef.current = null; }
  }, []);

  const handleDiscover = useCallback(async () => {
    setIsScanning(true); setScanError('');
    try {
      const { discoverMdnsDevices } = await import('../api');
      const result = await discoverMdnsDevices();
      if (result.success) setDiscoveredDevices(result.devices ?? []);
      else { setScanError(result.error ?? '扫描失败'); setDiscoveredDevices([]); }
    } catch { setScanError('扫描异常'); setDiscoveredDevices([]); }
    finally { setIsScanning(false); }
  }, []);

  const handleDeviceClick = async (device: typeof discoveredDevices[0], inPairing: boolean) => {
    if (!inPairing) {
      setIsConnecting(true); setIpError('');
      try {
        const { connectWifiManual } = await import('../api');
        const result = await connectWifiManual({ ip: device.ip, port: device.port });
        if (result.success) onClose(); else setIpError(result.message ?? '连接失败');
      } catch { setIpError('连接异常'); }
      finally { setIsConnecting(false); }
    } else {
      setManualConnectIp(device.ip);
      setPairingPort(device.pairing_port ? String(device.pairing_port) : '');
      setConnectionPort(String(device.port));
      setTimeout(() => document.getElementById('pairing-code')?.focus(), 100);
    }
  };

  const handleManualConnect = async () => {
    setIpError(''); setPortError('');
    const ip = manualConnectIp; const port = manualConnectPort;
    const ipOk = /^(?:\d{1,3}\.){3}\d{1,3}$/.test(ip) && ip.split('.').every(p => +p >= 0 && +p <= 255);
    const portOk = !isNaN(+port) && +port >= 1 && +port <= 65535;
    if (!ipOk) { setIpError(t.deviceSidebar.invalidIpError); return; }
    if (!portOk) { setPortError(t.deviceSidebar.invalidPortError); return; }
    setIsConnecting(true);
    try {
      const { connectWifiManual } = await import('../api');
      const result = await connectWifiManual({ ip, port: +port });
      if (result.success) onClose(); else setIpError(result.message ?? '连接失败');
    } catch { setIpError('连接异常'); }
    finally { setIsConnecting(false); }
  };

  const handlePair = async () => {
    setIpError(''); setPortError(''); setPairingCodeError('');
    const ipOk = /^(?:\d{1,3}\.){3}\d{1,3}$/.test(manualConnectIp) && manualConnectIp.split('.').every(p => +p >= 0 && +p <= 255);
    const portOk = !isNaN(+pairingPort) && +pairingPort >= 1 && +pairingPort <= 65535;
    const connOk = !isNaN(+connectionPort) && +connectionPort >= 1 && +connectionPort <= 65535;
    if (!ipOk) { setIpError(t.deviceSidebar.invalidIpError); return; }
    if (!portOk || !connOk) { setPortError(t.deviceSidebar.invalidPortError); return; }
    if (!/^\d{6}$/.test(pairingCode)) { setPairingCodeError(t.deviceSidebar.invalidPairingCodeError); return; }
    setIsConnecting(true);
    try {
      const { pairWifi } = await import('../api');
      const result = await pairWifi({ ip: manualConnectIp, pairing_port: +pairingPort, pairing_code: pairingCode, connection_port: +connectionPort });
      if (result.success) onClose();
      else {
        if (result.error === 'invalid_pairing_code') setPairingCodeError(result.message ?? '');
        else if (result.error === 'invalid_ip') setIpError(result.message ?? '');
        else setIpError(result.message ?? '配对失败');
      }
    } catch { setIpError('配对异常'); }
    finally { setIsConnecting(false); }
  };

  const handleGenerateQR = async () => {
    setIsGeneratingQR(true);
    try {
      const result = await generateQRPairing();
      if (result.success && result.qr_payload && result.session_id) {
        setQrSession({ sessionId: result.session_id, payload: result.qr_payload, status: 'listening', expiresAt: result.expires_at ?? Date.now() + 120000 });
        qrPollRef.current = window.setInterval(async () => {
          try {
            const status = await getQRPairingStatus(result.session_id!);
            setQrSession(prev => prev ? { ...prev, status: status.status as QRPairingSession['status'] } : null);
            if (['connected', 'timeout', 'error'].includes(status.status)) {
              stopQRPoll();
              if (status.status === 'connected') setTimeout(() => onClose(), 2000);
            }
          } catch { /* silent */ }
        }, 1000);
      }
    } catch { /* silent */ }
    finally { setIsGeneratingQR(false); }
  };

  const handleDiscoverRemote = async () => {
    setRemoteUrlError('');
    if (!remoteBaseUrl.trim()) { setRemoteUrlError('请输入地址'); return; }
    if (!remoteBaseUrl.startsWith('http://') && !remoteBaseUrl.startsWith('https://')) { setRemoteUrlError('必须以 http:// 或 https:// 开头'); return; }
    setIsDiscoveringRemote(true);
    try {
      const { discoverRemoteDevices } = await import('../api');
      const result = await discoverRemoteDevices({ base_url: remoteBaseUrl, timeout: 5 });
      if (result.success) { setDiscoveredRemoteDevices(result.devices ?? []); setSelectedRemoteDevice(null); }
      else { setRemoteUrlError(result.message ?? '发现失败'); setDiscoveredRemoteDevices([]); }
    } catch { setRemoteUrlError('连接失败'); setDiscoveredRemoteDevices([]); }
    finally { setIsDiscoveringRemote(false); }
  };

  const handleAddRemote = async () => {
    if (!selectedRemoteDevice) return;
    setIsConnectingRemote(true);
    try {
      const { addRemoteDevice } = await import('../api');
      const result = await addRemoteDevice({ base_url: remoteBaseUrl, device_id: selectedRemoteDevice });
      if (result.success) onClose(); else setRemoteUrlError(result.message ?? '添加失败');
    } catch { setRemoteUrlError('添加异常'); }
    finally { setIsConnectingRemote(false); }
  };

  // Auto-scan on open
  useEffect(() => {
    if (open) handleDiscover();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="sm:max-w-md max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t.deviceSidebar.manualConnectTitle}</DialogTitle>
          <DialogDescription>{t.deviceSidebar.manualConnectDescription}</DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={v => { setActiveTab(v); if (v === 'pair' && !qrSession && !isGeneratingQR) handleGenerateQR(); }}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="direct">{t.deviceSidebar.directConnectTab}</TabsTrigger>
            <TabsTrigger value="pair">{t.deviceSidebar.pairTab}</TabsTrigger>
            <TabsTrigger value="remote">远程设备</TabsTrigger>
          </TabsList>

          <DirectConnectTab
            discoveredDevices={discoveredDevices} isScanning={isScanning} isConnecting={isConnecting}
            scanError={scanError} ipError={ipError} selectedEmulator={selectedEmulator}
            manualConnectIp={manualConnectIp} manualConnectPort={manualConnectPort}
            portError={portError} EMULATOR_PRESETS={EMULATOR_PRESETS} t={t}
            onScan={handleDiscover} onManualConnect={handleManualConnect} onDeviceClick={handleDeviceClick}
            setSelectedEmulator={setSelectedEmulator} setManualConnectIp={setManualConnectIp}
            setManualConnectPort={setManualConnectPort}
          />

          <PairingTab
            discoveredDevices={discoveredDevices} isScanning={isScanning} isConnecting={isConnecting}
            scanError={scanError} ipError={ipError} pairingPort={pairingPort}
            pairingCode={pairingCode} pairingCodeError={pairingCodeError}
            connectionPort={connectionPort} manualConnectIp={manualConnectIp}
            portError={portError} t={t}
            onScan={handleDiscover} onPair={handlePair} onDeviceClick={handleDeviceClick}
            qrSession={qrSession} isGeneratingQR={isGeneratingQR}
            onGenerateQR={handleGenerateQR} onCancelQR={() => { stopQRPoll(); qrSession && cancelQRPairing(qrSession.sessionId).catch(() => {}); setQrSession(null); }}
            setManualConnectIp={setManualConnectIp} setPairingPort={setPairingPort}
            setPairingCode={setPairingCode} setConnectionPort={setConnectionPort}
          />

          <RemoteTab
            remoteBaseUrl={remoteBaseUrl} remoteUrlError={remoteUrlError}
            isDiscoveringRemote={isDiscoveringRemote}
            discoveredRemoteDevices={discoveredRemoteDevices}
            selectedRemoteDevice={selectedRemoteDevice}
            isConnectingRemote={isConnectingRemote}
            onDiscover={handleDiscoverRemote} onAdd={handleAddRemote}
            setRemoteBaseUrl={setRemoteBaseUrl} setSelectedRemoteDevice={setSelectedRemoteDevice}
          />
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t.common.cancel}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
