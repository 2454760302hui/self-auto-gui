import { DownOutlined, LoadingOutlined, SendOutlined } from '@ant-design/icons';
import type { GroupedActionDump, MidsceneYamlFlowItemAIAction, UIContext } from '@midscene/core';
import { Helmet } from '@modern-js/runtime/head';
import { Alert, Button, Spin, Tooltip, message } from 'antd';
import { Form, Input } from 'antd';
import { Radio } from 'antd';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import Blackboard from './blackboard';
import { iconForStatus } from './misc';
import Player from './player';
import DemoData from './playground-demo-ui-context.json';
import type { ReplayScriptsInfo } from './replay-scripts';
import { allScriptsFromDump } from './replay-scripts';
import './playground-component.less';
import Logo from './logo';
import { serverBase, useServerValid } from './open-in-playground';

import { ScriptPlayer, buildYaml, parseYamlScript } from '@midscene/web/yaml';

import { overrideAIConfig } from '@midscene/core';
import {
  ERROR_CODE_NOT_IMPLEMENTED_AS_DESIGNED,
  StaticPage,
  StaticPageAgent,
} from '@midscene/web/playground';
import type { WebUIContext } from '@midscene/web/utils';
import type { MenuProps } from 'antd';
import { Dropdown, Space } from 'antd';
import { EnvConfig } from './env-config';
import { type HistoryItem, useChromeTabInfo, useEnvConfig } from './store';

import { getTabInfo } from '@/extension/utils';
import {
  ChromeExtensionProxyPage,
  ChromeExtensionProxyPageAgent,
} from '@midscene/web/chrome-extension';

type PlaygroundTaskType =
  | 'aiAction'
  | 'aiQuery'
  | 'aiAssert'
  | 'aiWaitFor'
  | 'navigate'
  | 'snapshot';

interface PlaygroundResult {
  result: any;
  dump: GroupedActionDump | null;
  reportHTML: string | null;
  error: string | null;
}

interface SessionSummary {
  id: string;
  url: string;
  status: ControlSessionRecord['status'];
  startedAt: number;
}

interface TaskHistoryItem extends TaskSummary {
  events: ControlTaskEvent[];
}

interface TaskSummary {
  id: string;
  type: string;
  status: string;
  prompt: string;
}

interface ControlSessionRecord {
  id: string;
  runnerType: 'playwright';
  status: 'starting' | 'ready' | 'closed' | 'error';
  url: string;
  headed: boolean;
  createdAt: number;
  updatedAt: number;
}

interface ControlTaskRecord {
  id: string;
  sessionId: string;
  type: 'action' | 'query' | 'assert' | 'waitFor' | 'navigate' | 'snapshot';
  prompt: string;
  status: 'pending' | 'running' | 'success' | 'error';
  result?: any;
  error?: string;
  reportFile?: string | null;
  dump?: string;
  createdAt: number;
  updatedAt: number;
}

interface ControlTaskEvent {
  taskId: string;
  sessionId: string;
  type:
    | 'task-started'
    | 'step'
    | 'snapshot'
    | 'dump-updated'
    | 'task-finished'
    | 'task-failed';
  message: string;
  timestamp: number;
  status?: 'pending' | 'running' | 'success' | 'error';
  result?: any;
  error?: string;
  reportFile?: string | null;
  dump?: string;
  detail?: any;
  taskType?: ControlTaskRecord['type'];
}

const requestControlSession = async (url: string) => {
  const res = await fetch(`${serverBase}/api/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      url,
      headed: true,
    }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error || 'Failed to create session');
  }

  return (await res.json()) as ControlSessionRecord;
};

const requestControlTask = async (
  sessionId: string,
  type: PlaygroundTaskType,
  prompt: string,
) => {
  const taskTypeMap = {
    aiAction: 'action',
    aiQuery: 'query',
    aiAssert: 'assert',
    aiWaitFor: 'waitFor',
    navigate: 'navigate',
    snapshot: 'snapshot',
  } as const;

  const res = await fetch(`${serverBase}/api/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      sessionId,
      type: taskTypeMap[type],
      prompt,
    }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error || 'Failed to create task');
  }

  return (await res.json()) as ControlTaskRecord;
};

const waitForControlTask = async (
  taskId: string,
  taskType: ControlTaskRecord['type'],
  onProgress: (text: string) => void,
  onEvent?: (event: ControlTaskEvent) => void,
) => {
  const eventSource = new EventSource(`${serverBase}/api/tasks/${taskId}/events`);

  return await new Promise<ControlTaskRecord>((resolve, reject) => {
    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as ControlTaskEvent;
        onEvent?.(payload);
        if (payload?.message) {
          onProgress(payload.message);
        }

        if (payload?.type === 'task-finished') {
          eventSource.close();
          resolve({
            id: payload.taskId,
            sessionId: payload.sessionId,
            type: payload.taskType || taskType,
            prompt: '',
            status: payload.status || 'success',
            result: payload.result,
            reportFile: payload.reportFile,
            dump: payload.dump,
            createdAt: payload.timestamp,
            updatedAt: payload.timestamp,
          });
        }

        if (payload?.type === 'task-failed') {
          eventSource.close();
          reject(new Error(payload?.error || payload?.message || 'Task failed'));
        }
      } catch (error) {
        eventSource.close();
        reject(error);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      reject(new Error('Failed to subscribe task events'));
    };
  });
};

const closeControlSession = async (sessionId: string) => {
  await fetch(`${serverBase}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  }).catch(() => undefined);
};

const actionNameForType = (type: string) => {
  if (type === 'aiAction') return 'Action';
  if (type === 'aiQuery') return 'Query';
  if (type === 'aiAssert') return 'Assert';
  if (type === 'aiWaitFor') return 'Wait';
  if (type === 'navigate') return 'Navigate';
  if (type === 'snapshot') return 'Snapshot';
  return type;
};

const { TextArea } = Input;

export const staticAgentFromContext = (context: WebUIContext) => {
  const page = new StaticPage(context);
  return new StaticPageAgent(page);
};

export const useStaticPageAgent = (
  context: WebUIContext | undefined | null,
): StaticPageAgent | null => {
  const agent = useMemo(() => {
    if (!context) return null;

    return staticAgentFromContext(context);
  }, [context]);
  return agent;
};

const useHistorySelector = (onSelect: (history: HistoryItem) => void) => {
  const history = useEnvConfig((state) => state.history);
  const clearHistory = useEnvConfig((state) => state.clearHistory);

  const items: MenuProps['items'] = history.map((item, index) => ({
    label: (
      <a onClick={() => onSelect(item)}>
        {actionNameForType(item.type)} - {item.prompt.slice(0, 50)}
        {item.prompt.length > 50 ? '...' : ''}
      </a>
    ),
    key: String(index),
  }));

  items.push({
    type: 'divider',
  });

  items.push({
    label: (
      <a onClick={() => clearHistory()}>
        <Space>Clear History</Space>
      </a>
    ),
    key: 'clear',
  });

  return history.length > 0 ? (
    <div className="history-selector">
      <Dropdown menu={{ items }}>
        <Space>
          history <DownOutlined />
        </Space>
      </Dropdown>
    </div>
  ) : null;
};

const errorMessageServerNotReady = (
  <span>
    Don't worry, just one more step to launch the control server.
    <br />
    Please run one of the commands under the midscene project directory:
    <br />
    a. <strong>npx midscene-control-server</strong>
    <br />
    b. <strong>pnpm --filter @midscene/web dev:control-server</strong>
  </span>
);

const serverLaunchTip = (
  <div className="server-tip">
    <Alert
      message="Playground Server Not Ready"
      description={errorMessageServerNotReady}
      type="warning"
    />
  </div>
);

// remember to destroy the agent when the tab is destroyed: agent.page.destroy()
export const extensionAgentForTabId = (
  tabId: number | null,
  windowId: number | null,
) => {
  if (!tabId || !windowId) {
    return null;
  }
  const page = new ChromeExtensionProxyPage(tabId, windowId);
  return new ChromeExtensionProxyPageAgent(page);
};

export function Playground({
  getAgent,
  hideLogo,
  showContextPreview = true,
  dryMode = false,
}: {
  getAgent: () => StaticPageAgent | ChromeExtensionProxyPageAgent | null;
  hideLogo?: boolean;
  showContextPreview?: boolean;
  dryMode?: boolean;
}) {
  // const contextId = useContextId();
  const [uiContextPreview, setUiContextPreview] = useState<
    UIContext | undefined
  >(undefined);

  const [loading, setLoading] = useState(false);
  const [tabInfoString, setTabInfoString] = useState('');
  const [loadingProgressText, setLoadingProgressText] = useState('');
  const [taskEvents, setTaskEvents] = useState<ControlTaskEvent[]>([]);
  const [autoScrollEvents, setAutoScrollEvents] = useState(true);
  const [expandedEventKeys, setExpandedEventKeys] = useState<Record<string, boolean>>({});
  const [sessionSummary, setSessionSummary] = useState<SessionSummary | null>(null);
  const [taskSummaries, setTaskSummaries] = useState<TaskSummary[]>([]);
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [result, setResult] = useState<PlaygroundResult | null>(null);
  const [form] = Form.useForm();
  const { config, serviceMode, setServiceMode } = useEnvConfig();
  const configAlreadySet = Object.keys(config || {}).length >= 1;
  const runResultRef = useRef<HTMLHeadingElement>(null);
  const taskEventsListRef = useRef<HTMLDivElement>(null);

  const [verticalMode, setVerticalMode] = useState(false);

  const { tabId } = useChromeTabInfo();

  // if the screen is narrow, we use vertical mode
  useEffect(() => {
    const sizeThreshold = 750;
    setVerticalMode(window.innerWidth < sizeThreshold);

    const handleResize = () => {
      setVerticalMode(window.innerWidth < sizeThreshold);
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // override AI config
  useEffect(() => {
    overrideAIConfig(config as any);
  }, [config]);

  useEffect(() => {
    if (!autoScrollEvents || !taskEventsListRef.current) return;
    taskEventsListRef.current.scrollTop = taskEventsListRef.current.scrollHeight;
  }, [taskEvents, autoScrollEvents]);

  const [replayScriptsInfo, setReplayScriptsInfo] =
    useState<ReplayScriptsInfo | null>(null);
  const [replayCounter, setReplayCounter] = useState(0);

  const serverValid = useServerValid(serviceMode === 'Server');

  // setup context preview
  useEffect(() => {
    if (uiContextPreview) return;
    if (!showContextPreview) return;

    getAgent()
      ?.getUIContext()
      .then((context) => {
        setUiContextPreview(context);
      })
      .catch((e) => {
        message.error('Failed to get UI context');
        console.error(e);
      });
  }, [uiContextPreview, showContextPreview, getAgent]);

  const addHistory = useEnvConfig((state) => state.addHistory);

  const handleRun = useCallback(async () => {
    const value = form.getFieldsValue();
    const promptRequired = value.type !== 'snapshot';
    if (promptRequired && !value.prompt) {
      message.error('Prompt is required');
      return;
    }

    const startTime = Date.now();

    if (tabId) {
      Promise.resolve().then(async () => {
        const tab = await getTabInfo(tabId);
        const tabInfoString = dryMode ? '' : `${tab.title} ${tab.url}`;
        setTabInfoString(tabInfoString);
      });
    }
    setLoading(true);
    setResult(null);
    setTaskEvents([]);
    setExpandedEventKeys({});
    setSessionSummary(null);
    setTaskSummaries([]);
    setTaskHistory([]);
    setSelectedTaskId(null);
    addHistory({
      type: value.type,
      prompt: value.prompt,
      timestamp: Date.now(),
    });
    let result: PlaygroundResult = {
      result: null,
      dump: null,
      reportHTML: null,
      error: null,
    };

    const activeAgent = getAgent();
    try {
      if (!activeAgent) {
        throw new Error('No agent found');
      }
      activeAgent?.resetDump();
      if (serviceMode === 'Server') {
        const currentTab = tabId ? await getTabInfo(tabId) : null;
        if (!currentTab?.url) {
          throw new Error('No active tab URL found');
        }

        setTabInfoString(dryMode ? '' : `${currentTab.title} ${currentTab.url}`);
        if (value.type === 'snapshot') {
          setLoadingProgressText('Capturing snapshot...');
        } else if (value.type === 'navigate') {
          setLoadingProgressText('Navigating page...');
        } else {
          setLoadingProgressText('Running task in current session...');
        }

        let session = sessionSummary;
        if (!session || session.status === 'closed' || session.url !== currentTab.url) {
          const createdSession = await requestControlSession(currentTab.url);
          session = {
            id: createdSession.id,
            url: createdSession.url,
            status: createdSession.status,
            startedAt: createdSession.createdAt,
          };
          setSessionSummary(session);
          setTaskSummaries([]);
          setTaskHistory([]);
          setSelectedTaskId(null);
        }

        const task = await requestControlTask(
          session.id,
          value.type,
          value.prompt,
        );
        const nextTaskSummary = {
          id: task.id,
          type: task.type,
          status: task.status,
          prompt: task.prompt,
        };
        setTaskSummaries((current) => [...current, nextTaskSummary]);
        setTaskHistory((current) => [...current, { ...nextTaskSummary, events: [] }]);
        setSelectedTaskId(task.id);

        const finalTask = await waitForControlTask(
          task.id,
          task.type,
          setLoadingProgressText,
          (event) => {
            setTaskEvents((current) =>
              selectedTaskId === task.id || selectedTaskId === null
                ? [...current, event]
                : current,
            );
            setTaskHistory((current) =>
              current.map((item) =>
                item.id === task.id
                  ? {
                      ...item,
                      status:
                        event.type === 'task-failed'
                          ? 'error'
                          : event.type === 'task-finished'
                            ? 'success'
                            : event.status || item.status,
                      events: [...item.events, event],
                    }
                  : item,
              ),
            );
            setTaskSummaries((current) =>
              current.map((item) =>
                item.id === task.id
                  ? {
                      ...item,
                      status:
                        event.type === 'task-failed'
                          ? 'error'
                          : event.type === 'task-finished'
                            ? 'success'
                            : event.status || item.status,
                    }
                  : item,
              ),
            );
          },
        );

        result.result = finalTask.result ?? null;
        result.error = finalTask.error || null;
        result.dump = finalTask.dump ? JSON.parse(finalTask.dump) : null;
        result.reportHTML = null;
        setSessionSummary((current) =>
          current ? { ...current, status: 'ready' } : current,
        );
      } else {
        if (value.type === 'aiAction') {
          const yamlString = buildYaml(
            {
              url: 'https://www.baidu.com',
            },
            [
              {
                name: 'aiAction',
                flow: [{ aiAction: value.prompt }],
              },
            ],
          );

          const parsedYamlScript = parseYamlScript(yamlString);
          console.log('yamlString', parsedYamlScript, yamlString);
          let errorMessage = '';
          const yamlPlayer = new ScriptPlayer(
            parsedYamlScript,
            async () => {
              if (!activeAgent) throw new Error('Agent is not initialized');

              activeAgent?.resetDump();
              return {
                agent: activeAgent,
                freeFn: [],
              };
            },
            (taskStatus) => {
              let overallStatus = '';
              if (taskStatus.status === 'init') {
                overallStatus = 'initializing...';
              } else if (
                taskStatus.status === 'running' ||
                taskStatus.status === 'error'
              ) {
                const item = taskStatus.flow[0] as MidsceneYamlFlowItemAIAction;
                // const brief = flowItemBrief(item);
                const tips = item?.aiActionProgressTips || [];
                if (tips.length > 0) {
                  overallStatus = tips[tips.length - 1];
                }

                if (taskStatus.status === 'error') {
                  errorMessage = taskStatus.error?.message || '';
                }
              }

              setLoadingProgressText(overallStatus);
            },
          );

          await yamlPlayer.run();
          if (yamlPlayer.status === 'error') {
            throw new Error(errorMessage || 'Failed to run the script');
          }
        } else if (value.type === 'aiQuery') {
          result.result = await activeAgent?.aiQuery(value.prompt);
        } else if (value.type === 'aiAssert') {
          result.result = await activeAgent?.aiAssert(value.prompt, undefined, {
            keepRawResponse: true,
          });
        } else if (value.type === 'aiWaitFor') {
          await activeAgent?.aiWaitFor(value.prompt);
          result.result = 'Wait condition satisfied';
        } else if (value.type === 'navigate') {
          result.result = {
            note: 'Navigate is only available in Server mode',
            url: value.prompt,
          };
        } else if (value.type === 'snapshot') {
          result.result = {
            note: 'Snapshot is only available in Server mode',
          };
        }
      }
    } catch (e: any) {
      console.error(e);
      if (typeof e === 'string') {
        if (e.includes('of different extension')) {
          result.error =
            'Cannot access a chrome-extension:// URL of different extension. Please disable the suspicious plugins and refresh the page. Guide: https://midscenejs.com/quick-experience.html#faq';
        } else {
          result.error = e;
        }
      } else if (!e.message?.includes(ERROR_CODE_NOT_IMPLEMENTED_AS_DESIGNED)) {
        result.error = e.message;
      } else {
        result.error = 'Unknown error';
      }
    }

    try {
      if (
        serviceMode === 'In-Browser' ||
        serviceMode === 'In-Browser-Extension'
      ) {
        result.dump = activeAgent?.dumpDataString()
          ? JSON.parse(activeAgent.dumpDataString())
          : null;

        result.reportHTML = activeAgent?.reportHTMLString() || null;
      }
    } catch (e) {
      console.error(e);
    }

    try {
      console.log('destroy agent.page', activeAgent?.page);
      await activeAgent?.page?.destroy();
      console.log('destroy agent.page done', activeAgent?.page);
    } catch (e) {
      console.error(e);
    }

    setResult(result);
    setLoading(false);
    if (value.type === 'aiAction' && result?.dump) {
      const info = allScriptsFromDump(result.dump);
      setReplayScriptsInfo(info);
      setReplayCounter((c) => c + 1);
    } else {
      setReplayScriptsInfo(null);
    }
    console.log(`time taken: ${Date.now() - startTime}ms`);

    // Scroll the Run header into view
    // setTimeout(() => {
    //   runResultRef.current?.scrollIntoView({ behavior: 'smooth' });
    // }, 50);
  }, [form, getAgent, serviceMode, serverValid, tabId]);

  let placeholder = 'What do you want to do?';
  const selectedType = Form.useWatch('type', form);

  if (selectedType === 'aiQuery') {
    placeholder = 'What do you want to query?';
  } else if (selectedType === 'aiAssert') {
    placeholder = 'What do you want to assert?';
  } else if (selectedType === 'aiWaitFor') {
    placeholder = 'What condition do you want to wait for?';
  } else if (selectedType === 'navigate') {
    placeholder = 'Enter the target URL';
  } else if (selectedType === 'snapshot') {
    placeholder = 'Snapshot does not require a prompt in Server mode';
  }

  const runButtonEnabled =
    (serviceMode === 'In-Browser' && !!getAgent && configAlreadySet) ||
    (serviceMode === 'Server' && serverValid) ||
    (serviceMode === 'In-Browser-Extension' && !!getAgent && configAlreadySet);

  const visibleTaskEvents = selectedTaskId
    ? taskHistory.find((item) => item.id === selectedTaskId)?.events || []
    : taskEvents;

  const eventPanel = visibleTaskEvents.length ? (
    <div className="task-events-panel">
      <div className="task-events-header">
        <h4>Task Events</h4>
        <div className="task-events-actions">
          <Button size="small" type={autoScrollEvents ? 'primary' : 'default'} onClick={() => setAutoScrollEvents((value) => !value)}>
            Auto Scroll
          </Button>
          <Button
            size="small"
            onClick={() => {
              setTaskEvents([]);
              setTaskHistory((current) =>
                current.map((item) =>
                  selectedTaskId && item.id !== selectedTaskId
                    ? item
                    : { ...item, events: [] },
                ),
              );
              setExpandedEventKeys({});
            }}
          >
            Clear
          </Button>
        </div>
      </div>
      <div className="task-events-list" ref={taskEventsListRef}>
        {visibleTaskEvents.map((event, index) => {
          const eventKey = `${event.timestamp}-${index}`;
          const expanded = Boolean(expandedEventKeys[eventKey]);
          return (
            <div key={eventKey} className="task-event-item">
              <div className="task-event-meta">
                <span className="task-event-type">{event.type}</span>
                <span className="task-event-status">{event.status || 'running'}</span>
              </div>
              <div className="task-event-message">{event.message}</div>
              {event.detail ? (
                <>
                  <Button
                    type="link"
                    size="small"
                    className="task-event-toggle"
                    onClick={() =>
                      setExpandedEventKeys((current) => ({
                        ...current,
                        [eventKey]: !current[eventKey],
                      }))
                    }
                  >
                    {expanded ? 'Hide detail' : 'Show detail'}
                  </Button>
                  {expanded ? <pre>{JSON.stringify(event.detail, null, 2)}</pre> : null}
                </>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  ) : null;

  const summaryPanel = sessionSummary || taskSummaries.length ? (
    <div className="task-events-panel session-summary-panel">
      <h4>Session & Tasks</h4>
      {sessionSummary ? (
        <div className="session-summary-item">
          <div><strong>Session:</strong> {sessionSummary.id}</div>
          <div><strong>Status:</strong> {sessionSummary.status}</div>
          <div><strong>URL:</strong> {sessionSummary.url}</div>
        </div>
      ) : null}
      {taskHistory.length ? (
        <div className="task-summary-list">
          {taskHistory.map((task) => (
            <button
              key={task.id}
              type="button"
              className={`task-summary-item ${selectedTaskId === task.id ? 'task-summary-item-active' : ''}`}
              onClick={() => {
                setSelectedTaskId(task.id);
                setTaskEvents(task.events);
                setExpandedEventKeys({});
              }}
            >
              <div><strong>{task.type}</strong> · {task.status}</div>
              <div>{task.prompt || '(no prompt)'}</div>
              <div className="task-summary-id">{task.id}</div>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  ) : null;

  let resultDataToShow: any = (
    <div className="result-empty-tip">
      <span>The result will be shown here</span>
    </div>
  );
  const snapshotImage = result?.result?.screenshot;
  if (!serverValid && serviceMode === 'Server') {
    resultDataToShow = serverLaunchTip;
  } else if (loading) {
    resultDataToShow = (
      <div className="loading-container">
        <Spin spinning={loading} indicator={<LoadingOutlined spin />} />
        <div className="loading-progress-text loading-progress-text-tab-info">
          {tabInfoString}
        </div>
        <div className="loading-progress-text loading-progress-text-progress">
          {loadingProgressText}
        </div>
      </div>
    );
  } else if (replayScriptsInfo) {
    resultDataToShow = (
      <Player
        key={replayCounter}
        replayScripts={replayScriptsInfo.scripts}
        imageWidth={replayScriptsInfo.width}
        imageHeight={replayScriptsInfo.height}
        reportFileContent={result?.reportHTML}
      />
    );
  } else if (snapshotImage) {
    resultDataToShow = (
      <div>
        <img
          src={snapshotImage}
          alt="Snapshot"
          style={{ maxWidth: '100%', display: 'block', marginBottom: 12 }}
        />
        <pre>{JSON.stringify(result?.result, null, 2)}</pre>
      </div>
    );
  } else if (result?.result) {
    resultDataToShow =
      typeof result?.result === 'string' ? (
        <pre>{result?.result}</pre>
      ) : (
        <pre>{JSON.stringify(result?.result, null, 2)}</pre>
      );
  } else if (result?.error) {
    resultDataToShow = <pre>{result?.error}</pre>;
  }

  const serverTip = !serverValid ? (
    <div className="server-tip">
      {iconForStatus('failed')} Connection failed
    </div>
  ) : (
    <div className="server-tip">{iconForStatus('connected')} Connected</div>
  );

  const switchBtn =
    serviceMode === 'In-Browser-Extension' ? null : (
      <Tooltip
        title={
          <span>
            Server Mode: send the request through the server <br />
            In-Browser Mode: send the request through the browser fetch API (The
            AI service should support CORS in this case)
          </span>
        }
      >
        <Button
          type="link"
          onClick={(e) => {
            e.preventDefault();
            setServiceMode(serviceMode === 'Server' ? 'In-Browser' : 'Server');
          }}
        >
          {serviceMode === 'Server'
            ? 'Switch to In-Browser Mode'
            : 'Switch to Server Mode'}
        </Button>
      </Tooltip>
    );

  const statusContent = serviceMode === 'Server' ? serverTip : <EnvConfig />;

  const actionBtn = dryMode ? (
    <Tooltip title="Start executing until some interaction actions need to be performed. You can see the process of planning and locating.">
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleRun}
        disabled={!runButtonEnabled}
        loading={loading}
      >
        Dry Run
      </Button>
    </Tooltip>
  ) : (
    <Button
      type="primary"
      icon={<SendOutlined />}
      onClick={handleRun}
      disabled={!runButtonEnabled}
      loading={loading}
    >
      Run
    </Button>
  );

  const historySelector = useHistorySelector((historyItem) => {
    form.setFieldsValue({
      prompt: historyItem.prompt,
      type: historyItem.type,
    });
  });

  const logo = !hideLogo && (
    <div className="playground-header">
      <Logo />
    </div>
  );

  const history = useEnvConfig((state) => state.history);
  const lastHistory = history[0];
  const historyInitialValues = useMemo(() => {
    return {
      type: lastHistory?.type || 'aiAction',
      prompt: lastHistory?.prompt || '',
    };
  }, []);

  const formSection = (
    <Form
      form={form}
      onFinish={handleRun}
      initialValues={{ ...historyInitialValues }}
    >
      <div className="playground-form-container">
        <div className="form-part">
          <h3>
            {serviceMode === 'Server'
              ? 'Server Status'
              : 'In-Browser Request Config'}
          </h3>
          {statusContent}
          <div className="switch-btn-wrapper">{switchBtn}</div>
        </div>
        <div
          className="form-part context-panel"
          style={{ display: showContextPreview ? 'block' : 'none' }}
        >
          <h3>UI Context</h3>
          {uiContextPreview ? (
            <Blackboard
              uiContext={uiContextPreview}
              hideController
              disableInteraction
            />
          ) : (
            <div>
              {iconForStatus('failed')} No UI context
              <Button
                type="link"
                onClick={(e) => {
                  e.preventDefault();
                  setUiContextPreview(DemoData as any);
                }}
              >
                Load Demo
              </Button>
              <div>
                To load the UI context, you can either use the demo data above,
                or click the 'Send to Playground' in the report page.
              </div>
            </div>
          )}
        </div>
        <div className="form-part input-wrapper">
          <h3>Run</h3>
          <Form.Item name="type">
            <Radio.Group buttonStyle="solid" disabled={!runButtonEnabled}>
              <Radio.Button value="aiAction">
                {actionNameForType('aiAction')}
              </Radio.Button>
              <Radio.Button value="aiQuery">
                {actionNameForType('aiQuery')}
              </Radio.Button>
              <Radio.Button value="aiAssert">
                {actionNameForType('aiAssert')}
              </Radio.Button>
              <Radio.Button value="aiWaitFor">
                {actionNameForType('aiWaitFor')}
              </Radio.Button>
              <Radio.Button value="navigate">
                {actionNameForType('navigate')}
              </Radio.Button>
              <Radio.Button value="snapshot">
                {actionNameForType('snapshot')}
              </Radio.Button>
            </Radio.Group>
          </Form.Item>
          <div className="main-side-console-input">
            <Form.Item name="prompt">
              <TextArea
                disabled={!runButtonEnabled || selectedType === 'snapshot'}
                rows={4}
                placeholder={placeholder}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.metaKey) {
                    handleRun();
                    e.preventDefault();
                    e.stopPropagation();
                  }
                }}
              />
            </Form.Item>
            {actionBtn}
            {historySelector}
          </div>
        </div>
      </div>
    </Form>
  );

  let resultWrapperClassName = 'result-wrapper';
  if (verticalMode) {
    resultWrapperClassName += ' vertical-mode-result';
  }
  if (replayScriptsInfo && verticalMode) {
    resultWrapperClassName += ' result-wrapper-compact';
  }

  return verticalMode ? (
    <div className="playground-container vertical-mode">
      {formSection}
      <div className="form-part">
        <div className={resultWrapperClassName}>{resultDataToShow}</div>
        {summaryPanel}
        {eventPanel}
        <div ref={runResultRef} />
      </div>
    </div>
  ) : (
    <div className="playground-container">
      <Helmet>
        <title>Playground - Midscene.js</title>
      </Helmet>
      <PanelGroup autoSaveId="playground-layout" direction="horizontal">
        <Panel
          defaultSize={32}
          maxSize={60}
          minSize={20}
          className="playground-left-panel"
        >
          {logo}
          {formSection}
        </Panel>
        <PanelResizeHandle className="panel-resize-handle" />
        <Panel>
          <div className={resultWrapperClassName}>{resultDataToShow}</div>
          {summaryPanel}
          {eventPanel}
        </Panel>
      </PanelGroup>
    </div>
  );
}

export function StaticPlayground({
  context,
}: {
  context: WebUIContext | null;
}) {
  const agent = useStaticPageAgent(context);
  return (
    <Playground
      getAgent={() => {
        return agent;
      }}
      dryMode={true}
    />
  );
}
