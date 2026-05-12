import React, { useState } from 'react';
import {
  Edit,
  Loader2,
  Server,
  Smartphone,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ConfirmDialog } from './ConfirmDialog';
import { useTranslation } from '../lib/i18n-context';
import { removeRemoteDevice, updateDeviceName } from '../api';
import type { AgentStatus } from '../api';
import type { ToastType } from './Toast';

interface DeviceCardProps {
  id: string;
  serial: string;
  model: string;
  status: string;
  connectionType?: string;
  displayName?: string | null;
  agent?: AgentStatus | null;
  isActive: boolean;
  onClick: () => void;
  onConnectWifi?: () => Promise<void>;
  onDisconnectWifi?: () => Promise<void>;
  onNameUpdated?: () => void;
  showToast?: (message: string, type: ToastType) => void;
}

export function DeviceCard({
  id: _id,
  serial,
  model,
  status,
  connectionType,
  displayName,
  agent,
  isActive,
  onClick,
  onConnectWifi,
  onDisconnectWifi,
  onNameUpdated,
  showToast,
}: DeviceCardProps) {
  const t = useTranslation();
  const isOnline = status === 'device';
  const isUsb = connectionType === 'usb';
  const isWifi = connectionType === 'wifi';
  const isRemote = connectionType === 'remote';
  const [loading, setLoading] = useState(false);
  const [showWifiConfirm, setShowWifiConfirm] = useState(false);
  const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingName, setEditingName] = useState('');
  const [saving, setSaving] = useState(false);

  const actualDisplayName = displayName || model || t.deviceCard.unknownDevice;

  const getAgentStatusClass = () => {
    if (!isOnline) return 'bg-muted';
    if (!agent) return 'bg-muted';
    switch (agent.state) {
      case 'idle': return 'bg-emerald-500';
      case 'busy': return 'bg-amber-500';
      case 'error': return 'bg-red-500';
      case 'initializing': return 'bg-amber-500 animate-pulse';
      default: return 'bg-muted';
    }
  };

  const getCurrentStatusText = () => {
    if (!isOnline) return t.deviceCard.statusTooltip.none;
    if (!agent) return t.deviceCard.statusTooltip.none;
    switch (agent.state) {
      case 'idle': return t.deviceCard.statusTooltip.idle;
      case 'busy': return t.deviceCard.statusTooltip.busy;
      case 'error': return t.deviceCard.statusTooltip.error;
      case 'initializing': return t.deviceCard.statusTooltip.initializing;
      default: return t.deviceCard.statusTooltip.none;
    }
  };

  const handleWifiClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (loading || !onConnectWifi) return;
    setShowWifiConfirm(true);
  };

  const handleDisconnectClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (loading || !onDisconnectWifi) return;
    setShowDisconnectConfirm(true);
  };

  const handleConfirmWifi = async () => {
    setShowWifiConfirm(false);
    setLoading(true);
    try {
      if (onConnectWifi) await onConnectWifi();
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDisconnect = async () => {
    setShowDisconnectConfirm(false);
    setLoading(true);
    try {
      if (onDisconnectWifi) await onDisconnectWifi();
    } finally {
      setLoading(false);
    }
  };

  const handleEditClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingName(displayName || model || '');
    setShowEditDialog(true);
  };

  const handleSaveName = async () => {
    try {
      setSaving(true);
      const trimmedName = editingName.trim();
      const response = await updateDeviceName(serial, trimmedName || null);
      if (!response.success) {
        if (showToast) showToast(response.error || t.deviceCard.saveNameError, 'error');
        return;
      }
      setShowEditDialog(false);
      if (onNameUpdated) onNameUpdated();
      if (showToast) showToast(t.deviceCard.saveNameSuccess, 'success');
    } catch (error) {
      console.error('Failed to update device name:', error);
      if (showToast) showToast(t.deviceCard.saveNameError, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') onClick(); }}
        className={`
          group relative w-full text-left p-3 rounded-xl transition-all duration-200 cursor-pointer
          ${isActive
            ? 'bg-primary/5 border border-primary/20'
            : 'bg-transparent border border-transparent hover:bg-secondary/50 hover:border-border'
          }
        `}
      >
        {isActive && <div className="absolute left-0 top-2 bottom-2 w-1 bg-primary rounded-r" />}

        <div className="flex items-center gap-3 pl-2">
          {/* Agent status indicator - NEXA clean style */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className={`relative flex-shrink-0 w-3 h-3 rounded-full transition-all cursor-help ${isActive ? 'scale-110' : ''} ${getAgentStatusClass()}`}>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={10} className="max-w-xs">
              <div className="space-y-1.5">
                <p className="font-medium">
                  {t.deviceCard.statusTooltip.title}{getCurrentStatusText()}
                </p>
                <div className="text-xs space-y-0.5">
                  <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500" />{t.deviceCard.statusTooltip.legend.green}</p>
                  <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-amber-500" />{t.deviceCard.statusTooltip.legend.yellow}</p>
                  <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-500" />{t.deviceCard.statusTooltip.legend.red}</p>
                  <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-muted" />{t.deviceCard.statusTooltip.legend.gray}</p>
                </div>
              </div>
            </TooltipContent>
          </Tooltip>

          {/* Device icon and info */}
          <div className="flex-1 min-w-0 flex flex-col justify-center gap-0.5">
            <div className="flex items-center gap-2">
              <Smartphone className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
              <span className={`font-medium text-sm truncate`}>
                {actualDisplayName}
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleEditClick}
                    className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Edit className="w-3 h-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>{t.deviceCard.editName}</p></TooltipContent>
              </Tooltip>
            </div>
            <span className={`text-xs font-mono text-muted-foreground truncate`}>{serial}</span>
          </div>

          {/* Connection type badge - NEXA clean style */}
          <div className="flex-shrink-0 flex items-center">
            {isRemote ? (
              <Badge variant="secondary" className="text-xs">
                <Server className="w-2.5 h-2.5 mr-1" />
                {t.deviceCard.remote || 'Remote'}
              </Badge>
            ) : isWifi ? (
              <Badge variant="secondary" className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                <Wifi className="w-2.5 h-2.5 mr-1" />
                {t.deviceCard.wifi || 'WiFi'}
              </Badge>
            ) : isUsb ? (
              <Badge variant="secondary" className="text-xs">
                USB
              </Badge>
            ) : null}
          </div>

          {/* Action buttons - NEXA clean style */}
          <div className="flex items-center gap-1 flex-shrink-0">
            {onConnectWifi && isUsb && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleWifiClick}
                    disabled={loading}
                    className="h-7 w-7"
                  >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wifi className="w-3.5 h-3.5" />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>{t.deviceCard.connectViaWifi}</p></TooltipContent>
              </Tooltip>
            )}
            {onDisconnectWifi && isWifi && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleDisconnectClick}
                    disabled={loading}
                    className="h-7 w-7"
                  >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <WifiOff className="w-3.5 h-3.5" />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>{t.deviceCard.disconnectWifi}</p></TooltipContent>
              </Tooltip>
            )}
            {isRemote && (
              <Button
                variant="ghost"
                size="icon"
                onClick={async e => {
                  e.stopPropagation();
                  setLoading(true);
                  try { await removeRemoteDevice(serial); } catch (error) { console.error('Failed to remove remote device:', error); } finally { setLoading(false); }
                }}
                disabled={loading}
                className="h-7 w-7"
                title={t.deviceCard.removeRemote || '移除远程设备'}
              >
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* WiFi Connection Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showWifiConfirm}
        title={t.deviceCard.connectWifiTitle}
        content={t.deviceCard.connectWifiContent}
        onConfirm={handleConfirmWifi}
        onCancel={() => setShowWifiConfirm(false)}
      />

      {/* WiFi Disconnect Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDisconnectConfirm}
        title={t.deviceCard.disconnectWifiTitle}
        content={t.deviceCard.disconnectWifiContent}
        onConfirm={handleConfirmDisconnect}
        onCancel={() => setShowDisconnectConfirm(false)}
      />

      {/* Device Name Edit Dialog - NEXA clean style */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t.deviceCard.editNameDialogTitle}</DialogTitle>
            <DialogDescription>{t.deviceCard.editNameDialogDescription}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="device-name">{t.deviceCard.deviceNameLabel}</Label>
              <Input
                id="device-name"
                value={editingName}
                onChange={e => setEditingName(e.target.value)}
                placeholder={t.deviceCard.deviceNamePlaceholder}
                maxLength={100}
                onKeyDown={e => { if (e.key === 'Enter' && !saving) handleSaveName(); }}
              />
              <p className="text-xs text-muted-foreground">{t.deviceCard.deviceSerialLabel}: {serial}</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)} disabled={saving}>
              {t.common.cancel}
            </Button>
            <Button onClick={handleSaveName} disabled={saving}>
              {saving ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" />{t.common.loading}</>) : t.common.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
