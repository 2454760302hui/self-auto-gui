import * as React from 'react';

interface CentralWorkAreaProps {
  children?: React.ReactNode;
}

export function CentralWorkArea({ children }: CentralWorkAreaProps) {
  return (
    <main className="flex-1 flex flex-col overflow-hidden bg-background">
      {/* Split View Container */}
      <div className="flex-1 flex overflow-hidden gap-4 p-4">
        {/* Left: Screen Casting Area */}
        <div className="flex-1 flex flex-col rounded-lg border border-border bg-black overflow-hidden">
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 rounded-lg bg-secondary/50 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">📱</span>
              </div>
              <p className="text-muted-foreground text-sm">
                Select a device to start casting
              </p>
            </div>
          </div>
          {/* Casting Toolbar */}
          <div className="h-12 border-t border-border bg-card/50 flex items-center justify-center gap-2 px-4">
            <button className="px-3 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 transition-colors">
              Screenshot
            </button>
            <button className="px-3 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 transition-colors">
              Record
            </button>
            <button className="px-3 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 transition-colors">
              Fullscreen
            </button>
          </div>
        </div>

        {/* Right: Recording Panel */}
        <div className="w-80 flex flex-col rounded-lg border border-border bg-card overflow-hidden">
          <div className="h-12 border-b border-border px-4 flex items-center justify-between">
            <h3 className="font-semibold text-sm">Recording</h3>
            <div className="flex items-center gap-2">
              <button className="px-3 py-1 text-xs rounded bg-success text-white hover:bg-success/90 transition-colors">
                Start
              </button>
              <button className="px-3 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 transition-colors">
                Stop
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="text-center text-muted-foreground text-sm">
              <p>No recording in progress</p>
              <p className="text-xs mt-2">Operations will appear here</p>
            </div>
          </div>
        </div>
      </div>

      {/* Code Editor Area */}
      <div className="h-48 border-t border-border bg-card rounded-t-lg flex flex-col overflow-hidden">
        <div className="h-10 border-b border-border px-4 flex items-center gap-2">
          <button className="px-3 py-1 text-xs rounded bg-primary/10 text-primary font-medium">
            Pytest
          </button>
          <button className="px-3 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 transition-colors">
            YAML
          </button>
          <div className="flex-1" />
          <button className="px-3 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 transition-colors">
            Copy
          </button>
          <button className="px-3 py-1 text-xs rounded bg-primary hover:bg-primary/90 transition-colors text-white">
            Execute
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4 font-mono text-sm text-muted-foreground">
          <p># Generated code will appear here</p>
        </div>
      </div>

      {/* Main Content */}
      {children}
    </main>
  );
}
