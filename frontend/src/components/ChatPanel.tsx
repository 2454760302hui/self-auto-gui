import React, { useRef, useEffect, useCallback, useState } from 'react';
import {
  Send,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  History,
  ListChecks,
  Loader2,
  Square,
  Zap,
} from 'lucide-react';
import { throttle } from 'lodash';
import type {
  StepTimingSummary,
  Workflow,
  HistoryRecordResponse,
} from '../api';
import {
  listWorkflows,
  listHistory,
  clearHistory as clearHistoryApi,
  deleteHistoryRecord,
} from '../api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTranslation } from '../lib/i18n-context';
import { HistoryItemCard } from './HistoryItemCard';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { ImagePreview } from '@/components/ui/image-preview';
import {
  useTaskSessionConversation,
  type TaskConversationMessage,
} from '../hooks/useTaskSessionConversation';
import { QuickControlPanel } from './QuickControlPanel';

interface ActionPayload {
  action?: string;
  element?: [number, number];
  start?: [number, number];
  end?: [number, number];
  [key: string]: unknown;
}

interface ChatPanelProps {
  deviceId: string;
  deviceSerial: string;
  deviceName: string;
  deviceConnectionType?: string;
  isConfigured: boolean;
  unlimitedStepsEnabled?: boolean;
  onOpenCast?: () => void;
}

function getStepSummary(thinking: string | undefined, action: unknown): string {
  if (thinking && thinking.trim().length > 0) {
    return thinking;
  }

  if (action && typeof action === 'object') {
    const actionRecord = action as Record<string, unknown>;
    const metadata = actionRecord['_metadata'];

    if (metadata === 'finish') {
      const finishMessage = actionRecord['message'];
      if (
        typeof finishMessage === 'string' &&
        finishMessage.trim().length > 0
      ) {
        return `Finish: ${finishMessage}`;
      }
      return 'Finish task';
    }

    const actionName = actionRecord['action'];
    if (typeof actionName === 'string' && actionName.trim().length > 0) {
      return `Action: ${actionName}`;
    }
  }

  return 'Action executed';
}

function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

function getTimingChips(
  timings: StepTimingSummary | undefined
): Array<{ label: string; value: string }> {
  if (!timings) {
    return [];
  }

  const chips = [
    { label: 'Total', value: formatDuration(timings.total_duration_ms) },
    { label: 'LLM', value: formatDuration(timings.llm_duration_ms) },
  ];

  if (timings.screenshot_duration_ms > 0) {
    chips.push({
      label: 'Shot',
      value: formatDuration(timings.screenshot_duration_ms),
    });
  }

  if (timings.current_app_duration_ms > 0) {
    chips.push({
      label: 'App',
      value: formatDuration(timings.current_app_duration_ms),
    });
  }

  if (timings.execute_action_duration_ms > 0) {
    chips.push({
      label: 'Action',
      value: formatDuration(timings.execute_action_duration_ms),
    });
  }

  if (timings.sleep_duration_ms > 0) {
    chips.push({
      label: 'Sleep',
      value: formatDuration(timings.sleep_duration_ms),
    });
  }

  return chips;
}

export function ChatPanel({
  deviceId,
  deviceSerial,
  deviceName,
  deviceConnectionType,
  isConfigured,
  unlimitedStepsEnabled = false,
  onOpenCast,
}: ChatPanelProps) {
  const t = useTranslation();
  const [mode, setMode] = useState<'ai' | 'quick'>('ai');
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showHistoryPopover, setShowHistoryPopover] = useState(false);
  const [historyItems, setHistoryItems] = useState<HistoryRecordResponse[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [showWorkflowPopover, setShowWorkflowPopover] = useState(false);
  const {
    messages,
    setMessages,
    loading,
    aborting,
    error,
    sessionReady,
    sendMessage,
    resetConversation,
    abortConversation,
  } = useTaskSessionConversation({
    deviceId,
    deviceSerial,
    sessionStorageKey: `autoglm:classic-session:${deviceSerial}`,
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(0);
  const prevMessageSigRef = useRef<string | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showNewMessageNotice, setShowNewMessageNotice] = useState(false);
  const throttledUpdateScrollStateRef = useRef<ReturnType<
    typeof throttle
  > | null>(null);

  // Cleanup throttled function on unmount
  useEffect(() => {
    const throttledFn = throttle(() => {
      const container = messagesContainerRef.current;
      if (!container) return;
      const threshold = 80;
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      const atBottom = distanceFromBottom <= 1;
      setIsAtBottom(atBottom);
      if (distanceFromBottom <= threshold) {
        setShowNewMessageNotice(false);
      }
    }, 100);
    throttledUpdateScrollStateRef.current = throttledFn;
    return () => {
      throttledFn.cancel();
      throttledUpdateScrollStateRef.current = null;
    };
  }, []);

  // Load history items when popover opens
  useEffect(() => {
    if (showHistoryPopover) {
      const loadItems = async () => {
        try {
          const data = await listHistory(deviceSerial, 20, 0);
          setHistoryItems(data.records);
        } catch (error) {
          console.error('Failed to load history:', error);
          setHistoryItems([]);
        }
      };
      loadItems();
    }
  }, [showHistoryPopover, deviceSerial]);

  const handleSelectHistory = (record: HistoryRecordResponse) => {
    const newMessages: TaskConversationMessage[] = [];

    const userMsg = record.messages.find(m => m.role === 'user');
    if (userMsg) {
      newMessages.push({
        id: `${record.id}-user`,
        role: 'user',
        content: userMsg.content || record.task_text,
        timestamp: new Date(userMsg.timestamp),
      });
    } else {
      newMessages.push({
        id: `${record.id}-user`,
        role: 'user',
        content: record.task_text,
        timestamp: new Date(record.start_time),
      });
    }

    const thinkingList: string[] = [];
    const actionsList: Record<string, unknown>[] = [];
    const screenshotsList: (string | undefined)[] = [];
    record.messages
      .filter(m => m.role === 'assistant')
      .forEach(m => {
        if (m.thinking) thinkingList.push(m.thinking);
        if (m.action) actionsList.push(m.action);
        const recordData = m as unknown as { screenshot?: string };
        screenshotsList.push(recordData.screenshot);
      });

    const agentMessage: TaskConversationMessage = {
      id: `${record.id}-agent`,
      role: 'assistant',
      content: record.final_message,
      timestamp: record.end_time
        ? new Date(record.end_time)
        : new Date(record.start_time),
      steps: record.steps,
      success: record.success,
      thinking: thinkingList,
      actions: actionsList,
      screenshots: screenshotsList,
      stepTimings: record.step_timings,
      isStreaming: false,
    };
    newMessages.push(agentMessage);

    setMessages(newMessages);

    prevMessageCountRef.current = newMessages.length;
    prevMessageSigRef.current = [
      agentMessage.id,
      agentMessage.content?.length ?? 0,
      agentMessage.currentThinking?.length ?? 0,
      agentMessage.thinking ? JSON.stringify(agentMessage.thinking).length : 0,
      agentMessage.steps ?? '',
      agentMessage.isStreaming ? 1 : 0,
    ].join('|');

    setShowNewMessageNotice(false);
    setIsAtBottom(true);
    setShowHistoryPopover(false);
  };

  const handleClearHistory = async () => {
    if (confirm(t.history.clearAllConfirm)) {
      try {
        await clearHistoryApi(deviceSerial);
        setHistoryItems([]);
      } catch (error) {
        console.error('Failed to clear history:', error);
      }
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    try {
      await deleteHistoryRecord(deviceSerial, itemId);
      setHistoryItems(prev => prev.filter(item => item.id !== itemId));
    } catch (error) {
      console.error('Failed to delete history item:', error);
    }
  };

  const handleSend = useCallback(async () => {
    const didSend = await sendMessage(input);
    if (didSend) {
      setInput('');
    }
  }, [input, sendMessage]);

  const handleReset = useCallback(async () => {
    await resetConversation();
    setShowNewMessageNotice(false);
    setIsAtBottom(true);
    prevMessageCountRef.current = 0;
    prevMessageSigRef.current = null;
  }, [resetConversation]);

  const handleAbortChat = useCallback(async () => {
    await abortConversation();
  }, [abortConversation]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    const latest = messages[messages.length - 1];
    const thinkingSignature = latest?.thinking
      ? JSON.stringify(latest.thinking).length
      : 0;
    const latestSignature = latest
      ? [
          latest.id,
          latest.content?.length ?? 0,
          latest.currentThinking?.length ?? 0,
          thinkingSignature,
          latest.steps ?? '',
          latest.isStreaming ? 1 : 0,
        ].join('|')
      : null;

    const isNewMessage = messages.length > prevMessageCountRef.current;
    const hasLatestChanged =
      latestSignature !== prevMessageSigRef.current && messages.length > 0;

    prevMessageCountRef.current = messages.length;
    prevMessageSigRef.current = latestSignature;

    if (isAtBottom) {
      scrollToBottom();
      const frameId = requestAnimationFrame(() => {
        setShowNewMessageNotice(false);
      });
      return () => cancelAnimationFrame(frameId);
    }

    if (messages.length === 0) {
      const frameId = requestAnimationFrame(() => {
        setShowNewMessageNotice(false);
      });
      return () => cancelAnimationFrame(frameId);
    }

    if (isNewMessage || hasLatestChanged) {
      const frameId = requestAnimationFrame(() => {
        setShowNewMessageNotice(true);
      });
      return () => cancelAnimationFrame(frameId);
    }
  }, [messages, isAtBottom, scrollToBottom]);

  // Load workflows
  useEffect(() => {
    const loadWorkflows = async () => {
      try {
        const data = await listWorkflows();
        setWorkflows(data.workflows);
      } catch (error) {
        console.error('Failed to load workflows:', error);
      }
    };
    loadWorkflows();
  }, []);

  const handleExecuteWorkflow = (workflow: Workflow) => {
    setInput(workflow.text);
    setShowWorkflowPopover(false);
  };

  const handleMessagesScroll = () => {
    throttledUpdateScrollStateRef.current?.();
  };

  const handleScrollToLatest = () => {
    scrollToBottom();
    setShowNewMessageNotice(false);
    setIsAtBottom(true);
  };

  const handleInputKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="flex flex-col h-full border rounded-xl overflow-hidden">
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
            mode === 'ai' ? 'bg-primary/10' : 'bg-amber-500/10'
          }`}>
            {mode === 'ai' ? (
              <Sparkles className="h-5 w-5 text-primary" />
            ) : (
              <Zap className="h-5 w-5 text-amber-500" />
            )}
          </div>
          <div>
            <h2 className="font-semibold">{deviceName}</h2>
            <p className="text-xs text-muted-foreground font-mono">{deviceId}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Mode switcher */}
          <div className="flex items-center bg-secondary/50 rounded-lg p-0.5 border border-border">
            <button
              onClick={() => setMode('quick')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'quick'
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              快速控制
            </button>
          </div>

          {mode === 'ai' && (
            <>
              {loading && unlimitedStepsEnabled && (
                <Badge
                  variant="secondary"
                  className="bg-amber-500/10 text-amber-600 dark:text-amber-400"
                >
                  无限步数
                </Badge>
              )}

              {/* 历史记录按钮 */}
          <Popover
            open={showHistoryPopover}
            onOpenChange={setShowHistoryPopover}
          >
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-lg"
                title={t.history?.title || '历史记录'}
              >
                <History className="h-4 w-4" />
              </Button>
            </PopoverTrigger>

            <PopoverContent className="w-96 p-0" align="end" sideOffset={8}>
              <div className="flex items-center justify-between p-4 border-b border-border">
                <h3 className="font-semibold text-sm">{t.history?.title || '历史记录'}</h3>
                {historyItems.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearHistory}
                    className="h-7 text-xs"
                  >
                    {t.history?.clearAll || '清空全部'}
                  </Button>
                )}
              </div>

              <ScrollArea className="h-[400px]">
                <div className="p-4 space-y-2">
                  {historyItems.length > 0 ? (
                    historyItems.map(item => (
                      <HistoryItemCard
                        key={item.id}
                        item={item}
                        onSelect={handleSelectHistory}
                        onDelete={handleDeleteItem}
                      />
                    ))
                  ) : (
                    <div className="text-center py-8">
                      <History className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                      <p className="text-sm font-medium">{t.history?.noHistory || '暂无历史记录'}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {t.history?.noHistoryDescription || '开始对话后会显示历史记录'}
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </PopoverContent>
          </Popover>

          {!isConfigured && (
            <Badge variant="warning">
              <AlertCircle className="w-3 h-3 mr-1" />
              {t.devicePanel?.noConfig || '未配置'}
            </Badge>
          )}

          <Button
            variant="ghost"
            size="icon"
            onClick={handleReset}
            className="h-8 w-8 rounded-lg"
            title="重置对话"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
            </>
          )}
        </div>
      </div>

      {/* Quick Control Mode */}
      {mode === 'quick' && (
        <div className="flex-1 min-h-0 overflow-hidden">
          <QuickControlPanel deviceId={deviceId} deviceName={deviceName} />
        </div>
      )}

      {/* AI Assistant Mode */}
      {mode === 'ai' && (
      <>
      {/* 错误消息 */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* 消息区域 */}
      <div className="flex-1 min-h-0 relative">
        <div
          className="h-full overflow-y-auto p-4"
          ref={messagesContainerRef}
          onScroll={handleMessagesScroll}
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center min-h-[calc(100%-1rem)] animate-fade-in">
              {/* 空状态欢迎页 */}
              <div className="mb-6">
                <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                  <Sparkles className="h-8 w-8 text-primary" />
                </div>
              </div>
              <h2 className="text-xl font-semibold mb-2">AI 手机助手</h2>
              <p className="text-sm text-muted-foreground max-w-xs mb-6">
                {t.devicePanel?.describeTask || '用自然语言描述任务，AI 将自动操控手机完成'}
              </p>

              {/* 使用说明 */}
              <div className="w-full max-w-md space-y-4 text-left mb-6">
                <div className="bg-secondary/50 rounded-xl p-4 border border-border">
                  <h3 className="text-sm font-semibold mb-3 text-primary">如何使用</h3>
                  <ul className="space-y-2 text-xs text-muted-foreground">
                    <li className="flex items-start gap-2">
                      <span className="font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px] flex-shrink-0 mt-0.5">1</span>
                      <span>用<strong className="text-foreground">自然语言</strong>描述你想让手机完成的任务，AI 会自动分析屏幕并执行操作</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px] flex-shrink-0 mt-0.5">2</span>
                      <span>AI 会逐步执行（点击、滑动、输入文字等），每一步都会显示截图和操作详情</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px] flex-shrink-0 mt-0.5">3</span>
                      <span>也可以点击 <strong className="text-foreground">投屏</strong> 按钮实时查看手机画面，支持鼠标和键盘操控</span>
                    </li>
                  </ul>
                </div>

                <div className="bg-secondary/50 rounded-xl p-4 border border-border">
                  <h3 className="text-sm font-semibold mb-3 text-primary">示例指令</h3>
                  <div className="space-y-1.5 text-xs text-muted-foreground">
                    <p><span className="text-foreground font-medium">打开应用：</span>打开微信</p>
                    <p><span className="text-foreground font-medium">输入文字：</span>在搜索框输入 你好</p>
                    <p><span className="text-foreground font-medium">发送消息：</span>给张三发一条消息说今天开会</p>
                    <p><span className="text-foreground font-medium">搜索内容：</span>在浏览器搜索天气预报</p>
                    <p><span className="text-foreground font-medium">系统操作：</span>打开设置，调低屏幕亮度</p>
                    <p><span className="text-foreground font-medium">截图保存：</span>截图并保存</p>
                  </div>
                </div>
              </div>

              {/* 快捷操作 */}
              <div className="flex flex-wrap gap-2 justify-center max-w-sm">
                {[
                  { label: '打开微信', cmd: '打开微信' },
                  { label: '搜索天气', cmd: '在浏览器搜索天气预报' },
                  { label: '查看消息', cmd: '打开微信查看最新消息' },
                  { label: '打开设置', cmd: '打开设置' },
                  { label: '截图保存', cmd: '截图并保存' },
                  { label: '发消息', cmd: '给张三发消息说你好' },
                ].map(item => (
                  <button
                    key={item.label}
                    className="px-3 py-1.5 rounded-full text-xs border border-border hover:bg-primary/10 hover:border-primary/30 hover:text-primary transition-all"
                    onClick={() => {
                      setInput(item.cmd);
                      setTimeout(() => {
                        textareaRef.current?.focus();
                      }, 50);
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map(message => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' ? (
                  <div className="max-w-[85%] space-y-3">
                    {/* 步骤处理 */}
                    {Array.from(
                      {
                        length: Math.max(
                          message.thinking?.length || 0,
                          message.actions?.length || 0
                        ),
                      },
                      (_, idx) => idx
                    ).map(idx => {
                      const stepThinking = message.thinking?.[idx];
                      const stepAction = message.actions?.[idx];
                      const stepScreenshot = message.screenshots?.[idx];
                      const stepTimings = message.stepTimings?.[idx];
                      const stepSummary = getStepSummary(
                        stepThinking,
                        stepAction
                      );

                      return (
                        <div
                          key={idx}
                          className="bg-secondary/50 rounded-2xl rounded-tl-sm px-4 py-3"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10">
                              <Sparkles className="h-3 w-3 text-primary" />
                            </div>
                            <span className="text-xs font-medium text-muted-foreground">
                              Step {idx + 1}
                            </span>
                          </div>
                          <p className="text-sm whitespace-pre-wrap">
                            {stepSummary}
                          </p>

                          {stepTimings && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {getTimingChips(stepTimings).map(chip => (
                                <Badge
                                  key={`${idx}-${chip.label}`}
                                  variant="secondary"
                                  className="font-mono text-[11px]"
                                >
                                  {chip.label} {chip.value}
                                </Badge>
                              ))}
                            </div>
                          )}

                          {stepScreenshot && (
                            <div className="mt-3">
                              <ImagePreview
                                src={`data:image/png;base64,${stepScreenshot}`}
                                alt={`Step ${idx + 1}`}
                                maxHeight="350px"
                              >
                                {stepAction &&
                                  (() => {
                                    const parsedAction = stepAction as ActionPayload;
                                    const actionName = parsedAction.action;

                                    if (
                                      actionName &&
                                      ['Tap', 'Double Tap', 'Long Press'].includes(actionName)
                                    ) {
                                      const element = parsedAction.element;
                                      if (Array.isArray(element) && element.length === 2) {
                                        const left = `${(Math.max(0, Math.min(element[0], 1000)) / 1000) * 100}%`;
                                        const top = `${(Math.max(0, Math.min(element[1], 1000)) / 1000) * 100}%`;
                                        return (
                                          <div
                                            className="absolute w-8 h-8 rounded-full border-[3px] border-red-500 bg-red-500/20 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.6)]"
                                            style={{ left, top }}
                                          />
                                        );
                                      }
                                    }
                                    if (actionName === 'Swipe') {
                                      const start = parsedAction.start;
                                      const end = parsedAction.end;
                                      if (Array.isArray(start) && start.length === 2 && Array.isArray(end) && end.length === 2) {
                                        const x1 = (Math.max(0, Math.min(start[0], 1000)) / 1000) * 100;
                                        const y1 = (Math.max(0, Math.min(start[1], 1000)) / 1000) * 100;
                                        const x2 = (Math.max(0, Math.min(end[0], 1000)) / 1000) * 100;
                                        const y2 = (Math.max(0, Math.min(end[1], 1000)) / 1000) * 100;
                                        return (
                                          <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
                                            <defs>
                                              <marker
                                                id={`arrowhead-cast-${idx}`}
                                                markerWidth="6"
                                                markerHeight="6"
                                                refX="5"
                                                refY="3"
                                                orient="auto"
                                              >
                                                <polygon points="0,0 6,3 0,6" fill="rgba(239,68,68,0.9)" />
                                              </marker>
                                            </defs>
                                            <circle cx={`${x1}%`} cy={`${y1}%`} r="4" fill="rgba(239,68,68,0.9)" />
                                            <line
                                              x1={`${x1}%`}
                                              y1={`${y1}%`}
                                              x2={`${x2}%`}
                                              y2={`${y2}%`}
                                              stroke="rgba(239,68,68,0.9)"
                                              strokeWidth="3"
                                              markerEnd={`url(#arrowhead-cast-${idx})`}
                                              strokeDasharray="5 3"
                                            />
                                          </svg>
                                        );
                                      }
                                    }
                                    return null;
                                  })()}
                              </ImagePreview>
                            </div>
                          )}

                          {stepAction && (
                            <details className="mt-2 text-xs">
                              <summary className="cursor-pointer text-primary hover:text-primary/80 transition-colors">
                                查看操作
                              </summary>
                              <pre className="mt-2 p-2 bg-zinc-900 text-zinc-200 rounded-lg overflow-x-auto text-xs border border-border">
                                {JSON.stringify(stepAction, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      );
                    })}

                    {/* 当前思考中 */}
                    {message.currentThinking && (
                      <div className="bg-secondary/50 rounded-2xl rounded-tl-sm px-4 py-3 border border-border">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10">
                            <Sparkles className="h-3 w-3 text-primary animate-pulse" />
                          </div>
                          <span className="text-xs font-medium text-primary">思考中...</span>
                        </div>
                        <p className="text-sm whitespace-pre-wrap">
                          {message.currentThinking}
                          <span className="inline-block w-1 h-4 ml-0.5 bg-primary animate-pulse" />
                        </p>
                      </div>
                    )}

                    {/* 最终结果 */}
                    {message.content && (
                      <div
                        className={`
                          rounded-2xl px-4 py-3 flex items-start gap-2 border
                          ${
                            message.success === false
                              ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400'
                              : 'bg-secondary/50 border-border'
                          }
                        `}
                      >
                        <CheckCircle2
                          className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                            message.success === false
                              ? 'text-red-500'
                              : 'text-primary'
                          }`}
                        />
                        <div>
                          <p className="whitespace-pre-wrap">{message.content}</p>
                          {message.steps !== undefined && (
                            <p className="text-xs mt-2 text-muted-foreground">
                              完成 {message.steps} 步
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* 流式处理指示器 */}
                    {message.isStreaming && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        处理中...
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="max-w-[75%]">
                    <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-3">
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 text-right">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {showNewMessageNotice && (
          <div className="pointer-events-none absolute inset-x-0 bottom-4 flex justify-center">
            <Button
              onClick={handleScrollToLatest}
              size="sm"
              className="pointer-events-auto shadow-lg"
              aria-label="查看新消息"
            >
              查看新消息
            </Button>
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="p-4 border-t border-border bg-card">
        <div className="flex items-end gap-3">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder={
              !isConfigured
                ? t.devicePanel?.configureFirst || '请先配置 API'
                : t.devicePanel?.whatToDo || '描述你想完成的任务...'
            }
            disabled={loading}
            className="flex-1 min-h-[40px] max-h-[120px] resize-none"
            rows={1}
          />

          {/* 工作流快捷按钮 */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Popover
                open={showWorkflowPopover}
                onOpenChange={setShowWorkflowPopover}
              >
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-10 w-10 flex-shrink-0"
                  >
                    <ListChecks className="w-4 h-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="start" className="w-72 p-3">
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">{t.workflows?.selectWorkflow || '选择工作流'}</h4>
                    {workflows.length === 0 ? (
                      <div className="text-sm text-zinc-500 dark:text-zinc-400 space-y-1">
                        <p>暂无工作流</p>
                        <p>前往<a href="/workflows" className="text-primary underline">工作流</a>页面创建</p>
                      </div>
                    ) : (
                      <ScrollArea className="h-64">
                        <div className="space-y-1">
                          {workflows.map(workflow => (
                            <button
                              key={workflow.uuid}
                              onClick={() => handleExecuteWorkflow(workflow)}
                              className="w-full text-left p-2 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                            >
                              <div className="font-medium text-sm">{workflow.name}</div>
                              <div className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2">
                                {workflow.text}
                              </div>
                            </button>
                          ))}
                        </div>
                      </ScrollArea>
                    )}
                  </div>
                </PopoverContent>
              </Popover>
            </TooltipTrigger>
            <TooltipContent side="top" sideOffset={8} className="max-w-xs">
              <div className="space-y-1">
                <p className="font-medium">工作流</p>
                <p className="text-xs opacity-80">快速执行预设工作流</p>
              </div>
            </TooltipContent>
          </Tooltip>

          {/* 停止按钮 */}
          {loading && (
            <Button
              onClick={handleAbortChat}
              disabled={aborting}
              size="icon"
              variant="destructive"
              className="h-10 w-10 rounded-full flex-shrink-0"
              title="停止任务"
            >
              {aborting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Square className="h-4 w-4" />
              )}
            </Button>
          )}

          {/* 发送按钮 */}
          {!loading && (
            <Button
              onClick={handleSend}
              disabled={!input.trim() || !sessionReady}
              size="icon"
              className="h-10 w-10 rounded-full flex-shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
      </>
      )}
    </Card>
  );
}
