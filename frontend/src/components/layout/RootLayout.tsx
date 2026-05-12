import * as React from 'react';
import { TopNavBar } from './TopNavBar';
import { LeftSidebar } from './LeftSidebar';
import { CentralWorkArea } from './CentralWorkArea';
import { Toaster } from '../Toaster';
import { Keyboard } from 'lucide-react';
import { useGlobalKeyboard } from '@/hooks/useGlobalKeyboard';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';

interface RootLayoutProps {
  children?: React.ReactNode;
}

const SHORTCUTS = [
  { key: '?', shiftKey: true, description: '显示快捷键帮助' },
  { key: 'b', ctrlKey: true, description: '切换侧边栏' },
  { key: 'Escape', description: '关闭弹窗' },
];

export function RootLayout({ children }: RootLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [showShortcuts, setShowShortcuts] = React.useState(false);

  useGlobalKeyboard([
    { key: '?', shiftKey: true, handler: () => setShowShortcuts(v => !v) },
    { key: 'b', ctrlKey: true, handler: () => setSidebarOpen(v => !v) },
    { key: 'Escape', handler: () => setShowShortcuts(false) },
  ]);

  return (
    <>
      <div className="h-screen flex flex-col overflow-hidden bg-background">
        {/* Top Navigation Bar */}
        <TopNavBar onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Sidebar */}
          {sidebarOpen && (
            <LeftSidebar
              onClose={() => setSidebarOpen(false)}
            />
          )}

          {/* Central Work Area or Custom Content */}
          {children || <CentralWorkArea />}
        </div>
      </div>

      <Toaster />

      {/* Keyboard Shortcuts Dialog */}
      <Dialog open={showShortcuts} onOpenChange={setShowShortcuts}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Keyboard className="w-5 h-5 text-primary" />
              快捷键
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {SHORTCUTS.map(s => (
              <div key={s.key} className="flex items-center justify-between py-1.5">
                <span className="text-sm text-muted-foreground">{s.description}</span>
                <kbd className="px-2 py-0.5 rounded bg-secondary border border-border text-xs font-mono">
                  {s.key === 'Escape' ? 'Esc' : s.key}
                </kbd>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
