import * as React from 'react';
import { Menu, HelpCircle, Settings } from 'lucide-react';
import { ThemeToggle } from '../ThemeToggle';
import { useLocale } from '../../lib/i18n-context';
import { Globe, Github } from 'lucide-react';

interface TopNavBarProps {
  onToggleSidebar?: () => void;
}

export function TopNavBar({ onToggleSidebar }: TopNavBarProps) {
  const { locale, setLocale, localeName } = useLocale();

  const toggleLocale = () => {
    setLocale(locale === 'en' ? 'zh' : 'en');
  };

  return (
    <header
      className="h-14 border-b flex items-center justify-between px-6 sticky top-0 z-40"
      style={{
        background: 'rgba(12,15,26,0.8)',
        backdropFilter: 'blur(12px)',
        borderColor: 'rgba(124,58,237,0.15)',
      }}
    >
      {/* Left Section - Logo & Menu */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleSidebar}
          className="p-2 hover:bg-secondary/50 rounded-lg transition-colors"
          title="切换侧边栏"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <div className="relative flex items-center justify-center">
            {/* 最外层：最大范围柔和光晕 */}
            <div className="absolute w-12 h-12 rounded-lg animate-logo-breathe-outer bg-gradient-to-br from-indigo-500 via-violet-600 to-cyan-500" />
            {/* 中层：中等范围光晕 */}
            <div className="absolute w-10 h-10 rounded-lg animate-logo-breathe-mid bg-gradient-to-br from-indigo-400 via-violet-500 to-cyan-400" />
            {/* 内层：核心光效 */}
            <div className="w-8 h-8 rounded-lg relative z-10 bg-gradient-to-br from-indigo-600 via-violet-700 to-cyan-700 flex items-center justify-center animate-logo-breathe-core shadow-lg">
              <span className="text-white font-black text-sm tracking-widest" style={{ textShadow: '0 0 8px rgba(139,92,246,0.9), 0 0 16px rgba(6,182,212,0.5)' }}>N</span>
            </div>
          </div>
          <h1 className="text-lg font-bold nextagent-gradient-text">AutoGLM</h1>
        </div>
      </div>

      {/* Center Section - Module Tabs */}
      <div className="flex items-center gap-1">
        <span className="text-[11px] text-muted-foreground mr-2 hidden lg:block">模块：</span>
        <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-secondary/30 border border-border">
          <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
          <span className="text-xs text-muted-foreground">4 模块运行中</span>
        </div>
      </div>

      {/* Right Section - Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleLocale}
          className="p-2 hover:bg-secondary/50 rounded-lg transition-colors flex items-center gap-1"
          title="切换语言"
        >
          <Globe className="w-4 h-4" />
          <span className="text-xs hidden sm:inline">{localeName}</span>
        </button>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 hover:bg-secondary/50 rounded-lg transition-colors"
          title="GitHub"
        >
          <Github className="w-4 h-4" />
        </a>
        <button
          className="p-2 hover:bg-secondary/50 rounded-lg transition-colors"
          title="帮助"
        >
          <HelpCircle className="w-4 h-4" />
        </button>
        <ThemeToggle />
        <button
          className="p-2 hover:bg-secondary/50 rounded-lg transition-colors"
          title="设置"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
