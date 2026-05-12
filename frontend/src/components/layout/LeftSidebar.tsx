import * as React from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import {
  Globe,
  Shield,
  Zap,
  Smartphone,
  Terminal,
  ChevronRight,
  Layers,
  X,
} from 'lucide-react';

interface ModuleItem {
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
  badge?: string;
  href: string;
  group: string;
}

interface LeftSidebarProps {
  onClose?: () => void;
}

const MODULES: ModuleItem[] = [
  // 自动化模块
  { label: '投屏预览', description: '实时设备画面', icon: Globe, color: 'cyan', href: '/cast', group: 'automation' },
  { label: '设备控制', description: '触控操作面板', icon: Smartphone, color: 'emerald', href: '/automation', group: 'automation' },
  { label: '终端', description: 'ADB 命令行', icon: Terminal, color: 'slate', href: '/terminal', group: 'automation' },
  // 浏览器自动化模块
  { label: '浏览器自动化', description: 'NLP/DSL Web 控制', icon: Globe, color: 'violet', href: '/browser', group: 'browser', badge: 'NEW' },
  { label: 'API 测试', description: 'YAML 接口测试', icon: Zap, color: 'cyan', href: '/api-testing', group: 'browser', badge: 'NEW' },
  { label: '安全测试', description: '漏洞扫描工具', icon: Shield, color: 'red', href: '/security', group: 'browser', badge: 'NEW' },
  // 管理模块
  { label: '定时任务', description: 'Cron 调度', icon: Zap, color: 'amber', href: '/scheduled-tasks', group: 'manage' },
  { label: '历史记录', description: '任务执行历史', icon: Layers, color: 'slate', href: '/history', group: 'manage' },
  { label: '日志', description: '系统日志查看', icon: Terminal, color: 'slate', href: '/logs', group: 'manage' },
];

const GROUPS = [
  { key: 'automation', label: '自动化', color: '#06b6d4' },
  { key: 'browser', label: '浏览器自动化', color: '#7c3aed' },
  { key: 'manage', label: '管理与调度', color: '#f59e0b' },
];

export function LeftSidebar({ onClose }: LeftSidebarProps) {
  const location = useLocation();
  const [collapsedGroups, setCollapsedGroups] = React.useState<Set<string>>(new Set());

  const toggleGroup = (key: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const groupedModules = GROUPS.map(g => ({
    ...g,
    items: MODULES.filter(m => m.group === g.key),
  }));

  const isActive = (href: string) => location.pathname === href || location.pathname.startsWith(href + '/');

  return (
    <aside className="w-64 border-r border-border bg-sidebar flex flex-col overflow-hidden flex-shrink-0"
      style={{ borderColor: 'rgba(124,58,237,0.1)' }}>
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-4"
        style={{ borderColor: 'rgba(124,58,237,0.1)' }}>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-cyan-500 flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-xs">N</span>
          </div>
          <div>
            <span className="font-bold text-sm nextagent-gradient-text">AutoGLM</span>
            <p className="text-[10px] text-muted-foreground leading-tight">设备控制台</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-secondary rounded transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Module Navigation */}
      <div className="flex-1 overflow-y-auto py-2">
        {groupedModules.map(group => (
          <div key={group.key} className="mb-1">
            {/* Group Header */}
            <button
              onClick={() => toggleGroup(group.key)}
              className="w-full flex items-center justify-between px-4 py-2 hover:bg-secondary/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: group.color }} />
                <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  {group.label}
                </span>
              </div>
              <ChevronRight className={`w-3 h-3 text-muted-foreground/50 transition-transform duration-200 ${collapsedGroups.has(group.key) ? '' : 'rotate-90'}`} />
            </button>

            {/* Group Items */}
            {!collapsedGroups.has(group.key) && (
              <div className="px-2 space-y-0.5 pb-1">
                {group.items.map(item => {
                  const active = isActive(item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      to={item.href}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all group ${
                        active
                          ? 'bg-primary/15 text-primary border border-primary/20'
                          : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground border border-transparent'
                      }`}
                      style={active ? {
                        background: 'rgba(124,58,237,0.1)',
                        borderColor: 'rgba(124,58,237,0.2)',
                      } : {}}
                    >
                      <Icon
                        className={`w-4 h-4 flex-shrink-0 ${
                          active ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-xs">{item.label}</span>
                          {item.badge && (
                            <span className="text-[9px] font-bold px-1 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/20">
                              {item.badge}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-muted-foreground/70 leading-tight">{item.description}</p>
                      </div>
                      {active && (
                        <div className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                      )}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer Status */}
      <div className="px-4 py-3 border-t border-border"
        style={{ borderColor: 'rgba(124,58,237,0.1)' }}>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="text-xs text-muted-foreground">系统就绪</span>
        </div>
      </div>
    </aside>
  );
}
