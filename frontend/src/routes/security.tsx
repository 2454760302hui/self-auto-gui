import { createFileRoute } from '@tanstack/react-router';
import * as React from 'react';
import {
  Shield,
  Play,
  Square,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  Download,
  Copy,
  RefreshCw,
  Globe,
  ChevronDown,
  ChevronUp,
  XCircle,
  Bug,
  Clock,
  Activity,
} from 'lucide-react';
import {
  startSecurityScan,
  getSecurityScanStatus,
  getSecurityScanResult,
  listSecurityScans,
  deleteSecurityScan,
  exportSecurityReport,
  SCAN_TYPE_OPTIONS,
  SEVERITY_COLORS,
  type SecurityVuln,
  type SecurityScanSummary,
} from '../lib/security-api';
import { Toast, type ToastType } from '../components/Toast';
import { Button } from '@/components/ui/button';

export const Route = createFileRoute('/security')({
  component: SecurityPage,
});

function SeverityBadge({ severity }: { severity: string }) {
  const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS['info'];
  const icons: Record<string, React.ElementType> = {
    critical: XCircle,
    high: AlertTriangle,
    medium: Bug,
    low: Activity,
    info: CheckCircle2,
  };
  const Icon = icons[severity] || Activity;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${colors}`}>
      <Icon className="w-3 h-3" />
      {severity.toUpperCase()}
    </span>
  );
}

function SecurityPage() {
  const [targetUrl, setTargetUrl] = React.useState('https://httpbin.org');
  const [scanType, setScanType] = React.useState('quick');
  const [isScanning, setIsScanning] = React.useState(false);
  const [scanProgress, setScanProgress] = React.useState(0);
  const [currentTaskId, setCurrentTaskId] = React.useState('');
  const [scans, setScans] = React.useState<SecurityScanSummary[]>([]);
  const [selectedScan, setSelectedScan] = React.useState<SecurityScanSummary | null>(null);
  const [vulns, setVulns] = React.useState<SecurityVuln[]>([]);
  const [expandedVuln, setExpandedVuln] = React.useState<string | null>(null);
  const [showHistory, setShowHistory] = React.useState(true);
  const [toast, setToast] = React.useState({ message: '', type: 'info' as ToastType, visible: false });

  const showToast = (message: string, type: ToastType = 'info') => {
    setToast({ message, type, visible: true });
    setTimeout(() => setToast(p => ({ ...p, visible: false })), 3500);
  };

  // Simple log function (logs to console for now)
  const addLog = (type: string, content: string) => {
    console.log(`[${type}] ${content}`);
  };

  const loadScans = React.useCallback(async () => {
    try {
      const result = await listSecurityScans();
      setScans(result.scans);
    } catch { setScans([]); }
  }, []);

  React.useEffect(() => { loadScans(); }, [loadScans]);

  const startScan = async () => {
    if (!targetUrl.trim()) { showToast('请输入目标 URL', 'warning'); return; }
    if (!targetUrl.startsWith('http')) { showToast('URL 必须以 http:// 或 https:// 开头', 'warning'); return; }

    setIsScanning(true);
    setScanProgress(0);
    setVulns([]);
    setSelectedScan(null);

    try {
      addLog('info', `▶ 启动扫描 [${scanType}] → ${targetUrl}`);
      const result = await startSecurityScan({
        target_url: targetUrl,
        scan_type: scanType as 'quick' | 'full' | 'xss' | 'sqli' | 'cmd',
      });

      if (result.success) {
        setCurrentTaskId(result.task_id);
        addLog('success', `✓ 扫描已启动 (ID: ${result.task_id})`);
        showToast('扫描已启动，正在进行中...', 'info');
        pollScanStatus(result.task_id);
      } else {
        addLog('error', `✗ 启动失败: ${result.error}`);
        showToast(`启动失败: ${result.error}`, 'error');
        setIsScanning(false);
      }
    } catch (e) {
      addLog('error', `✗ 异常: ${e}`);
      showToast('扫描启动异常', 'error');
      setIsScanning(false);
    }
  };

  const pollScanStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await getSecurityScanStatus(taskId);
        setScanProgress(status.progress_percent);
        if (status.status === 'completed') {
          clearInterval(interval);
          setIsScanning(false);
          setScanProgress(100);
          addLog('success', `✓ 扫描完成，发现 ${status.vulns_found} 个漏洞`);
          const result = await getSecurityScanResult(taskId);
          if (result.success) {
            setVulns(result.vulns || []);
          }
          loadScans();
          showToast(`扫描完成，发现 ${status.vulns_found} 个漏洞`, status.vulns_found > 0 ? 'warning' : 'success');
        } else if (status.status === 'failed') {
          clearInterval(interval);
          setIsScanning(false);
          addLog('error', `✗ 扫描失败: ${status.message}`);
          showToast('扫描失败', 'error');
        }
      } catch {
        clearInterval(interval);
        setIsScanning(false);
      }
    }, 2000);
  };

  const loadScanResult = async (scan: SecurityScanSummary) => {
    setSelectedScan(scan);
    try {
      const result = await getSecurityScanResult(scan.task_id);
      if (result.success) {
        setVulns(result.vulns || []);
        addLog('info', `已加载扫描记录: ${scan.target_url}`);
      }
    } catch {
      showToast('加载扫描结果失败', 'error');
    }
  };

  const handleDeleteScan = async (taskId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteSecurityScan(taskId);
    if (selectedScan?.task_id === taskId) {
      setSelectedScan(null);
      setVulns([]);
    }
    loadScans();
    showToast('扫描记录已删除', 'success');
  };

  const handleExport = async (format: 'json' | 'html') => {
    if (!currentTaskId && !selectedScan) return;
    try {
      const result = await exportSecurityReport(currentTaskId || selectedScan!.task_id, format);
      if (result.success && result.report_content) {
        navigator.clipboard.writeText(result.report_content);
        showToast(`${format.toUpperCase()} 报告已复制`, 'success');
      }
    } catch {
      showToast('导出失败', 'error');
    }
  };

  const stats = {
    total: vulns.length,
    critical: vulns.filter(v => v.severity === 'critical').length,
    high: vulns.filter(v => v.severity === 'high').length,
    medium: vulns.filter(v => v.severity === 'medium').length,
    low: vulns.filter(v => v.severity === 'low').length,
    info: vulns.filter(v => v.severity === 'info').length,
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {toast.visible && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(p => ({ ...p, visible: false }))} />
      )}

      {/* Header */}
      <div className="px-6 py-3 border-b border-border flex items-center justify-between flex-shrink-0"
        style={{ borderColor: 'rgba(239,68,68,0.1)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold">
              <span style={{ background: 'linear-gradient(135deg, #ef4444, #f97316)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                安全测试
              </span>
            </h1>
            <p className="text-[11px] text-muted-foreground">Xray + Rad 漏洞扫描引擎</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={loadScans} title="刷新">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Main Panel */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Scan Config */}
          <div className="px-6 py-4 border-b border-border flex-shrink-0"
            style={{ borderColor: 'rgba(239,68,68,0.08)', background: 'rgba(239,68,68,0.02)' }}>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="text-[11px] font-medium text-muted-foreground mb-1 block">目标 URL</label>
                <input
                  value={targetUrl}
                  onChange={e => setTargetUrl(e.target.value)}
                  placeholder="https://example.com"
                  disabled={isScanning}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none focus:ring-1 focus:ring-red-500/50 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="text-[11px] font-medium text-muted-foreground mb-1 block">扫描类型</label>
                <select
                  value={scanType}
                  onChange={e => setScanType(e.target.value)}
                  disabled={isScanning}
                  className="px-3 py-2 rounded-lg border border-border bg-card text-sm focus:outline-none disabled:opacity-50"
                >
                  {SCAN_TYPE_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <Button
                className="gap-2"
                onClick={startScan}
                disabled={isScanning}
              >
                {isScanning ? (
                  <><Loader2 className="w-4 h-4 animate-spin" />扫描中...</>
                ) : (
                  <><Play className="w-4 h-4" />开始扫描</>
                )}
              </Button>
            </div>

            {/* Progress */}
            {isScanning && (
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] text-muted-foreground">扫描进度</span>
                  <span className="text-[11px] font-medium text-red-400">{scanProgress}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${scanProgress}%`, background: 'linear-gradient(90deg, #ef4444, #f97316)' }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Vulnerability Results */}
          <div className="flex-1 overflow-y-auto p-6 min-h-0">
            {vulns.length > 0 && (
              <div className="mb-6">
                {/* Stats */}
                <div className="grid grid-cols-5 gap-3 mb-4">
                  {[
                    { label: '总计', value: stats.total, color: 'text-foreground' },
                    { label: '严重', value: stats.critical, color: 'text-red-400' },
                    { label: '高危', value: stats.high, color: 'text-orange-400' },
                    { label: '中危', value: stats.medium, color: 'text-yellow-400' },
                    { label: '低危', value: stats.low, color: 'text-blue-400' },
                  ].map(s => (
                    <div key={s.label} className="text-center p-3 rounded-xl bg-card border border-border">
                      <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                      <div className="text-[10px] text-muted-foreground mt-0.5">{s.label}</div>
                    </div>
                  ))}
                </div>

                {/* Vuln List */}
                <div className="space-y-2">
                  {vulns.map(v => (
                    <div key={v.id} className="rounded-xl border border-border bg-card overflow-hidden">
                      <button
                        onClick={() => setExpandedVuln(expandedVuln === v.id ? null : v.id)}
                        className="w-full flex items-center justify-between p-4 hover:bg-secondary/20 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <SeverityBadge severity={v.severity} />
                          <div className="text-left">
                            <div className="text-sm font-medium">{v.name}</div>
                            <div className="text-[10px] text-muted-foreground flex items-center gap-1 mt-0.5">
                              <Globe className="w-3 h-3" />
                              {v.url}
                            </div>
                          </div>
                        </div>
                        {expandedVuln === v.id ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                      </button>
                      {expandedVuln === v.id && (
                        <div className="px-4 pb-4 border-t border-border text-xs space-y-2 pt-3"
                          style={{ borderColor: 'rgba(239,68,68,0.08)' }}>
                          <div>
                            <div className="font-semibold text-muted-foreground mb-1">漏洞类型</div>
                            <div className="text-foreground">{v.vuln_type}</div>
                          </div>
                          <div>
                            <div className="font-semibold text-muted-foreground mb-1">详细信息</div>
                            <div className="text-foreground leading-relaxed">{v.detail}</div>
                          </div>
                          {v.payload && (
                            <div>
                              <div className="font-semibold text-muted-foreground mb-1">Payload</div>
                              <div className="font-mono bg-secondary/50 px-2 py-1 rounded text-[10px] text-red-400 break-all">
                                {v.payload}
                              </div>
                            </div>
                          )}
                          <div>
                            <div className="font-semibold text-muted-foreground mb-1">发现时间</div>
                            <div>{new Date(v.timestamp).toLocaleString('zh-CN')}</div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {vulns.length === 0 && !isScanning && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500/10 to-orange-500/10 border border-red-500/20 flex items-center justify-center mb-4">
                  <Shield className="w-8 h-8 text-red-400/50" />
                </div>
                <h3 className="font-semibold text-lg mb-2">安全扫描中心</h3>
                <p className="text-sm text-muted-foreground max-w-md mb-6">
                  输入目标 URL 并选择扫描类型，Xray + Rad 引擎将自动检测 SQL注入、XSS跨站脚本、命令注入等安全漏洞。
                </p>
                <div className="grid grid-cols-3 gap-3 max-w-xl">
                  {SCAN_TYPE_OPTIONS.slice(0, 3).map(o => (
                    <div key={o.value} className="p-3 rounded-xl border border-border bg-card text-left">
                      <div className="text-xs font-medium mb-1">{o.label}</div>
                      <div className="text-[10px] text-muted-foreground">{o.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - History */}
        <div className="w-72 border-l border-border flex flex-col overflow-hidden flex-shrink-0"
          style={{ borderColor: 'rgba(239,68,68,0.1)' }}>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0 hover:bg-secondary/20 transition-colors"
            style={{ borderColor: 'rgba(239,68,68,0.08)' }}
          >
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">扫描历史</span>
              <span className="text-[10px] text-muted-foreground bg-secondary/50 px-1.5 py-0.5 rounded-full">{scans.length}</span>
            </div>
            {showHistory ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>

          {showHistory && (
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {scans.length === 0 && (
                <div className="text-center py-8">
                  <Shield className="w-8 h-8 mx-auto mb-2 text-muted-foreground/30" />
                  <p className="text-xs text-muted-foreground">暂无扫描记录</p>
                </div>
              )}
              {scans.map(scan => (
                <button
                  key={scan.task_id}
                  onClick={() => loadScanResult(scan)}
                  className={`w-full text-left p-3 rounded-xl transition-all border ${
                    selectedScan?.task_id === scan.task_id
                      ? 'border-red-500/30 bg-red-500/5'
                      : 'border-border hover:border-red-500/20 hover:bg-secondary/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <SeverityBadge severity={
                      scan.severity_counts.critical > 0 ? 'critical' :
                      scan.severity_counts.high > 0 ? 'high' :
                      scan.severity_counts.medium > 0 ? 'medium' :
                      'info'
                    } />
                    <button
                      onClick={e => handleDeleteScan(scan.task_id, e)}
                      className="p-0.5 hover:bg-red-500/10 rounded transition-colors"
                    >
                      <Trash2 className="w-3 h-3 text-muted-foreground hover:text-red-400" />
                    </button>
                  </div>
                  <div className="text-[11px] truncate mb-0.5">{new URL(scan.target_url).hostname}</div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{scan.scan_type}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {((scan.duration_ms || 0) / 1000).toFixed(1)}s
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {scan.severity_counts.critical > 0 && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-400">{scan.severity_counts.critical} 严重</span>
                    )}
                    {scan.severity_counts.high > 0 && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-orange-500/10 text-orange-400">{scan.severity_counts.high} 高危</span>
                    )}
                    {scan.total === 0 && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">无漏洞</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Simple log display - logs shown in scan results
