import React, { Component, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  handleReset = () => this.setState({ hasError: false, error: null });

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-48 gap-4 p-8">
          <div className="w-14 h-14 rounded-2xl bg-red-500/10 flex items-center justify-center">
            <AlertTriangle className="w-7 h-7 text-red-500" />
          </div>
          <div className="text-center max-w-sm">
            <h3 className="text-base font-semibold mb-1">页面加载失败</h3>
            <p className="text-sm text-muted-foreground mb-1">
              此模块发生了意外错误，请尝试重新加载。
            </p>
            {this.state.error && (
              <p className="text-xs text-muted-foreground/60 font-mono mt-2 px-3 py-2 bg-destructive/5 rounded-lg border border-destructive/10">
                {this.state.error.message}
              </p>
            )}
          </div>
          <Button onClick={this.handleReset} className="gap-2">
            <RefreshCw className="w-4 h-4" />
            重试
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
