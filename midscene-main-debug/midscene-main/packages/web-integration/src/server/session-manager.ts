import { randomUUID } from 'node:crypto';
import type { PageAgent } from '@/common/agent';
import type { Browser, Page } from 'playwright';
import type { WebPage } from '@/playwright/page';
import {
  createPlaywrightSession,
  type PlaywrightSessionOptions,
} from './playwright-runner';

export type SessionStatus = 'starting' | 'ready' | 'closed' | 'error';
export type TaskStatus = 'pending' | 'running' | 'success' | 'error';
export type TaskType =
  | 'action'
  | 'query'
  | 'assert'
  | 'waitFor'
  | 'navigate'
  | 'snapshot';

interface SessionRuntime {
  browser: Browser;
  page: Page;
  webPage: WebPage;
  agent: PageAgent;
  destroy: () => Promise<void>;
}

export interface SessionRecord {
  id: string;
  runnerType: 'playwright';
  status: SessionStatus;
  url: string;
  headed: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface TaskRecord {
  id: string;
  sessionId: string;
  type: TaskType;
  prompt: string;
  status: TaskStatus;
  result?: any;
  error?: string;
  reportFile?: string | null;
  dump?: string;
  createdAt: number;
  updatedAt: number;
}

export interface TaskRunContext {
  task: TaskRecord;
  agent: PageAgent;
  page: Page;
  webPage: WebPage;
}

export interface TaskRunResult {
  result?: any;
  reportFile?: string | null;
  dump?: string;
}

export class SessionManager {
  private sessions = new Map<string, SessionRecord>();
  private runtimes = new Map<string, SessionRuntime>();
  private tasks = new Map<string, TaskRecord>();
  private sessionLocks = new Map<string, Promise<void>>();

  async createSession(options: PlaywrightSessionOptions): Promise<SessionRecord> {
    const id = randomUUID();
    const now = Date.now();
    const record: SessionRecord = {
      id,
      runnerType: 'playwright',
      status: 'starting',
      url: options.url,
      headed: Boolean(options.headed),
      createdAt: now,
      updatedAt: now,
    };

    this.sessions.set(id, record);

    try {
      const runtime = await createPlaywrightSession({
        ...options,
        testId: options.testId || `server-session-${id}`,
      });
      this.runtimes.set(id, runtime);
      record.status = 'ready';
      record.updatedAt = Date.now();
      return { ...record };
    } catch (error) {
      record.status = 'error';
      record.updatedAt = Date.now();
      throw error;
    }
  }

  listSessions(): SessionRecord[] {
    return Array.from(this.sessions.values()).map((item) => ({ ...item }));
  }

  getSession(id: string): SessionRecord | undefined {
    const session = this.sessions.get(id);
    return session ? { ...session } : undefined;
  }

  async closeSession(id: string): Promise<boolean> {
    const session = this.sessions.get(id);
    if (!session) return false;

    const runtime = this.runtimes.get(id);
    if (runtime) {
      await runtime.destroy();
      this.runtimes.delete(id);
    }

    session.status = 'closed';
    session.updatedAt = Date.now();
    return true;
  }

  createTask(sessionId: string, type: TaskType, prompt: string): TaskRecord {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }
    if (session.status !== 'ready') {
      throw new Error(`Session is not ready: ${sessionId}`);
    }

    const now = Date.now();
    const task: TaskRecord = {
      id: randomUUID(),
      sessionId,
      type,
      prompt,
      status: 'pending',
      createdAt: now,
      updatedAt: now,
    };
    this.tasks.set(task.id, task);
    return { ...task };
  }

  getTask(id: string): TaskRecord | undefined {
    const task = this.tasks.get(id);
    return task ? { ...task } : undefined;
  }

  listTasksBySession(sessionId: string): TaskRecord[] {
    return Array.from(this.tasks.values())
      .filter((task) => task.sessionId === sessionId)
      .sort((a, b) => a.createdAt - b.createdAt)
      .map((task) => ({ ...task }));
  }

  async runTask(
    taskId: string,
    runner: (context: TaskRunContext) => Promise<TaskRunResult>,
  ): Promise<TaskRecord> {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new Error(`Task not found: ${taskId}`);
    }
    const runtime = this.runtimes.get(task.sessionId);
    if (!runtime) {
      throw new Error(`Session runtime not found: ${task.sessionId}`);
    }

    const previous = this.sessionLocks.get(task.sessionId) || Promise.resolve();
    let release!: () => void;
    const current = new Promise<void>((resolve) => {
      release = resolve;
    });
    this.sessionLocks.set(task.sessionId, previous.then(() => current));

    await previous;
    task.status = 'running';
    task.updatedAt = Date.now();

    try {
      const result = await runner({
        task: { ...task },
        agent: runtime.agent,
        page: runtime.page,
        webPage: runtime.webPage,
      });
      task.status = 'success';
      task.result = result.result;
      task.reportFile = result.reportFile;
      task.dump = result.dump;
      task.updatedAt = Date.now();
      return { ...task };
    } catch (error: any) {
      task.status = 'error';
      task.error = error?.message || String(error);
      task.updatedAt = Date.now();
      return { ...task };
    } finally {
      release();
    }
  }
}
