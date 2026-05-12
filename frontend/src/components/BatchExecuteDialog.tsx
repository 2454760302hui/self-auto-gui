import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle, XCircle, Send, Smartphone } from 'lucide-react';
import { batchExecute, type BatchTaskResult } from '../api';

interface BatchExecuteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deviceIds: string[];
  deviceNames?: Record<string, string>;
  onComplete?: () => void;
}

export function BatchExecuteDialog({
  open,
  onOpenChange,
  deviceIds,
  deviceNames = {},
  onComplete,
}: BatchExecuteDialogProps) {
  const [message, setMessage] = useState('');
  const [executing, setExecuting] = useState(false);
  const [results, setResults] = useState<BatchTaskResult[]>([]);
  const [done, setDone] = useState(false);

  const handleExecute = async () => {
    if (!message.trim() || deviceIds.length === 0) return;
    setExecuting(true);
    setResults([]);
    setDone(false);
    try {
      const res = await batchExecute(deviceIds, message);
      setResults(res.results);
      setDone(true);
      onComplete?.();
    } catch (err) {
      console.error('Batch execute failed:', err);
    } finally {
      setExecuting(false);
    }
  };

  const handleClose = () => {
    setMessage('');
    setResults([]);
    setDone(false);
    onOpenChange(false);
  };

  const successCount = results.filter(r => r.status === 'submitted').length;
  const failCount = results.filter(r => r.status === 'failed').length;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>批量执行任务</DialogTitle>
          <DialogDescription>
            向 {deviceIds.length} 台设备同时发送指令
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Device chips */}
          <div className="flex flex-wrap gap-1.5">
            {deviceIds.map(id => (
              <Badge key={id} variant="outline" className="text-xs">
                <Smartphone className="w-3 h-3 mr-1" />
                {deviceNames[id] || id}
              </Badge>
            ))}
          </div>

          <Textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            placeholder="输入要批量执行的指令..."
            rows={3}
            disabled={executing}
          />

          {/* Results */}
          {results.length > 0 && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              <div className="flex gap-2 text-xs">
                <span className="text-emerald-600">成功: {successCount}</span>
                <span className="text-red-600">失败: {failCount}</span>
              </div>
              {results.map(r => (
                <div
                  key={r.device_id}
                  className={`flex items-center gap-2 text-sm rounded-lg p-2 ${
                    r.status === 'submitted'
                      ? 'bg-emerald-50 dark:bg-emerald-950/20'
                      : 'bg-red-50 dark:bg-red-950/20'
                  }`}
                >
                  {r.status === 'submitted' ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                  )}
                  <span className="truncate">
                    {deviceNames[r.device_id] || r.device_id}
                  </span>
                  {r.error && (
                    <span className="text-xs text-red-500 truncate ml-auto">
                      {r.error}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            {done ? '关闭' : '取消'}
          </Button>
          {!done && (
            <Button
              variant="default"
              onClick={handleExecute}
              disabled={executing || !message.trim()}
            >
              {executing ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : (
                <Send className="w-4 h-4 mr-1" />
              )}
              批量执行
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
