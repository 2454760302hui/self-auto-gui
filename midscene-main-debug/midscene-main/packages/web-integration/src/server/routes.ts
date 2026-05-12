import express, { type Router } from 'express';
import type { PageAgent } from '@/common/agent';
import type { Page as PlaywrightPage } from 'playwright';
import type { LogStream } from './log-stream';
import type {
  SessionManager,
  TaskRecord,
  TaskType,
  TaskRunContext,
} from './session-manager';

const supportedTaskTypes: TaskType[] = [
  'action',
  'query',
  'assert',
  'waitFor',
  'navigate',
  'snapshot',
];

export function createServerRoutes(
  sessionManager: SessionManager,
  logStream: LogStream,
): Router {
  const router = express.Router();

  router.get('/status', (req, res) => {
    res.json({ status: 'ok' });
  });

  router.post('/sessions', express.json({ limit: '1mb' }), async (req, res, next) => {
    try {
      const session = await sessionManager.createSession(req.body);
      res.json(session);
    } catch (error) {
      next(error);
    }
  });

  router.get('/sessions', (req, res) => {
    res.json(sessionManager.listSessions());
  });

  router.get('/sessions/:id', (req, res) => {
    const session = sessionManager.getSession(req.params.id);
    if (!session) {
      res.status(404).json({ error: 'Session not found' });
      return;
    }
    res.json(session);
  });

  router.get('/sessions/:id/tasks', (req, res) => {
    const session = sessionManager.getSession(req.params.id);
    if (!session) {
      res.status(404).json({ error: 'Session not found' });
      return;
    }
    res.json(sessionManager.listTasksBySession(req.params.id));
  });

  router.delete('/sessions/:id', async (req, res, next) => {
    try {
      const closed = await sessionManager.closeSession(req.params.id);
      if (!closed) {
        res.status(404).json({ error: 'Session not found' });
        return;
      }
      res.json({ success: true });
    } catch (error) {
      next(error);
    }
  });

  router.post('/tasks', express.json({ limit: '1mb' }), async (req, res, next) => {
    try {
      const { sessionId, type, prompt } = req.body;
      if (!sessionId || !type) {
        res.status(400).json({ error: 'sessionId and type are required' });
        return;
      }
      if (!supportedTaskTypes.includes(type)) {
        res.status(400).json({ error: `Unsupported task type: ${type}` });
        return;
      }
      if (type !== 'snapshot' && !prompt) {
        res.status(400).json({ error: 'prompt is required' });
        return;
      }

      const taskPrompt = typeof prompt === 'string' ? prompt : '';
      const task = sessionManager.createTask(sessionId, type, taskPrompt);
      logStream.publish({
        taskId: task.id,
        sessionId: task.sessionId,
        type: 'task-started',
        message: `Task started: ${task.type}`,
        timestamp: Date.now(),
        status: 'running',
        taskType: task.type,
      });

      void sessionManager
        .runTask(task.id, async (context) => runTaskWithEvents(context, logStream))
        .then((finalTask) => {
          if (finalTask.status === 'success') {
            if (finalTask.dump) {
              logStream.publish({
                taskId: finalTask.id,
                sessionId: finalTask.sessionId,
                type: 'dump-updated',
                message: 'Dump updated',
                timestamp: Date.now(),
                status: 'success',
                reportFile: finalTask.reportFile,
                dump: finalTask.dump,
              });
            }
            logStream.publish({
              taskId: finalTask.id,
              sessionId: finalTask.sessionId,
              type: 'task-finished',
              message: 'Task finished',
              timestamp: Date.now(),
              status: 'success',
              result: finalTask.result,
              reportFile: finalTask.reportFile,
              taskType: finalTask.type,
            });
          } else {
            logStream.publish({
              taskId: finalTask.id,
              sessionId: finalTask.sessionId,
              type: 'task-failed',
              message: finalTask.error || 'Task failed',
              timestamp: Date.now(),
              status: 'error',
              error: finalTask.error,
              taskType: finalTask.type,
            });
          }
        });

      res.json(task);
    } catch (error) {
      next(error);
    }
  });

  router.get('/tasks/:id', (req, res) => {
    const task = sessionManager.getTask(req.params.id);
    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }
    res.json(task);
  });

  router.get('/tasks/:id/events', (req, res) => {
    const task = sessionManager.getTask(req.params.id);
    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();
    logStream.subscribe(task.id, res);
  });

  return router;
}

async function runTaskWithEvents(
  context: TaskRunContext,
  logStream: LogStream,
) {
  const { task } = context;
  logStream.publishStep(task.id, task.sessionId, `Executing ${task.type}`, {
    prompt: task.prompt,
  });
  return runTaskByType(context, logStream);
}

async function runTaskByType(context: TaskRunContext, logStream: LogStream) {
  const { task } = context;
  if (task.type === 'navigate') {
    return runNavigateTask(context, logStream);
  }
  if (task.type === 'snapshot') {
    return runSnapshotTask(context, logStream);
  }
  return runAgentTask(context, logStream);
}

async function runAgentTask(
  context: TaskRunContext,
  logStream: LogStream,
): Promise<{ result?: any; reportFile?: string | null; dump?: string }> {
  const { task, agent } = context;
  const progressOptions = {
    onTaskStart(taskDetail: any) {
      logStream.publishStep(task.id, task.sessionId, 'AI step started', {
        lifecycle: 'start',
        type: taskDetail.type,
        subType: taskDetail.subType,
        param: taskDetail.param,
        thought: taskDetail.thought,
        status: taskDetail.status,
      });
    },
    onTaskFinish(taskDetail: any) {
      logStream.publishStep(task.id, task.sessionId, 'AI step finished', {
        lifecycle: 'finish',
        type: taskDetail.type,
        subType: taskDetail.subType,
        param: taskDetail.param,
        thought: taskDetail.thought,
        status: taskDetail.status,
        output: taskDetail.output,
        error: taskDetail.error,
      });
    },
    onTaskError(taskDetail: any) {
      logStream.publishStep(task.id, task.sessionId, 'AI step failed', {
        lifecycle: 'error',
        type: taskDetail.type,
        subType: taskDetail.subType,
        param: taskDetail.param,
        thought: taskDetail.thought,
        status: taskDetail.status,
        error: taskDetail.error,
      });
    },
  };

  let result: any;
  if (task.type === 'action') {
    await agent.aiAction(task.prompt, progressOptions);
    result = null;
  } else if (task.type === 'query') {
    result = await agent.aiQuery(task.prompt, progressOptions);
  } else if (task.type === 'assert') {
    await agent.aiAssert(task.prompt, undefined, undefined, progressOptions);
    result = null;
  } else {
    await agent.aiWaitFor(task.prompt, undefined, progressOptions);
    result = null;
  }

  return {
    result,
    reportFile: agent.reportFile || null,
    dump: agent.dumpDataString(),
  };
}

async function runNavigateTask(
  context: TaskRunContext,
  logStream: LogStream,
): Promise<{ result?: any; reportFile?: string | null; dump?: string }> {
  const { task, page, agent } = context;
  logStream.publishStep(task.id, task.sessionId, 'Navigating page', {
    url: task.prompt,
  });
  await page.goto(task.prompt);
  await Promise.race([
    page.waitForLoadState('networkidle'),
    new Promise((resolve) => setTimeout(resolve, 20_000)),
  ]);

  const currentUrl = page.url();
  const dump = agent.dumpDataString();
  return {
    result: { url: currentUrl },
    reportFile: agent.reportFile || null,
    dump,
  };
}

async function runSnapshotTask(
  context: TaskRunContext,
  logStream: LogStream,
): Promise<{ result?: any; reportFile?: string | null; dump?: string }> {
  const { task, page, webPage, agent } = context;
  logStream.publishStep(task.id, task.sessionId, 'Capturing snapshot');
  const screenshot = await webPage.screenshotBase64();
  const currentUrl = page.url();
  const title = await page.title();
  logStream.publish({
    taskId: task.id,
    sessionId: task.sessionId,
    type: 'snapshot',
    message: 'Snapshot captured',
    timestamp: Date.now(),
    status: 'running',
    detail: {
      url: currentUrl,
      title,
      screenshot,
    },
  });

  return {
    result: {
      url: currentUrl,
      title,
      screenshot,
    },
    reportFile: agent.reportFile || null,
    dump: agent.dumpDataString(),
  };
}
