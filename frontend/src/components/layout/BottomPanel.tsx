import * as React from 'react';
import { ChevronUp, X, Send } from 'lucide-react';

interface BottomPanelProps {
  height?: number;
  onHeightChange?: (height: number) => void;
  onClose?: () => void;
}

export function BottomPanel({
  height = 128,
  onHeightChange,
  onClose,
}: BottomPanelProps) {
  const [isDragging, setIsDragging] = React.useState(false);
  const panelRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!panelRef.current) return;
      const container = panelRef.current.parentElement;
      if (!container) return;

      const newHeight = container.clientHeight - e.clientY;
      const minHeight = 80;
      const maxHeight = container.clientHeight - 200;

      if (newHeight >= minHeight && newHeight <= maxHeight) {
        onHeightChange?.(newHeight);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, onHeightChange]);

  return (
    <div
      ref={panelRef}
      style={{ height: `${height}px` }}
      className="border-t border-border bg-card flex flex-col overflow-hidden"
    >
      {/* Drag Handle */}
      <div
        onMouseDown={() => setIsDragging(true)}
        className="h-1 bg-border hover:bg-primary/50 cursor-ns-resize transition-colors"
      />

      {/* Header */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
          <h3 className="font-semibold text-sm">智能助手</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-secondary rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col">
        <div className="flex-1 space-y-3 mb-4">
          {/* Sample messages */}
          <div className="flex gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
              <span className="text-xs">🤖</span>
            </div>
            <div className="bg-secondary/50 rounded-lg px-3 py-2 max-w-xs">
              <p className="text-sm text-foreground">
                Hello! I'm your AI assistant. Describe what you'd like to automate.
              </p>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="flex gap-2 mt-auto">
          <input
            type="text"
            placeholder="Describe your task..."
            className="flex-1 px-3 py-2 rounded-lg bg-secondary/50 border border-border text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary"
          />
          <button className="px-3 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white transition-colors flex items-center gap-1">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
