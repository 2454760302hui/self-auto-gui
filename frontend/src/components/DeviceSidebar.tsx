import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Smartphone, Settings, ChevronLeft, ChevronRight,
  Plug, Plus, FolderCog, RefreshCw,
} from 'lucide-react';
import { GroupedDeviceList } from './GroupedDeviceList';
import { AddDeviceDialog } from './AddDeviceDialog';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { Device } from '../api';
import { useDeviceGroups } from '../hooks/useDeviceGroups';
import { useTranslation } from '../lib/i18n-context';
import type { ToastType } from './Toast';

const SIDEBAR_DEFAULT_WIDTH = 320;
const SIDEBAR_MIN_WIDTH = 260;
const SIDEBAR_MAX_WIDTH = 560;

const getInitialCollapsedState = (): boolean => {
  try { return JSON.parse(localStorage.getItem('sidebar-collapsed') ?? 'false'); }
  catch { return false; }
};

const getInitialSidebarWidth = (): number => {
  try {
    const saved = localStorage.getItem('sidebar-width');
    if (saved !== null) {
      const n = Number(saved);
      if (!Number.isNaN(n)) return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, n));
    }
  } catch { /* ignore */ }
  return SIDEBAR_DEFAULT_WIDTH;
};

interface DeviceSidebarProps {
  devices: Device[];
  currentDeviceId: string;
  onSelectDevice: (deviceId: string) => void;
  onOpenConfig: () => void;
  onConnectWifi: (deviceId: string) => void;
  onDisconnectWifi: (deviceId: string) => void;
  onRefreshDevices?: () => void;
  onOpenGroupManager?: () => void;
  onBatchExecute?: (deviceIds: string[], deviceNames: Record<string, string>) => void;
  showToast?: (message: string, type: ToastType) => void;
}

export function DeviceSidebar({
  devices, currentDeviceId, onSelectDevice, onOpenConfig,
  onConnectWifi, onDisconnectWifi, onRefreshDevices,
  onOpenGroupManager, onBatchExecute, showToast,
}: DeviceSidebarProps) {
  const t = useTranslation();
  const [isCollapsed, setIsCollapsed] = useState(getInitialCollapsedState);
  const [sidebarWidth, setSidebarWidth] = useState(getInitialSidebarWidth);
  const [isResizing, setIsResizing] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const { groups, refreshGroups } = useDeviceGroups();
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(sidebarWidth);

  // ── Persistence ──────────────────────────────────────────────────────────────
  useEffect(() => { localStorage.setItem('sidebar-collapsed', JSON.stringify(isCollapsed)); }, [isCollapsed]);
  useEffect(() => { localStorage.setItem('sidebar-width', String(sidebarWidth)); }, [sidebarWidth]);

  // ── Drag resize ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isResizing) return;
    const handleMove = (e: MouseEvent) => {
      const delta = e.clientX - dragStartX.current;
      setSidebarWidth(Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, dragStartWidth.current + delta)));
    };
    const handleUp = () => { setIsResizing(false); };
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [isResizing]);

  // ── Keyboard shortcut: Ctrl+B ─────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        setIsCollapsed(v => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleResizeStart = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isCollapsed) return;
    e.preventDefault();
    dragStartX.current = e.clientX;
    dragStartWidth.current = sidebarWidth;
    setIsResizing(true);
  };

  return (
    <>
      {/* Collapsed expand button */}
      {isCollapsed && (
        <Button
          variant="ghost" size="icon"
          onClick={() => setIsCollapsed(false)}
          className="absolute left-0 top-20 z-50 h-12 w-8 rounded-r-xl bg-card hover:bg-secondary border-l-0"
          title="Expand sidebar"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      )}

      {/* Sidebar */}
      <div
        className={`
          ${isCollapsed ? 'w-0 -ml-4 opacity-0' : 'opacity-100'}
          ${isResizing ? '' : 'transition-[width,opacity] duration-300 ease-in-out'}
          h-full min-h-0 bg-card border-r border-border
          flex flex-col relative overflow-hidden
        `}
        style={isCollapsed ? undefined : { width: `${sidebarWidth}px` }}
      >
        {/* Resize handle */}
        {!isCollapsed && (
          <div
            role="separator" aria-orientation="vertical"
            onMouseDown={handleResizeStart}
            className="absolute top-0 right-0 bottom-0 w-1 cursor-col-resize
                       hover:bg-primary/20 active:bg-primary/30 z-20 transition-colors"
            title="Drag to resize"
          />
        )}

        {/* Header */}
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Smartphone className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">NEXA</h2>
              <p className="text-xs text-muted-foreground">
                {devices.length} {t.deviceSidebar?.devices ?? '设备'}
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setIsCollapsed(true)} className="h-8 w-8 rounded-lg" title="Collapse">
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>

        <Separator className="mx-4" />

        {/* Device list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-0">
          {devices.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mb-4">
                <Plug className="h-8 w-8 text-muted-foreground/50" />
              </div>
              <p className="font-medium text-foreground">{t.deviceSidebar?.noDevicesConnected ?? '暂无设备'}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t.deviceSidebar?.clickToRefresh ?? '点击刷新'}</p>
            </div>
          ) : (
            <GroupedDeviceList
              devices={devices}
              groups={groups}
              currentDeviceId={currentDeviceId}
              onSelectDevice={onSelectDevice}
              onConnectWifi={onConnectWifi}
              onDisconnectWifi={onDisconnectWifi}
              onRefreshDevices={onRefreshDevices}
              onRefreshGroups={refreshGroups}
              onBatchExecute={onBatchExecute}
              showToast={showToast}
            />
          )}
        </div>

        <Separator className="mx-4" />

        {/* Bottom actions */}
        <div className="p-3 space-y-2">
          <Button variant="default" onClick={() => setShowAddDialog(true)} className="w-full justify-start gap-2">
            <Plus className="h-4 w-4" />
            {t.deviceSidebar?.addDevice ?? '添加设备'}
          </Button>
          {onRefreshDevices && (
            <Button variant="outline" onClick={onRefreshDevices} className="w-full justify-start gap-2">
              <RefreshCw className="h-4 w-4" />
              {t.deviceSidebar?.refreshDevices ?? '刷新设备'}
            </Button>
          )}
          {onOpenGroupManager && (
            <Button variant="outline" onClick={onOpenGroupManager} className="w-full justify-start gap-2">
              <FolderCog className="h-4 w-4" />
              {t.deviceSidebar?.manageGroups ?? '管理分组'}
            </Button>
          )}
          <Button variant="outline" onClick={onOpenConfig} className="w-full justify-start gap-2">
            <Settings className="h-4 w-4" />
            {t.deviceSidebar?.settings ?? '设置'}
          </Button>
        </div>
      </div>

      {/* Add Device Dialog */}
      <AddDeviceDialog open={showAddDialog} onClose={() => setShowAddDialog(false)} />
    </>
  );
}
